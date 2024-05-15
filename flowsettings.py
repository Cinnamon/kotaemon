import os
from inspect import currentframe, getframeinfo
from pathlib import Path

from decouple import config
from theflow.settings.default import *  # noqa

cur_frame = currentframe()
if cur_frame is None:
    raise ValueError("Cannot get the current frame.")
this_file = getframeinfo(cur_frame).filename
this_dir = Path(this_file).parent

# change this if your app use a different name
KH_PACKAGE_NAME = "kotaemon_app"

# App can be ran from anywhere and it's not trivial to decide where to store app data.
# So let's use the same directory as the flowsetting.py file.
KH_APP_DATA_DIR = this_dir / "ktem_app_data"
KH_APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# User data directory
KH_USER_DATA_DIR = KH_APP_DATA_DIR / "user_data"
KH_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# doc directory
KH_DOC_DIR = this_dir / "docs"

# HF models can be big, let's store them in the app data directory so that it's easier
# for users to manage their storage.
# ref: https://huggingface.co/docs/huggingface_hub/en/guides/manage-cache
os.environ["HF_HOME"] = str(KH_APP_DATA_DIR / "huggingface")
os.environ["HF_HUB_CACHE"] = str(KH_APP_DATA_DIR / "huggingface")

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
KH_DATABASE = f"sqlite:///{KH_USER_DATA_DIR / 'sql.db'}"
KH_FILESTORAGE_PATH = str(KH_USER_DATA_DIR / "files")

KH_DOCSTORE = {
    "__type__": "kotaemon.storages.SimpleFileDocumentStore",
    "path": str(KH_USER_DATA_DIR / "docstore"),
}
KH_VECTORSTORE = {
    "__type__": "kotaemon.storages.ChromaVectorStore",
    "path": str(KH_USER_DATA_DIR / "vectorstore"),
}
KH_LLMS = {}
KH_EMBEDDINGS = {}

# populate options from config
if config("AZURE_OPENAI_API_KEY", default="") and config(
    "AZURE_OPENAI_ENDPOINT", default=""
):
    if config("AZURE_OPENAI_CHAT_DEPLOYMENT", default=""):
        KH_LLMS["azure"] = {
            "spec": {
                "__type__": "kotaemon.llms.AzureChatOpenAI",
                "temperature": 0,
                "azure_endpoint": config("AZURE_OPENAI_ENDPOINT", default=""),
                "api_key": config("AZURE_OPENAI_API_KEY", default=""),
                "api_version": config("OPENAI_API_VERSION", default="")
                or "2024-02-15-preview",
                "azure_deployment": config("AZURE_OPENAI_CHAT_DEPLOYMENT", default=""),
                "timeout": 20,
            },
            "default": False,
            "accuracy": 5,
            "cost": 5,
        }
    if config("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT", default=""):
        KH_EMBEDDINGS["azure"] = {
            "spec": {
                "__type__": "kotaemon.embeddings.AzureOpenAIEmbeddings",
                "azure_endpoint": config("AZURE_OPENAI_ENDPOINT", default=""),
                "api_key": config("AZURE_OPENAI_API_KEY", default=""),
                "api_version": config("OPENAI_API_VERSION", default="")
                or "2024-02-15-preview",
                "azure_deployment": config(
                    "AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT", default=""
                ),
                "timeout": 10,
            },
            "default": False,
        }

if config("OPENAI_API_KEY", default=""):
    KH_LLMS["openai"] = {
        "spec": {
            "__type__": "kotaemon.llms.ChatOpenAI",
            "temperature": 0,
            "base_url": config("OPENAI_API_BASE", default="")
            or "https://api.openai.com/v1",
            "api_key": config("OPENAI_API_KEY", default=""),
            "model": config("OPENAI_CHAT_MODEL", default="") or "gpt-3.5-turbo",
            "timeout": 10,
        },
        "default": False,
    }
    if len(KH_EMBEDDINGS) < 1:
        KH_EMBEDDINGS["openai"] = {
            "spec": {
                "__type__": "kotaemon.embeddings.OpenAIEmbeddings",
                "base_url": config("OPENAI_API_BASE", default="")
                or "https://api.openai.com/v1",
                "api_key": config("OPENAI_API_KEY", default=""),
                "model": config(
                    "OPENAI_EMBEDDINGS_MODEL", default="text-embedding-ada-002"
                )
                or "text-embedding-ada-002",
                "timeout": 10,
            },
            "default": False,
        }

if config("LOCAL_MODEL", default=""):
    KH_LLMS["local"] = {
        "spec": {
            "__type__": "kotaemon.llms.EndpointChatLLM",
            "endpoint_url": "http://localhost:31415/v1/chat/completions",
        },
        "default": False,
        "cost": 0,
    }
    if len(KH_EMBEDDINGS) < 1:
        KH_EMBEDDINGS["local"] = {
            "spec": {
                "__type__": "kotaemon.embeddings.EndpointEmbeddings",
                "endpoint_url": "http://localhost:31415/v1/embeddings",
            },
            "default": False,
            "cost": 0,
        }

if len(KH_EMBEDDINGS) < 1:
    KH_EMBEDDINGS["local-bge-base-en-v1.5"] = {
        "spec": {
            "__type__": "kotaemon.embeddings.FastEmbedEmbeddings",
            "model_name": "BAAI/bge-base-en-v1.5",
        },
        "default": True,
    }

KH_REASONINGS = ["ktem.reasoning.simple.FullQAPipeline"]
KH_VLM_ENDPOINT = "{0}/openai/deployments/{1}/chat/completions?api-version={2}".format(
    config("AZURE_OPENAI_ENDPOINT", default=""),
    config("OPENAI_VISION_DEPLOYMENT_NAME", default="gpt-4-vision"),
    config("OPENAI_API_VERSION", default=""),
)


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
        "name": "File",
        "config": {},
        "index_type": "ktem.index.file.FileIndex",
    },
]
