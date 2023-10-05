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

        # openai.error.InvalidRequestError: Too many inputs. The max number of
        # inputs is 16.  We hope to increase the number of inputs per request
        # soon. Please contact us through an Azure support request at:
        # https://go.microsoft.com/fwlink/?linkid=2213926 for further questions.
        params["chunk_size"] = 16
        super().__init__(**params)
