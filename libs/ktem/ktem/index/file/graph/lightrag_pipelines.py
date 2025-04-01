import asyncio
import glob
import logging
import os
import re
from pathlib import Path
from typing import Generator

import numpy as np
import pandas as pd
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
from .visualize import create_knowledge_graph, visualize_graph

try:
    from lightrag import LightRAG, QueryParam

    # newer versions of LightRAG needs to be initialized before using
    from lightrag.kg.shared_storage import initialize_pipeline_status
    from lightrag.operate import (
        _find_most_related_edges_from_entities,
        _find_most_related_text_unit_from_entities,
    )
    from lightrag.utils import EmbeddingFunc, compute_args_hash

except ImportError:
    print(
        (
            "LightRAG dependencies not installed. "
            "Try `pip install git+https://github.com/HKUDS/LightRAG.git` to install. "
            "LighthRAG retriever pipeline will not work properly."
        )
    )


logging.getLogger("lightrag").setLevel(logging.INFO)


filestorage_path = Path(settings.KH_FILESTORAGE_PATH) / "lightrag"
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

        try:
            output = await _call_model(model, input_messages)
        except Exception as e:
            logging.error(f"Failed to call LLM API after 3 retries: {str(e)}")
            raise

        print("-" * 50)
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


def list_of_list_to_df(data: list[list]) -> pd.DataFrame:
    df = pd.DataFrame(data[1:], columns=data[0])
    return df


def clean_quote(input: str) -> str:
    return re.sub(r"[\"']", "", input)


async def lightrag_build_local_query_context(
    graph_func,
    query,
    query_param,
):
    knowledge_graph_inst = graph_func.chunk_entity_relation_graph
    entities_vdb = graph_func.entities_vdb
    text_chunks_db = graph_func.text_chunks

    results = await entities_vdb.query(query, top_k=query_param.top_k)
    if not len(results):
        raise ValueError("No results found")

    node_datas = await asyncio.gather(
        *[knowledge_graph_inst.get_node(r["entity_name"]) for r in results]
    )
    node_degrees = await asyncio.gather(
        *[knowledge_graph_inst.node_degree(r["entity_name"]) for r in results]
    )
    node_datas = [
        {**n, "entity_name": k["entity_name"], "rank": d}
        for k, n, d in zip(results, node_datas, node_degrees)
        if n is not None
    ]

    try:
        use_text_units = await _find_most_related_text_unit_from_entities(
            node_datas, query_param, text_chunks_db, knowledge_graph_inst
        )
    except Exception:
        use_text_units = []

    try:
        use_relations = await _find_most_related_edges_from_entities(
            node_datas, query_param, knowledge_graph_inst
        )
    except Exception:
        use_relations = []

    logging.info(
        f"Local query uses {len(node_datas)} entities, "
        f"{len(use_relations)} relations, {len(use_text_units)} text units"
    )

    entites_section_list = [["id", "entity", "type", "description", "rank"]]
    for i, n in enumerate(node_datas):
        entites_section_list.append(
            [
                str(i),
                clean_quote(n["entity_name"]),
                n.get("entity_type", "UNKNOWN"),
                clean_quote(n.get("description", "UNKNOWN")),
                n["rank"],
            ]
        )
    entities_df = list_of_list_to_df(entites_section_list)

    relations_section_list = [
        ["id", "source", "target", "description", "keywords", "weight", "rank"]
    ]
    for i, e in enumerate(use_relations):
        relations_section_list.append(
            [
                str(i),
                clean_quote(e["src_tgt"][0]),
                clean_quote(e["src_tgt"][1]),
                clean_quote(e["description"]),
                e["keywords"],
                e["weight"],
                e["rank"],
            ]
        )
    relations_df = list_of_list_to_df(relations_section_list)

    text_units_section_list = [["id", "content"]]
    for i, t in enumerate(use_text_units):
        text_units_section_list.append([str(i), t["content"]])
    sources_df = list_of_list_to_df(text_units_section_list)

    return entities_df, relations_df, sources_df


def build_graphrag(working_dir, llm_func, embedding_func):
    graphrag_func = LightRAG(
        working_dir=working_dir,
        llm_model_func=llm_func,
        embedding_func=embedding_func,
    )

    # newer versions of LightRAG needs to be initialized before using
    asyncio.run(graphrag_func.initialize_storages())
    asyncio.run(initialize_pipeline_status())

    return graphrag_func


class LightRAGIndexingPipeline(GraphRAGIndexingPipeline):
    """GraphRAG specific indexing pipeline"""

    prompts: dict[str, str] = {}
    collection_graph_id: str
    index_batch_size: int = INDEX_BATCHSIZE

    def store_file_id_with_graph_id(self, file_ids: list[str | None]):
        if not settings.USE_GLOBAL_GRAPHRAG:
            return super().store_file_id_with_graph_id(file_ids)

        # Use the collection-wide graph ID for LightRAG
        graph_id = self.collection_graph_id

        # Record all files under this graph_id
        with Session(engine) as session:
            for file_id in file_ids:
                if not file_id:
                    continue
                # Check if mapping already exists
                existing = (
                    session.query(self.Index)
                    .filter(
                        self.Index.source_id == file_id,
                        self.Index.target_id == graph_id,
                        self.Index.relation_type == "graph",
                    )
                    .first()
                )
                if not existing:
                    node = self.Index(
                        source_id=file_id,
                        target_id=graph_id,
                        relation_type="graph",
                    )
                    session.add(node)
            session.commit()

        return graph_id

    @classmethod
    def get_user_settings(cls) -> dict:
        try:
            from lightrag.prompt import PROMPTS

            blacklist_keywords = ["default", "response", "process"]
            settings_dict = {
                "batch_size": {
                    "name": (
                        "Index batch size " "(reduce if you have rate limit issues)"
                    ),
                    "value": INDEX_BATCHSIZE,
                    "component": "number",
                }
            }
            settings_dict.update(
                {
                    prompt_name: {
                        "name": f"Prompt for '{prompt_name}'",
                        "value": content,
                        "component": "text",
                    }
                    for prompt_name, content in PROMPTS.items()
                    if all(
                        keyword not in prompt_name.lower()
                        for keyword in blacklist_keywords
                    )
                    and isinstance(content, str)
                }
            )
            return settings_dict
        except ImportError as e:
            print(e)
            return {}

    def call_graphrag_index(self, graph_id: str, docs: list[Document]):
        from lightrag.prompt import PROMPTS

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
            text="[GraphRAG] Creating/Updating index... This can take a long time.",
        )

        # Check if graph already exists
        graph_file = input_path / "graph_chunk_entity_relation.graphml"
        is_incremental = graph_file.exists()

        # Only clear cache if it's a new graph
        if not is_incremental:
            json_files = glob.glob(f"{input_path}/*.json")
            for json_file in json_files:
                os.remove(json_file)

        # Initialize or load existing GraphRAG
        graphrag_func = build_graphrag(
            input_path,
            llm_func=llm_func,
            embedding_func=embedding_func,
        )

        total_docs = len(all_docs)
        process_doc_count = 0
        yield Document(
            channel="debug",
            text=(
                f"[GraphRAG] {'Updating' if is_incremental else 'Creating'} index: "
                f"{process_doc_count} / {total_docs} documents."
            ),
        )

        for doc_id in range(0, len(all_docs), self.index_batch_size):
            cur_docs = all_docs[doc_id : doc_id + self.index_batch_size]
            combined_doc = "\n".join(cur_docs)

            # Use insert for incremental updates
            graphrag_func.insert(combined_doc)
            process_doc_count += len(cur_docs)
            yield Document(
                channel="debug",
                text=(
                    f"[GraphRAG] {'Updated' if is_incremental else 'Indexed'} "
                    f"{process_doc_count} / {total_docs} documents."
                ),
            )

        yield Document(
            channel="debug",
            text=f"[GraphRAG] {'Update' if is_incremental else 'Indexing'} finished.",
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


class LightRAGRetrieverPipeline(BaseFileIndexRetriever):
    """GraphRAG specific retriever pipeline"""

    Index = Param(help="The SQLAlchemy Index table")
    file_ids: list[str] = []
    search_type: str = "local"

    @classmethod
    def get_user_settings(cls) -> dict:
        return {
            "search_type": {
                "name": "Search type",
                "value": "local",
                "choices": ["local", "global", "hybrid"],
                "component": "dropdown",
                "info": "Whether to use local or global search in the graph.",
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

    def format_context_records(
        self, entities, relationships, sources
    ) -> list[RetrievedDocument]:
        docs = []
        context: str = ""

        # entities current parsing error
        header = "<b>Entities</b>\n"
        context = entities[["entity", "description"]].to_markdown(index=False)
        docs.append(self._to_document(header, context))

        header = "\n<b>Relationships</b>\n"
        context = relationships[["source", "target", "description"]].to_markdown(
            index=False
        )
        docs.append(self._to_document(header, context))

        header = "\n<b>Sources</b>\n"
        context = ""
        for _, row in sources.iterrows():
            title, content = row["id"], row["content"]
            context += f"\n\n<h5>Source <b>#{title}</b></h5>\n"
            context += content
        docs.append(self._to_document(header, context))

        return docs

    def plot_graph(self, relationships):
        G = create_knowledge_graph(relationships)
        plot = visualize_graph(G)
        return plot

    def run(
        self,
        text: str,
    ) -> list[RetrievedDocument]:
        if not self.file_ids:
            return []

        graphrag_func, query_params = self._build_graph_search()

        # only local mode support graph visualization
        if query_params.mode == "local":
            entities, relationships, sources = asyncio.run(
                lightrag_build_local_query_context(graphrag_func, text, query_params)
            )
            documents = self.format_context_records(entities, relationships, sources)
            plot = self.plot_graph(relationships)
            documents += [
                RetrievedDocument(
                    text="",
                    metadata={
                        "file_name": "GraphRAG",
                        "type": "plot",
                        "data": plot,
                    },
                ),
            ]
        else:
            context = graphrag_func.query(text, query_params)

            # account for missing ``` for closing code block
            context += "\n```"

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
