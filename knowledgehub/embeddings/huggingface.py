from langchain.embeddings import HuggingFaceBgeEmbeddings as LCHuggingFaceEmbeddings

from kotaemon.embeddings.base import LangchainEmbeddings


class HuggingFaceEmbeddings(LangchainEmbeddings):
    """HuggingFace embeddings

    This class wraps around the Langchain HuggingFaceEmbeddings class
    """

    _lc_class = LCHuggingFaceEmbeddings
