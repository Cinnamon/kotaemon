from pathlib import Path

from decouple import config
from platformdirs import user_cache_dir
from theflow.settings.default import *  # noqa

user_cache_dir = Path(
    user_cache_dir(str(config("KH_APP_NAME", default="ktem")), "Cinnamon")
)
user_cache_dir.mkdir(parents=True, exist_ok=True)


COHERE_API_KEY = config("COHERE_API_KEY", default="")
KH_MODE = "dev"
KH_FEATURE_USER_MANAGEMENT = False
KH_FEATURE_USER_MANAGEMENT_ADMIN = str(
    config("KH_FEATURE_USER_MANAGEMENT_ADMIN", default="admin")
)
KH_FEATURE_USER_MANAGEMENT_PASSWORD = str(
    config("KH_FEATURE_USER_MANAGEMENT_PASSWORD", default="XsdMbe8zKP8KdeE@")
)
KH_ENABLE_ALEMBIC = False
KH_DATABASE = f"sqlite:///{user_cache_dir / 'sql.db'}"
KH_FILESTORAGE_PATH = str(user_cache_dir / "files")

KH_DOCSTORE = {
    "__type__": "kotaemon.storages.SimpleFileDocumentStore",
    "path": str(user_cache_dir / "docstore"),
}
KH_VECTORSTORE = {
    "__type__": "kotaemon.storages.ChromaVectorStore",
    "path": str(user_cache_dir / "vectorstore"),
}
KH_LLMS = {
    # example for using Azure OpenAI, the config variables can set as environment
    # variables or in the .env file
    # "gpt4": {
    #     "def": {
    #         "__type__": "knowledgehub.llms.AzureChatOpenAI",
    #         "temperature": 0,
    #         "azure_endpoint": config("AZURE_OPENAI_ENDPOINT", default=""),
    #         "openai_api_key": config("AZURE_OPENAI_API_KEY", default=""),
    #         "openai_api_version": config("OPENAI_API_VERSION", default=""),
    #         "deployment_name": "<your deployment name>",
    #         "stream": True,
    #     },
    #     "accuracy": 10,
    #     "cost": 10,
    #     "default": False,
    # },
    # "gpt35": {
    #     "def": {
    #         "__type__": "knowledgehub.llms.AzureChatOpenAI",
    #         "temperature": 0,
    #         "azure_endpoint": config("AZURE_OPENAI_ENDPOINT", default=""),
    #         "openai_api_key": config("AZURE_OPENAI_API_KEY", default=""),
    #         "openai_api_version": config("OPENAI_API_VERSION", default=""),
    #         "deployment_name": "<your deployment name>",
    #         "request_timeout": 10,
    #         "stream": False,
    #     },
    #     "accuracy": 5,
    #     "cost": 5,
    #     "default": False,
    # },
    "local": {
        "def": {
            "__type__": "kotaemon.llms.AzureChatOpenAI",
            "temperature": 0,
            "azure_endpoint": config("AZURE_OPENAI_ENDPOINT", default=""),
            "openai_api_key": config("AZURE_OPENAI_API_KEY", default=""),
            "openai_api_version": config("OPENAI_API_VERSION", default=""),
            "deployment_name": "dummy-q2",
            "stream": True,
        },
        "default": False,
    },
    "gpt35": {
        "def": {
            "__type__": "kotaemon.llms.AzureChatOpenAI",
            "temperature": 0,
            "azure_endpoint": config("AZURE_OPENAI_ENDPOINT", default=""),
            "openai_api_key": config("AZURE_OPENAI_API_KEY", default=""),
            "openai_api_version": config("OPENAI_API_VERSION", default=""),
            "deployment_name": "dummy-q2",
            "request_timeout": 10,
            "stream": False,
        },
        "accuracy": 5,
        "cost": 5,
        "default": True,
    },
}
KH_EMBEDDINGS = {
    # example for using Azure OpenAI, the config variables can set as environment
    # variables or in the .env file
    # "ada": {
    #     "def": {
    #         "__type__": "knowledgehub.embeddings.AzureOpenAIEmbeddings",
    #         "model": "text-embedding-ada-002",
    #         "azure_endpoint": config("AZURE_OPENAI_ENDPOINT", default=""),
    #         "openai_api_key": config("AZURE_OPENAI_API_KEY", default=""),
    #         "deployment": "<your deployment name>",
    #         "chunk_size": 16,
    #     },
    #     "accuracy": 5,
    #     "cost": 5,
    #     "default": True,
    # },
    "local": {
        "def": {
            "__type__": "kotaemon.embeddings.AzureOpenAIEmbeddings",
            "model": "text-embedding-ada-002",
            "azure_endpoint": config("AZURE_OPENAI_ENDPOINT", default=""),
            "openai_api_key": config("AZURE_OPENAI_API_KEY", default=""),
            "deployment": "dummy-q2-text-embedding",
            "chunk_size": 16,
        },
        "default": False,
    },
}
KH_REASONINGS = ["ktem.reasoning.simple.FullQAPipeline"]


SETTINGS_APP = {
    "lang": {
        "name": "Language",
        "value": "en",
        "choices": [("English", "en"), ("Japanese", "ja")],
        "component": "dropdown",
    }
}


SETTINGS_REASONING = {
    "use": {
        "name": "Reasoning options",
        "value": None,
        "choices": [],
        "component": "radio",
    },
    "lang": {
        "name": "Language",
        "value": "en",
        "choices": [("English", "en"), ("Japanese", "ja")],
        "component": "dropdown",
    },
}


KH_INDEX_TYPES = ["ktem.index.file.FileIndex"]
KH_INDICES = [
    {
        "id": 1,
        "name": "File",
        "config": {},
        "index_type": "ktem.index.file.FileIndex",
    }
]
