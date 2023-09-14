from langchain.embeddings import OpenAIEmbeddings as LCOpenAIEmbeddings

from .base import LangchainEmbeddings


class OpenAIEmbeddings(LangchainEmbeddings):
    _lc_class = LCOpenAIEmbeddings


class AzureOpenAIEmbeddings(LangchainEmbeddings):
    _lc_class = LCOpenAIEmbeddings

    def __init__(self, **params):
        params["openai_api_type"] = "azure"
        super().__init__(**params)
