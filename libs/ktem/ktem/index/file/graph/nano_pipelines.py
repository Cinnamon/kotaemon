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

try:
    from nano_graphrag import GraphRAG, QueryParam
except ImportError:
    print(
        (
            "Nano-GraphRAG dependencies not installed. Try pip install nano-graphrag"
            "Nao-GraphRAG retriever pipeline will not work properly."
        )
    )


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
                df = pd.read_csv(StringIO(csv_content_processed), engine='python')
                dataframes[section_name] = df
            except Exception as e:
                print(f"Error parsing CSV for section {section_name}: {e}")
                dataframes[section_name] = None
        else:
            dataframes[section_name] = None

    # Access the DataFrames
    reports = dataframes.get('Reports', [])
    entities = dataframes.get('Entities', [])
    relationships = dataframes.get('Relationships', [])
    sources = dataframes.get('Sources', [])

    return reports, entities, relationships, sources


class NaNoGraphRAGIndexingPipeline(IndexDocumentPipeline):
    """GraphRAG specific indexing pipeline"""

    def route(self, file_path: str | Path) -> IndexPipeline:
        """Simply disable the splitter (chunking) for this pipeline"""
        pipeline = super().route(file_path)
        pipeline.splitter = None

        return pipeline

    def store_file_id_with_graph_id(self, file_ids: list[str | None]):
        # create new graph_id and assign them to doc_id in self.Index
        # record in the index
        graph_id = str(uuid4())
        with Session(engine) as session:
            nodes = []
            for file_id in file_ids:
                if not file_id:
                    continue
                nodes.append(
                    self.Index(
                        source_id=file_id,
                        target_id=graph_id,
                        relation_type="graph",
                    )
                )

            session.add_all(nodes)
            session.commit()

        return graph_id

    def write_docs_to_files(self, graph_id: str, docs: list[Document]):
        root_path, input_path = prepare_graph_index_path(graph_id)
        input_path.mkdir(parents=True, exist_ok=True)

        for doc in docs:
            if doc.metadata.get("type", "text") == "text":
                with open(input_path / f"{doc.doc_id}.txt", "w") as f:
                    f.write(doc.text)

        return root_path
    
    def graph_indexing(self, graph_id: str, docs: list[Document]):
        root_path, input_path = prepare_graph_index_path(graph_id)
        input_path.mkdir(parents=True, exist_ok=True)
        
        all_docs = [doc.text for doc in docs if doc.metadata.get("type", "text") == "text"]

        print(f"Indexing {len(all_docs)} documents...")
        print(all_docs)

        ## indexing 
        graphrag_func = GraphRAG(working_dir=input_path, enable_naive_rag=True,
                         embedding_func_max_async=4)
        
        graphrag_func.insert(all_docs)
        ## output must be contain: Loaded graph from ..input/graph_chunk_entity_relation.graphml with xxx nodes, xxx edges

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

    @classmethod
    def get_user_settings(cls) -> dict:
        return {
            "search_type": {
                "name": "Search type",
                "value": "local",
                "choices": ["local", "global", "naive"],
                "component": "dropdown",
                "info": "Whether to use naive or local or global search in the graph.",
            }
        }

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

         ## indexing 

        root_path, input_path = prepare_graph_index_path(graph_id)
        input_path.mkdir(parents=True, exist_ok=True)

        graphrag_func = GraphRAG(working_dir=input_path, enable_naive_rag=True,
                         embedding_func_max_async=4)

        query_params = QueryParam(mode='local', only_need_context=True)


        return graphrag_func, query_params #context_builder

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

    def format_context_records(self, context_records) -> list[RetrievedDocument]:

        ## Extract CSV content from the context
        reports, entities, relationships, sources = extract_csv_output(context_records)

        docs = []

        context: str = ""

        header = "<b>Entities</b>\n"
        context = entities[["entity", "description"]].to_markdown(index=False)
        docs.append(self._to_document(header, context))

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

    def generate_relevant_scores(self, text, documents: list[RetrievedDocument]):
        return documents

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
