from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Sequence

from llama_index.readers.base import BaseReader
from theflow import Node
from theflow.utils.modules import ObjectInitDeclaration as _

from kotaemon.base import BaseComponent
from kotaemon.embeddings import AzureOpenAIEmbeddings
from kotaemon.indices.extractors import BaseDocParser
from kotaemon.indices.rankings import BaseReranking
from kotaemon.indices.splitters import TokenSplitter
from kotaemon.loaders import (
    AutoReader,
    DirectoryReader,
    MathpixPDFReader,
    OCRReader,
    PandasExcelReader,
)
from kotaemon.pipelines.agents import BaseAgent
from kotaemon.pipelines.indexing import IndexVectorStoreFromDocumentPipeline
from kotaemon.pipelines.retrieving import RetrieveDocumentFromVectorStorePipeline
from kotaemon.storages import (
    BaseDocumentStore,
    BaseVectorStore,
    InMemoryDocumentStore,
    InMemoryVectorStore,
)

from .qa import AgentQAPipeline, QuestionAnsweringPipeline
from .utils import file_names_to_collection_name


class ReaderIndexingPipeline(BaseComponent):
    """
    Indexing pipeline which takes input from list of files
    and perform ingestion to vectorstore
    """

    # Expose variables for users to switch in prompt ui
    storage_path: Path = Path("./storage")
    reader_name: str = "normal"  # "normal", "mathpix" or "ocr"
    chunk_size: int = 1024
    chunk_overlap: int = 256
    vector_store: BaseVectorStore = _(InMemoryVectorStore)
    doc_store: BaseDocumentStore = _(InMemoryDocumentStore)
    doc_parsers: list[BaseDocParser] = []

    embedding: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings.withx(
        model="text-embedding-ada-002",
        deployment="dummy-q2-text-embedding",
        azure_endpoint="https://bleh-dummy.openai.azure.com/",
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        chunk_size=16,
    )

    def get_reader(self, input_files: list[str | Path]):
        # document parsers
        file_extractor: dict[str, BaseReader | AutoReader] = {
            ".xlsx": PandasExcelReader(),
        }
        if self.reader_name == "normal":
            file_extractor[".pdf"] = AutoReader("UnstructuredReader")
        elif self.reader_name == "ocr":
            file_extractor[".pdf"] = OCRReader()
        else:
            file_extractor[".pdf"] = MathpixPDFReader()
        main_reader = DirectoryReader(
            input_files=input_files,
            file_extractor=file_extractor,
        )
        return main_reader

    @Node.auto(depends_on=["doc_store", "vector_store", "embedding"])
    def indexing_vector_pipeline(self):
        return IndexVectorStoreFromDocumentPipeline(
            doc_store=self.doc_store,
            vector_store=self.vector_store,
            embedding=self.embedding,
        )

    @Node.auto(depends_on=["chunk_size", "chunk_overlap"])
    def text_splitter(self) -> TokenSplitter:
        return TokenSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

    def run(
        self,
        file_path_list: list[str | Path] | str | Path,
        force_reindex: Optional[bool] = False,
    ):
        self.storage_path.mkdir(exist_ok=True)

        if not isinstance(file_path_list, list):
            file_path_list = [file_path_list]

        self.file_name_list = [Path(path).stem for path in file_path_list]
        collection_name = file_names_to_collection_name(self.file_name_list)

        file_storage_path = self.storage_path / collection_name

        # skip indexing if storage path exist
        if force_reindex or not file_storage_path.exists():
            file_storage_path.mkdir(exist_ok=True)
            # reader call
            documents = self.get_reader(input_files=file_path_list)()
            nodes = self.text_splitter(documents)
            self.log_progress(".num_docs", num_docs=len(nodes))

            # document parsers call
            if self.doc_parsers:
                for parser in self.doc_parsers:
                    nodes = parser(nodes)

            self.indexing_vector_pipeline(nodes)
            # persist right after indexing
            self.indexing_vector_pipeline.save(file_storage_path)
        else:
            self.indexing_vector_pipeline.load(file_storage_path)

    def to_retrieving_pipeline(self, top_k=3, rerankers: Sequence[BaseReranking] = []):
        retrieving_pipeline = RetrieveDocumentFromVectorStorePipeline(
            vector_store=self.vector_store,
            doc_store=self.doc_store,
            embedding=self.embedding,
            top_k=top_k,
            rerankers=rerankers,
        )
        return retrieving_pipeline

    def to_qa_pipeline(self, llm: BaseComponent, **kwargs):
        qa_pipeline = QuestionAnsweringPipeline(
            storage_path=self.storage_path,
            file_name_list=self.file_name_list,
            vector_store=self.vector_store,
            doc_store=self.doc_store,
            embedding=self.embedding,
            llm=llm,
            **kwargs,
        )
        return qa_pipeline

    def to_agent_pipeline(self, agent: BaseAgent, **kwargs):
        agent_pipeline = AgentQAPipeline(
            storage_path=self.storage_path,
            file_name_list=self.file_name_list,
            vector_store=self.vector_store,
            doc_store=self.doc_store,
            embedding=self.embedding,
            agent=agent,
            **kwargs,
        )
        agent_pipeline.add_search_tool()
        return agent_pipeline
