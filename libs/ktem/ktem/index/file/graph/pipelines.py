import os
import subprocess
from pathlib import Path
from shutil import rmtree
from typing import Generator
from uuid import uuid4

import pandas as pd
import tiktoken
from ktem.db.models import engine
from sqlalchemy.orm import Session
from theflow.settings import settings

from kotaemon.base import Document, Param, RetrievedDocument

from ..pipelines import BaseFileIndexRetriever, IndexDocumentPipeline, IndexPipeline
from .visualize import create_knowledge_graph, visualize_graph

try:
    from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
    from graphrag.query.indexer_adapters import (
        read_indexer_entities,
        read_indexer_relationships,
        read_indexer_reports,
        read_indexer_text_units,
    )
    from graphrag.query.input.loaders.dfs import store_entity_semantic_embeddings
    from graphrag.query.llm.oai.embedding import OpenAIEmbedding
    from graphrag.query.llm.oai.typing import OpenaiApiType
    from graphrag.query.structured_search.local_search.mixed_context import (
        LocalSearchMixedContext,
    )
    from graphrag.vector_stores.lancedb import LanceDBVectorStore
except ImportError:
    print(
        (
            "GraphRAG dependencies not installed. "
            "GraphRAG retriever pipeline will not work properly."
        )
    )


filestorage_path = Path(settings.KH_FILESTORAGE_PATH) / "graphrag"
filestorage_path.mkdir(parents=True, exist_ok=True)


def prepare_graph_index_path(graph_id: str):
    root_path = Path(filestorage_path) / graph_id
    input_path = root_path / "input"

    return root_path, input_path


class GraphRAGIndexingPipeline(IndexDocumentPipeline):
    """GraphRAG specific indexing pipeline"""

    def route(self, file_path: Path) -> IndexPipeline:
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

    def call_graphrag_index(self, input_path: str):
        # Construct the command
        command = [
            "python",
            "-m",
            "graphrag.index",
            "--root",
            input_path,
            "--reporter",
            "rich",
            "--init",
        ]

        # Run the command
        yield Document(
            channel="debug",
            text="[GraphRAG] Creating index... This can take a long time.",
        )
        result = subprocess.run(command, capture_output=True, text=True)
        print(result.stdout)
        command = command[:-1]

        # Run the command and stream stdout
        with subprocess.Popen(command, stdout=subprocess.PIPE, text=True) as process:
            if process.stdout:
                for line in process.stdout:
                    yield Document(channel="debug", text=line)

    def stream(
        self, file_paths: str | Path | list[str | Path], reindex: bool = False, **kwargs
    ) -> Generator[
        Document, None, tuple[list[str | None], list[str | None], list[Document]]
    ]:
        file_ids, errors, all_docs = yield from super().stream(
            file_paths, reindex=reindex, **kwargs
        )

        # assign graph_id to file_ids
        graph_id = self.store_file_id_with_graph_id(file_ids)
        # call GraphRAG index with docs and graph_id
        graph_index_path = self.write_docs_to_files(graph_id, all_docs)
        yield from self.call_graphrag_index(graph_index_path)

        return file_ids, errors, all_docs


class GraphRAGRetrieverPipeline(BaseFileIndexRetriever):
    """GraphRAG specific retriever pipeline"""

    Index = Param(help="The SQLAlchemy Index table")
    file_ids: list[str] = []

    @classmethod
    def get_user_settings(cls) -> dict:
        return {
            "search_type": {
                "name": "Search type",
                "value": "local",
                "choices": ["local", "global"],
                "component": "dropdown",
                "info": "Whether to use local or global search in the graph.",
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

        root_path, _ = prepare_graph_index_path(graph_id)
        output_path = root_path / "output"
        child_paths = sorted(
            list(output_path.iterdir()), key=lambda x: x.stem, reverse=True
        )

        # get the latest child path
        assert child_paths, "GraphRAG index output not found"
        latest_child_path = Path(child_paths[0]) / "artifacts"

        INPUT_DIR = latest_child_path
        LANCEDB_URI = str(INPUT_DIR / "lancedb")
        COMMUNITY_REPORT_TABLE = "create_final_community_reports"
        ENTITY_TABLE = "create_final_nodes"
        ENTITY_EMBEDDING_TABLE = "create_final_entities"
        RELATIONSHIP_TABLE = "create_final_relationships"
        TEXT_UNIT_TABLE = "create_final_text_units"
        COMMUNITY_LEVEL = 2

        # read nodes table to get community and degree data
        entity_df = pd.read_parquet(f"{INPUT_DIR}/{ENTITY_TABLE}.parquet")
        entity_embedding_df = pd.read_parquet(
            f"{INPUT_DIR}/{ENTITY_EMBEDDING_TABLE}.parquet"
        )
        entities = read_indexer_entities(
            entity_df, entity_embedding_df, COMMUNITY_LEVEL
        )

        # load description embeddings to an in-memory lancedb vectorstore
        # to connect to a remote db, specify url and port values.
        description_embedding_store = LanceDBVectorStore(
            collection_name="entity_description_embeddings",
        )
        description_embedding_store.connect(db_uri=LANCEDB_URI)
        if Path(LANCEDB_URI).is_dir():
            rmtree(LANCEDB_URI)
        _ = store_entity_semantic_embeddings(
            entities=entities, vectorstore=description_embedding_store
        )
        print(f"Entity count: {len(entity_df)}")

        # Read relationships
        relationship_df = pd.read_parquet(f"{INPUT_DIR}/{RELATIONSHIP_TABLE}.parquet")
        relationships = read_indexer_relationships(relationship_df)

        # Read community reports
        report_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_REPORT_TABLE}.parquet")
        reports = read_indexer_reports(report_df, entity_df, COMMUNITY_LEVEL)

        # Read text units
        text_unit_df = pd.read_parquet(f"{INPUT_DIR}/{TEXT_UNIT_TABLE}.parquet")
        text_units = read_indexer_text_units(text_unit_df)

        embedding_model = os.getenv("GRAPHRAG_EMBEDDING_MODEL")
        text_embedder = OpenAIEmbedding(
            api_key=os.getenv("OPENAI_API_KEY"),
            api_base=None,
            api_type=OpenaiApiType.OpenAI,
            model=embedding_model,
            deployment_name=embedding_model,
            max_retries=20,
        )
        token_encoder = tiktoken.get_encoding("cl100k_base")

        context_builder = LocalSearchMixedContext(
            community_reports=reports,
            text_units=text_units,
            entities=entities,
            relationships=relationships,
            covariates=None,
            entity_text_embeddings=description_embedding_store,
            embedding_vectorstore_key=EntityVectorStoreKey.ID,
            # if the vectorstore uses entity title as ids,
            # set this to EntityVectorStoreKey.TITLE
            text_embedder=text_embedder,
            token_encoder=token_encoder,
        )
        return context_builder

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
        entities = context_records.get("entities", [])
        relationships = context_records.get("relationships", [])
        reports = context_records.get("reports", [])
        sources = context_records.get("sources", [])

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
            title, content = row["title"], row["content"]
            context += f"\n\n<h5>Report <b>{title}</b></h5>\n"
            context += content
        docs.append(self._to_document(header, context))

        header = "\n<b>Sources</b>\n"
        context = ""
        for idx, row in sources.iterrows():
            title, content = row["id"], row["text"]
            context += f"\n\n<h5>Source <b>#{title}</b></h5>\n"
            context += content
        docs.append(self._to_document(header, context))

        return docs

    def plot_graph(self, context_records):
        relationships = context_records.get("relationships", [])
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
        context_builder = self._build_graph_search()

        local_context_params = {
            "text_unit_prop": 0.5,
            "community_prop": 0.1,
            "conversation_history_max_turns": 5,
            "conversation_history_user_turns_only": True,
            "top_k_mapped_entities": 10,
            "top_k_relationships": 10,
            "include_entity_rank": False,
            "include_relationship_weight": False,
            "include_community_rank": False,
            "return_candidate_context": False,
            "embedding_vectorstore_key": EntityVectorStoreKey.ID,
            # set this to EntityVectorStoreKey.TITLE i
            # f the vectorstore uses entity title as ids
            "max_tokens": 12_000,
            # change this based on the token limit you have on your model
            # (if you are using a model with 8k limit, a good setting could be 5000)
        }

        context_text, context_records = context_builder.build_context(
            query=text,
            conversation_history=None,
            **local_context_params,
        )
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
