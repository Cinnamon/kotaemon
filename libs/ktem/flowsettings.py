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
KH_DATABASE = f"sqlite:///{user_cache_dir / 'sql.db'}"
KH_DOCSTORE = {
    "__type__": "kotaemon.storages.SimpleFileDocumentStore",
    "path": str(user_cache_dir / "docstore"),
}
KH_VECTORSTORE = {
    "__type__": "kotaemon.storages.ChromaVectorStore",
    "path": str(user_cache_dir / "vectorstore"),
}
KH_FILESTORAGE_PATH = str(user_cache_dir / "files")
KH_LLMS = {
    "gpt4": {
        "def": {
            "__type__": "kotaemon.llms.AzureChatOpenAI",
            "temperature": 0,
            "azure_endpoint": config("OPENAI_API_BASE", default=""),
            "openai_api_key": config("OPENAI_API_KEY", default=""),
            "openai_api_version": config("OPENAI_API_VERSION", default=""),
            "deployment_name": "dummy-q2",
            "stream": True,
        },
        "accuracy": 10,
        "cost": 10,
        "default": False,
    },
    "gpt35": {
        "def": {
            "__type__": "kotaemon.llms.AzureChatOpenAI",
            "temperature": 0,
            "azure_endpoint": config("OPENAI_API_BASE", default=""),
            "openai_api_key": config("OPENAI_API_KEY", default=""),
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
    "ada": {
        "def": {
            "__type__": "kotaemon.embeddings.AzureOpenAIEmbeddings",
            "model": "text-embedding-ada-002",
            "azure_endpoint": config("OPENAI_API_BASE", default=""),
            "openai_api_key": config("OPENAI_API_KEY", default=""),
            "deployment": "dummy-q2-text-embedding",
            "chunk_size": 16,
        },
        "accuracy": 5,
        "cost": 5,
        "default": True,
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


KH_INDEX = "ktem.indexing.file.IndexDocumentPipeline"
