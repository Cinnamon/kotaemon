import os
import shutil
import subprocess
from pathlib import Path
from shutil import rmtree
from typing import Generator
from uuid import uuid4

import pandas as pd
import tiktoken
import yaml
from decouple import config
from ktem.db.models import engine
from sqlalchemy.orm import Session
from theflow.settings import settings
import re
from io import StringIO
from dotenv import load_dotenv
load_dotenv()

from kotaemon.base import Document, Param, RetrievedDocument
from ..pipelines import BaseFileIndexRetriever, IndexDocumentPipeline, IndexPipeline
from .visualize import create_knowledge_graph, visualize_graph
from .pipelines import GraphRAGIndexingPipeline 

try:
    from nano_graphrag import GraphRAG, QueryParam
    from nano_graphrag.base import BaseKVStorage
    from nano_graphrag._utils import compute_args_hash, wrap_embedding_func_with_attrs

except ImportError:
    print(
        (
            "Nano-GraphRAG dependencies not installed. Try pip install nano-graphrag"
            "Nao-GraphRAG retriever pipeline will not work properly."
        )
    )

import logging

try:
    import ollama
except ImportError:
    print("""Ollama dependencies not installed. Try pip install ollama
            Try setup ollama and local embedding and local llm model following the link: https://github.com/Cinnamon/kotaemon/blob/main/docs/local_model.md#note
            """
    )

import numpy as np
logging.basicConfig(level=logging.WARNING)
logging.getLogger("nano-graphrag").setLevel(logging.INFO)


filestorage_path = Path(settings.KH_FILESTORAGE_PATH) / "nano_graphrag"
filestorage_path.mkdir(parents=True, exist_ok=True)


def prepare_graph_index_path(graph_id: str):
    root_path = Path(filestorage_path) / graph_id
    input_path = root_path / "input"

    return root_path, input_path

# Function to extract CSV content from a section
def extract_csv_content(section_content):
    matches = re.findall(r'```csv(.*?)```', section_content, re.DOTALL)
    if matches:
        csv_content = matches[0].strip()
        return csv_content
    else:
        return None
    
def extract_csv_output(context):
    sections = re.split(r'-----([A-Za-z]+)-----', context)
    section_dict = {}
    for i in range(1, len(sections), 2):
        section_name = sections[i].strip()
        section_content = sections[i+1].strip()
        section_dict[section_name] = section_content
        
    # Read CSV content into DataFrames
    dataframes = {}
    for section_name, section_content in section_dict.items():
        csv_content = extract_csv_content(section_content)
        if csv_content:
            # Preprocess the CSV content to handle the delimiter
            # Replace ',\t' with ','
            csv_content_processed = csv_content.replace(',\t', ',')
            # csv_content_processed = csv_content
            # Now read the CSV using ',' as the delimiter
            try:
                df = pd.read_csv(StringIO(csv_content_processed), engine='python') #, sep=',', quotechar='"')
                dataframes[section_name] = df
            except Exception as e:
                print(f"Error parsing CSV for section {section_name}: {e}")
                dataframes[section_name] = None
        else:
            dataframes[section_name] = None

    # Access the DataFrames
    reports = dataframes.get('Reports', [])
    entities = dataframes.get('Entities', pd.DataFrame({"entity": [""], "description": [""]})) #[]
    relationships = dataframes.get('Relationships', [])
    sources = dataframes.get('Sources', [])

    return reports, entities, relationships, sources

##ref: https://github.com/gusye1234/nano-graphrag/blob/main/examples/using_ollama_as_llm_and_embedding.py

# Assumed embedding model settings
EMBEDDING_MODEL = os.getenv("LOCAL_MODEL_EMBEDDINGS", "nomic-embed-text") # "nomic-embed-text"
EMBEDDING_MODEL_DIM = os.getenv("LOCAL_MODEL_EMBEDDINGS_DIM", 768)
EMBEDDING_MODEL_MAX_TOKENS = os.getenv("LOCAL_MODEL_EMBEDDINGS_MAX_TOKENS", 512)

LOCAL_MODEL = os.getenv("LOCAL_MODEL", "llama3.1:8b")

def remove_if_exist(file):
    if os.path.exists(file):
        os.remove(file)


async def ollama_model_if_cache(
    prompt, system_prompt=None, history_messages=[], **kwargs
) -> str:
    # remove kwargs that are not supported by ollama
    kwargs.pop("max_tokens", None)
    kwargs.pop("response_format", None)

    ollama_client = ollama.AsyncClient()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    # Get the cached response if having-------------------
    hashing_kv: BaseKVStorage = kwargs.pop("hashing_kv", None)
    messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})
    if hashing_kv is not None:
        args_hash = compute_args_hash(LOCAL_MODEL, messages)
        if_cache_return = await hashing_kv.get_by_id(args_hash)
        if if_cache_return is not None:
            return if_cache_return["return"]
    # -----------------------------------------------------
    response = await ollama_client.chat(model=LOCAL_MODEL, messages=messages, **kwargs)

    result = response["message"]["content"]
    # Cache the response if having-------------------
    if hashing_kv is not None:
        await hashing_kv.upsert({args_hash: {"return": result, "model": LOCAL_MODEL}})
    # -----------------------------------------------------
    return result

# We're using Ollama to generate embeddings for the BGE model
@wrap_embedding_func_with_attrs(
    embedding_dim=EMBEDDING_MODEL_DIM,
    max_token_size=EMBEDDING_MODEL_MAX_TOKENS,
)
async def ollama_embedding(texts: list[str]) -> np.ndarray:
    embed_text = []
    for text in texts:
        data = ollama.embeddings(model=EMBEDDING_MODEL, prompt=text)
        embed_text.append(data["embedding"])

    return embed_text

def build_graphrag(working_dir):

    if os.getenv("USE_CUSTOMIZED_GRAPHRAG_SETTING") == "true":

        try:

            print("Using customized NaNoGraphRAG setting with local llm and embedding model from ollama !!")
            graphrag_func = GraphRAG(
                working_dir=working_dir,
                best_model_func=ollama_model_if_cache,
                cheap_model_func=ollama_model_if_cache,
                embedding_func=ollama_embedding,
            )
        except:
            print("You need check ollama local model and embedding model.Using default NaNoGraphRAG setting, you need OPENAI_API_KEY in .env file")
            graphrag_func = GraphRAG(working_dir=working_dir, 
                                 #enable_naive_rag=True,
                                embedding_func_max_async=4)

    else:
        print("Using default NaNoGraphRAG setting, you need OPENAI_API_KEY in .env file")
        graphrag_func = GraphRAG(working_dir=working_dir, 
                                 #enable_naive_rag=True,
                                embedding_func_max_async=4)
        
    return graphrag_func


class NaNoGraphRAGIndexingPipeline(GraphRAGIndexingPipeline):
    """GraphRAG specific indexing pipeline"""

    
    def graph_indexing(self, graph_id: str, docs: list[Document]):
        root_path, input_path = prepare_graph_index_path(graph_id)
        input_path.mkdir(parents=True, exist_ok=True)
        
        all_docs = [doc.text for doc in docs if doc.metadata.get("type", "text") == "text"]

        print(f"Indexing {len(all_docs)} documents...")
        print(all_docs)


        ###remove cache
        remove_if_exist(f"{input_path}/vdb_entities.json")
        remove_if_exist(f"{input_path}/kv_store_full_docs.json")
        remove_if_exist(f"{input_path}/kv_store_text_chunks.json")
        remove_if_exist(f"{input_path}/kv_store_community_reports.json")
        remove_if_exist(f"{input_path}/graph_chunk_entity_relation.graphml")

        ## indexing 
        graphrag_func = build_graphrag(input_path)
        
        ## output must be contain: Loaded graph from ..input/graph_chunk_entity_relation.graphml with xxx nodes, xxx edges
        graphrag_func.insert(all_docs)

    def stream(
        self, file_paths: str | Path | list[str | Path], reindex: bool = False, **kwargs
    ) -> Generator[
        Document, None, tuple[list[str | None], list[str | None], list[Document]]
    ]:
        file_ids, errors, all_docs = yield from super().stream(
            file_paths, reindex=reindex, **kwargs
        )
        
        yield Document(
            channel="debug",
            text="[GraphRAG] Creating index... This can take a long time.",
        )
        
        # assign graph_id to file_ids
        graph_id = self.store_file_id_with_graph_id(file_ids)
        # call GraphRAG index with docs and graph_id

        yield from self.graph_indexing(graph_id, all_docs)

        return file_ids, errors, all_docs


class NaNoGraphRAGRetrieverPipeline(BaseFileIndexRetriever):
    """GraphRAG specific retriever pipeline"""

    Index = Param(help="The SQLAlchemy Index table")
    file_ids: list[str] = []


    def _build_graph_search(self):
        assert (
            len(self.file_ids) <= 1
        ), "GraphRAG retriever only supports one file_id at a time"

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

        root_path, input_path = prepare_graph_index_path(graph_id)
        input_path.mkdir(parents=True, exist_ok=True)

        graphrag_func = build_graphrag(input_path)

        query_params = QueryParam(mode='local', only_need_context=True)


        return graphrag_func, query_params

    def format_context_records(self, context_records) -> list[RetrievedDocument]:

        ## Extract CSV content from the context
        reports, entities, relationships, sources = extract_csv_output(context_records)

        docs = []

        context: str = ""

        # header = "<b>Entities</b>\n"
        # context = entities[["entity", "description"]].to_markdown(index=False)
        # docs.append(self._to_document(header, context)) # entities current parsing error

        header = "\n<b>Relationships</b>\n"
        context = relationships[["source", "target", "description"]].to_markdown(
            index=False
        )
        docs.append(self._to_document(header, context))

        header = "\n<b>Reports</b>\n"
        context = ""
        for idx, row in reports.iterrows():
            title, content = row["id"], row["content"] # not contain title
            context += f"\n\n<h5>Report <b>{title}</b></h5>\n"
            context += content
        docs.append(self._to_document(header, context))

        header = "\n<b>Sources</b>\n"
        context = ""
        for idx, row in sources.iterrows():
            title, content = row["id"], row["content"]
            context += f"\n\n<h5>Source <b>#{title}</b></h5>\n"
            context += content
        docs.append(self._to_document(header, context))

        return docs

    def plot_graph(self, context_records):
        reports, entities, relationships, sources = extract_csv_output(context_records)
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
        context_records = graphrag_func.query(text, param = query_params)

        documents = self.format_context_records(context_records)
        plot = self.plot_graph(context_records)

        return documents + [
            RetrievedDocument(
                text="",
                metadata={
                    "file_name": "GraphRAG",
                    "type": "plot",
                    "data": plot,
                },
            ),
        ]
