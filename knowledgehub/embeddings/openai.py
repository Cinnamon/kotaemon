from langchain import embeddings as lcembeddings

from .base import LangchainEmbeddings


class OpenAIEmbeddings(LangchainEmbeddings):
    """OpenAI embeddings.

    This method is wrapped around the Langchain OpenAIEmbeddings class.
    """

    _lc_class = lcembeddings.OpenAIEmbeddings


class AzureOpenAIEmbeddings(LangchainEmbeddings):
    """Azure OpenAI embeddings.

    This method is wrapped around the Langchain AzureOpenAIEmbeddings class.
    """

    _lc_class = lcembeddings.AzureOpenAIEmbeddings
