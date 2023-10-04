from langchain.embeddings import OpenAIEmbeddings as LCOpenAIEmbeddings

from .base import LangchainEmbeddings


class OpenAIEmbeddings(LangchainEmbeddings):
    """OpenAI embeddings.

    This method is wrapped around the Langchain OpenAIEmbeddings class.
    """

    _lc_class = LCOpenAIEmbeddings


class AzureOpenAIEmbeddings(LangchainEmbeddings):
    """Azure OpenAI embeddings.

    This method is wrapped around the Langchain OpenAIEmbeddings class.
    """

    _lc_class = LCOpenAIEmbeddings

    def __init__(self, **params):
        params["openai_api_type"] = "azure"
        super().__init__(**params)
