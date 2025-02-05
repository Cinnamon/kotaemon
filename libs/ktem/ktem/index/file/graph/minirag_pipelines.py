import glob
import logging
import os
from pathlib import Path
from typing import Generator

import numpy as np
from ktem.db.models import engine
from ktem.embeddings.manager import embedding_models_manager as embeddings
from ktem.llms.manager import llms
from sqlalchemy.orm import Session
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from theflow.settings import settings

from kotaemon.base import Document, Param, RetrievedDocument
from kotaemon.base.schema import AIMessage, HumanMessage, SystemMessage

from ..pipelines import BaseFileIndexRetriever
from .pipelines import GraphRAGIndexingPipeline

try:
    from minirag import MiniRAG, QueryParam
    from minirag.utils import EmbeddingFunc, compute_args_hash

except ImportError:
    print(
        (
            "MiniRAG dependencies not installed. "
            "Try `pip install git+https://github.com/HKUDS/MiniRAG.git` to install. "
            "MiniRAG retriever pipeline will not work properly."
        )
    )


logging.getLogger("minirag").setLevel(logging.INFO)


filestorage_path = Path(settings.KH_FILESTORAGE_PATH) / "minirag"
filestorage_path.mkdir(parents=True, exist_ok=True)

INDEX_BATCHSIZE = 4


def get_llm_func(model):
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception,)),
        after=lambda retry_state: logging.warning(
            f"LLM API call attempt {retry_state.attempt_number} failed. Retrying..."
        ),
    )
    async def _call_model(model, input_messages):
        return (await model.ainvoke(input_messages)).text

    async def llm_func(
        prompt, system_prompt=None, history_messages=[], **kwargs
    ) -> str:
        input_messages = [SystemMessage(text=system_prompt)] if system_prompt else []

        hashing_kv = kwargs.pop("hashing_kv", None)
        if history_messages:
            for msg in history_messages:
                if msg.get("role") == "user":
                    input_messages.append(HumanMessage(text=msg["content"]))
                else:
                    input_messages.append(AIMessage(text=msg["content"]))

        input_messages.append(HumanMessage(text=prompt))

        if hashing_kv is not None:
            args_hash = compute_args_hash("model", input_messages)
            if_cache_return = await hashing_kv.get_by_id(args_hash)
            if if_cache_return is not None:
                return if_cache_return["return"]

        print("-" * 50)
        print(prompt, "\n", "-" * 50)

        try:
            output = await _call_model(model, input_messages)
        except Exception as e:
            logging.error(f"Failed to call LLM API after 3 retries: {str(e)}")
            raise

        print("-" * 50)
        print(prompt, "\n", "-" * 50)
        print(output, "\n", "-" * 50)

        if hashing_kv is not None:
            await hashing_kv.upsert({args_hash: {"return": output, "model": "model"}})

        return output

    return llm_func


def get_embedding_func(model):
    async def embedding_func(texts: list[str]) -> np.ndarray:
        outputs = model(texts)
        embedding_outputs = np.array([doc.embedding for doc in outputs])

        return embedding_outputs

    return embedding_func


def get_default_models_wrapper():
    # setup model functions
    default_embedding = embeddings.get_default()
    default_embedding_dim = len(default_embedding(["Hi"])[0].embedding)
    embedding_func = EmbeddingFunc(
        embedding_dim=default_embedding_dim,
        max_token_size=8192,
        func=get_embedding_func(default_embedding),
    )
    print("GraphRAG embedding dim", default_embedding_dim)

    default_llm = llms.get_default()
    llm_func = get_llm_func(default_llm)

    return llm_func, embedding_func, default_llm, default_embedding


def prepare_graph_index_path(graph_id: str):
    root_path = Path(filestorage_path) / graph_id
    input_path = root_path / "input"

    return root_path, input_path


def build_graphrag(working_dir, llm_func, embedding_func):
    graphrag_func = MiniRAG(
        working_dir=working_dir,
        llm_model_func=llm_func,
        llm_model_max_token_size=2048,
        embedding_func=embedding_func,
    )
    return graphrag_func


class MiniRAGIndexingPipeline(GraphRAGIndexingPipeline):
    """GraphRAG specific indexing pipeline"""

    prompts: dict[str, str] = {}

    @classmethod
    def get_user_settings(cls) -> dict:
        try:
            from minirag.prompt import PROMPTS

            blacklist_keywords = ["default", "response", "process"]
            return {
                prompt_name: {
                    "name": f"Prompt for '{prompt_name}'",
                    "value": content,
                    "component": "text",
                }
                for prompt_name, content in PROMPTS.items()
                if all(
                    keyword not in prompt_name.lower() for keyword in blacklist_keywords
                )
                and isinstance(content, str)
            }
        except ImportError as e:
            print(e)
            return {}

    def call_graphrag_index(self, graph_id: str, docs: list[Document]):
        from minirag.prompt import PROMPTS

        # modify the prompt if it is set in the settings
        for prompt_name, content in self.prompts.items():
            if prompt_name in PROMPTS:
                PROMPTS[prompt_name] = content

        _, input_path = prepare_graph_index_path(graph_id)
        input_path.mkdir(parents=True, exist_ok=True)

        (
            llm_func,
            embedding_func,
            default_llm,
            default_embedding,
        ) = get_default_models_wrapper()
        print(
            f"Indexing GraphRAG with LLM {default_llm} "
            f"and Embedding {default_embedding}..."
        )

        all_docs = [
            doc.text
            for doc in docs
            if doc.metadata.get("type", "text") == "text" and len(doc.text.strip()) > 0
        ]

        yield Document(
            channel="debug",
            text="[GraphRAG] Creating index... This can take a long time.",
        )

        # remove all .json files in the input_path directory (previous cache)
        json_files = glob.glob(f"{input_path}/*.json")
        for json_file in json_files:
            os.remove(json_file)

        # indexing
        graphrag_func = build_graphrag(
            input_path,
            llm_func=llm_func,
            embedding_func=embedding_func,
        )
        # output must be contain: Loaded graph from
        # ..input/graph_chunk_entity_relation.graphml with xxx nodes, xxx edges
        total_docs = len(all_docs)
        process_doc_count = 0
        yield Document(
            channel="debug",
            text=f"[GraphRAG] Indexed {process_doc_count} / {total_docs} documents.",
        )

        for doc_id in range(0, len(all_docs), INDEX_BATCHSIZE):
            cur_docs = all_docs[doc_id : doc_id + INDEX_BATCHSIZE]
            combined_doc = "\n".join(cur_docs)

            graphrag_func.insert(combined_doc)
            process_doc_count += len(cur_docs)
            yield Document(
                channel="debug",
                text=(
                    f"[GraphRAG] Indexed {process_doc_count} "
                    f"/ {total_docs} documents."
                ),
            )

        yield Document(
            channel="debug",
            text="[GraphRAG] Indexing finished.",
        )

    def stream(
        self, file_paths: str | Path | list[str | Path], reindex: bool = False, **kwargs
    ) -> Generator[
        Document, None, tuple[list[str | None], list[str | None], list[Document]]
    ]:
        file_ids, errors, all_docs = yield from super().stream(
            file_paths, reindex=reindex, **kwargs
        )

        return file_ids, errors, all_docs


class MiniRAGRetrieverPipeline(BaseFileIndexRetriever):
    """GraphRAG specific retriever pipeline"""

    Index = Param(help="The SQLAlchemy Index table")
    file_ids: list[str] = []
    search_type: str = "mini"

    @classmethod
    def get_user_settings(cls) -> dict:
        return {
            "search_type": {
                "name": "Search type",
                "value": "mini",
                "choices": ["mini", "light"],
                "component": "dropdown",
                "info": "Search type in the graph.",
            }
        }

    def _build_graph_search(self):
        file_id = self.file_ids[0]

        # retrieve the graph_id from the index
        with Session(engine) as session:
            graph_id = (
                session.query(self.Index.target_id)
                .filter(self.Index.source_id == file_id)
                .filter(self.Index.relation_type == "graph")
                .first()
            )
            graph_id = graph_id[0] if graph_id else None
            assert graph_id, f"GraphRAG index not found for file_id: {file_id}"

        _, input_path = prepare_graph_index_path(graph_id)
        input_path.mkdir(parents=True, exist_ok=True)

        llm_func, embedding_func, _, _ = get_default_models_wrapper()
        graphrag_func = build_graphrag(
            input_path,
            llm_func=llm_func,
            embedding_func=embedding_func,
        )
        print("search_type", self.search_type)
        query_params = QueryParam(mode=self.search_type, only_need_context=True)

        return graphrag_func, query_params

    def _to_document(self, header: str, context_text: str) -> RetrievedDocument:
        return RetrievedDocument(
            text=context_text,
            metadata={
                "file_name": header,
                "type": "table",
                "llm_trulens_score": 1.0,
            },
            score=1.0,
        )

    def run(
        self,
        text: str,
    ) -> list[RetrievedDocument]:
        if not self.file_ids:
            return []

        graphrag_func, query_params = self._build_graph_search()

        # only support non-graph visualization for now
        context = graphrag_func.query(text, query_params)

        documents = [
            RetrievedDocument(
                text=context,
                metadata={
                    "file_name": "GraphRAG {} Search".format(
                        query_params.mode.capitalize()
                    ),
                    "type": "table",
                },
            )
        ]

        return documents
