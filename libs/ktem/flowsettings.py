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
KH_LLMS = {}
KH_EMBEDDINGS = {}

# populate options from config
if config("AZURE_OPENAI_API_KEY", default="") and config(
    "AZURE_OPENAI_ENDPOINT", default=""
):
    if config("AZURE_OPENAI_CHAT_DEPLOYMENT", default=""):
        KH_LLMS["azure"] = {
            "def": {
                "__type__": "kotaemon.llms.LCAzureChatOpenAI",
                "temperature": 0,
                "azure_endpoint": config("AZURE_OPENAI_ENDPOINT", default=""),
                "openai_api_key": config("AZURE_OPENAI_API_KEY", default=""),
                "api_version": config("OPENAI_API_VERSION", default="")
                or "2024-02-15-preview",
                "deployment_name": config("AZURE_OPENAI_CHAT_DEPLOYMENT", default=""),
                "request_timeout": 10,
                "stream": False,
            },
            "default": False,
            "accuracy": 5,
            "cost": 5,
        }
    if config("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT", default=""):
        KH_EMBEDDINGS["azure"] = {
            "def": {
                "__type__": "kotaemon.embeddings.AzureOpenAIEmbeddings",
                "azure_endpoint": config("AZURE_OPENAI_ENDPOINT", default=""),
                "openai_api_key": config("AZURE_OPENAI_API_KEY", default=""),
                "api_version": config("OPENAI_API_VERSION", default="")
                or "2024-02-15-preview",
                "deployment": config("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT", default=""),
                "request_timeout": 10,
                "chunk_size": 16,
            },
            "default": False,
            "accuracy": 5,
            "cost": 5,
        }

if config("OPENAI_API_KEY", default=""):
    KH_LLMS["openai"] = {
        "def": {
            "__type__": "kotaemon.llms.ChatOpenAI",
            "temperature": 0,
            "openai_api_base": config("OPENAI_API_BASE", default="")
            or "https://api.openai.com/v1",
            "openai_api_key": config("OPENAI_API_KEY", default=""),
            "model": config("OPENAI_CHAT_MODEL", default="") or "gpt-3.5-turbo",
            "request_timeout": 10,
            "stream": False,
        },
        "default": False,
    }
    if len(KH_EMBEDDINGS) < 1:
        KH_EMBEDDINGS["openai"] = {
            "def": {
                "__type__": "kotaemon.embeddings.OpenAIEmbeddings",
                "openai_api_base": config("OPENAI_API_BASE", default="")
                or "https://api.openai.com/v1",
                "openai_api_key": config("OPENAI_API_KEY", default=""),
                "model": config(
                    "OPENAI_EMBEDDINGS_MODEL", default="text-embedding-ada-002"
                )
                or "text-embedding-ada-002",
                "request_timeout": 10,
                "chunk_size": 16,
            },
            "default": False,
        }

if config("LOCAL_MODEL", default=""):
    KH_LLMS["local"] = {
        "def": {
            "__type__": "kotaemon.llms.EndpointChatLLM",
            "endpoint_url": "http://localhost:31415/v1/chat/completions",
        },
        "default": False,
        "cost": 0,
    }
    if len(KH_EMBEDDINGS) < 1:
        KH_EMBEDDINGS["local"] = {
            "def": {
                "__type__": "kotaemon.embeddings.EndpointEmbeddings",
                "endpoint_url": "http://localhost:31415/v1/embeddings",
            },
            "default": False,
            "cost": 0,
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
