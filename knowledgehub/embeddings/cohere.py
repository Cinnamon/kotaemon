from langchain.embeddings import CohereEmbeddings as LCCohereEmbeddings

from kotaemon.embeddings.base import LangchainEmbeddings


class CohereEmbdeddings(LangchainEmbeddings):
    """Cohere embeddings.

    This class wraps around the Langchain CohereEmbeddings class.
    """

    _lc_class = LCCohereEmbeddings
