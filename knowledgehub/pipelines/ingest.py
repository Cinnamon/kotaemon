import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from llama_index.readers.base import BaseReader
from theflow import Node
from theflow.utils.modules import ObjectInitDeclaration as _

from kotaemon.base import BaseComponent
from kotaemon.embeddings import AzureOpenAIEmbeddings
from kotaemon.loaders import (
    AutoReader,
    DirectoryReader,
    MathpixPDFReader,
    OCRReader,
    PandasExcelReader,
)
from kotaemon.parsers.splitter import SimpleNodeParser
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
    vector_store: _[BaseVectorStore] = _(InMemoryVectorStore)
    doc_store: _[BaseDocumentStore] = _(InMemoryDocumentStore)

    embedding: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings.withx(
        model="text-embedding-ada-002",
        deployment="dummy-q2-text-embedding",
        openai_api_base="https://bleh-dummy-2.openai.azure.com/",
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
    )

    def get_reader(self, input_files: List[Union[str, Path]]):
        # document parsers
        file_extractor: Dict[str, BaseReader] = {
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
    def text_splitter(self) -> SimpleNodeParser:
        return SimpleNodeParser(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )

    def run(
        self,
        file_path_list: Union[List[Union[str, Path]], Union[str, Path]],
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

            self.indexing_vector_pipeline(nodes)
            # persist right after indexing
            self.indexing_vector_pipeline.save(file_storage_path)
        else:
            self.indexing_vector_pipeline.load(file_storage_path)

    def to_retrieving_pipeline(self, top_k=3):
        retrieving_pipeline = RetrieveDocumentFromVectorStorePipeline(
            vector_store=self.vector_store,
            doc_store=self.doc_store,
            embedding=self.embedding,
            top_k=top_k,
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
            **kwargs
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
            **kwargs
        )
        agent_pipeline.add_search_tool()
        return agent_pipeline
