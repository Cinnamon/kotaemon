from pathlib import Path

from kotaemon.base import Document
from kotaemon.loaders import AutoReader, UnstructuredReader
from langchain.schema import Document as LangchainDocument
from llama_index.node_parser import SimpleNodeParser


def test_pdf_reader():
    reader = AutoReader("PDFReader")
    dirpath = Path(__file__).parent
    documents = reader.load_data(dirpath / "resources/dummy.pdf")

    # check document reader output
    assert len(documents) == 1

    first_doc = documents[0]
    assert isinstance(first_doc, Document)
    assert first_doc.text.lower().replace(" ", "") == "dummypdffile"

    langchain_doc = first_doc.to_langchain_format()
    assert isinstance(langchain_doc, LangchainDocument)

    # test chunking using NodeParser from llama-index
    node_parser = SimpleNodeParser.from_defaults(chunk_size=100, chunk_overlap=20)
    nodes = node_parser.get_nodes_from_documents(documents)
    assert len(nodes) > 0


def test_unstructured_pdf_reader():
    reader = UnstructuredReader()
    dirpath = Path(__file__).parent
    input_path = dirpath / "resources/dummy.pdf"
    documents = reader.load_data(input_path)

    # check document reader output
    assert len(documents) == 1

    first_doc = documents[0]
    assert isinstance(first_doc, Document)
    assert first_doc.text.lower().replace(" ", "") == "dummypdffile"

    # split documents mode
    documents = reader.load_data(input_path, split_documents=True)
    # check document reader output
    assert len(documents) == 1
