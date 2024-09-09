import os
from importlib.metadata import version
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

KH_APP_VERSION = config("KH_APP_VERSION", None)
if not KH_APP_VERSION:
    try:
        # Caution: This might produce the wrong version
        # https://stackoverflow.com/a/59533071
        KH_APP_VERSION = version(KH_PACKAGE_NAME)
    except Exception:
        KH_APP_VERSION = "local"

# App can be ran from anywhere and it's not trivial to decide where to store app data.
# So let's use the same directory as the flowsetting.py file.
KH_APP_DATA_DIR = this_dir / "ktem_app_data"
KH_APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# User data directory
KH_USER_DATA_DIR = KH_APP_DATA_DIR / "user_data"
KH_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# markdown output directory
KH_MARKDOWN_OUTPUT_DIR = KH_APP_DATA_DIR / "markdown_cache_dir"
KH_MARKDOWN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# chunks output directory
KH_CHUNKS_OUTPUT_DIR = KH_APP_DATA_DIR / "chunks_cache_dir"
KH_CHUNKS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# zip output directory
KH_ZIP_OUTPUT_DIR = KH_APP_DATA_DIR / "zip_cache_dir"
KH_ZIP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# zip input directory
KH_ZIP_INPUT_DIR = KH_APP_DATA_DIR / "zip_cache_dir_in"
KH_ZIP_INPUT_DIR.mkdir(parents=True, exist_ok=True)

# HF models can be big, let's store them in the app data directory so that it's easier
# for users to manage their storage.
# ref: https://huggingface.co/docs/huggingface_hub/en/guides/manage-cache
os.environ["HF_HOME"] = str(KH_APP_DATA_DIR / "huggingface")
os.environ["HF_HUB_CACHE"] = str(KH_APP_DATA_DIR / "huggingface")

# doc directory
KH_DOC_DIR = this_dir / "docs"

KH_MODE = "dev"
KH_FEATURE_USER_MANAGEMENT = True
KH_USER_CAN_SEE_PUBLIC = None
KH_FEATURE_USER_MANAGEMENT_ADMIN = str(
    config("KH_FEATURE_USER_MANAGEMENT_ADMIN", default="admin")
)
KH_FEATURE_USER_MANAGEMENT_PASSWORD = str(
    config("KH_FEATURE_USER_MANAGEMENT_PASSWORD", default="admin")
)
KH_ENABLE_ALEMBIC = False
KH_DATABASE = f"sqlite:///{KH_USER_DATA_DIR / 'sql.db'}"
KH_FILESTORAGE_PATH = str(KH_USER_DATA_DIR / "files")

KH_DOCSTORE = {
    # "__type__": "kotaemon.storages.ElasticsearchDocumentStore",
    # "__type__": "kotaemon.storages.SimpleFileDocumentStore",
    "__type__": "kotaemon.storages.LanceDBDocumentStore",
    "path": str(KH_USER_DATA_DIR / "docstore"),
}
KH_VECTORSTORE = {
    # "__type__": "kotaemon.storages.LanceDBVectorStore",
    "__type__": "kotaemon.storages.ChromaVectorStore",
    # "__type__": "kotaemon.storages.MilvusVectorStore",
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
            "model": config("OPENAI_CHAT_MODEL", default="gpt-3.5-turbo"),
            "timeout": 20,
        },
        "default": True,
    }
    KH_EMBEDDINGS["openai"] = {
        "spec": {
            "__type__": "kotaemon.embeddings.OpenAIEmbeddings",
            "base_url": config("OPENAI_API_BASE", default="https://api.openai.com/v1"),
            "api_key": config("OPENAI_API_KEY", default=""),
            "model": config(
                "OPENAI_EMBEDDINGS_MODEL", default="text-embedding-ada-002"
            ),
            "timeout": 10,
            "context_length": 8191,
        },
        "default": True,
    }

if config("LOCAL_MODEL", default=""):
    KH_LLMS["ollama"] = {
        "spec": {
            "__type__": "kotaemon.llms.ChatOpenAI",
            "base_url": "http://localhost:11434/v1/",
            "model": config("LOCAL_MODEL", default="llama3.1:8b"),
            "api_key": "ollama",
        },
        "default": False,
    }
    KH_EMBEDDINGS["ollama"] = {
        "spec": {
            "__type__": "kotaemon.embeddings.OpenAIEmbeddings",
            "base_url": "http://localhost:11434/v1/",
            "model": config("LOCAL_MODEL_EMBEDDINGS", default="nomic-embed-text"),
            "api_key": "ollama",
        },
        "default": False,
    }

    KH_EMBEDDINGS["fast_embed"] = {
        "spec": {
            "__type__": "kotaemon.embeddings.FastEmbedEmbeddings",
            "model_name": "BAAI/bge-base-en-v1.5",
        },
        "default": False,
    }

# additional LLM configurations
KH_LLMS["claude"] = {
    "spec": {
        "__type__": "kotaemon.llms.chats.LCAnthropicChat",
        "model_name": "claude-3-5-sonnet-20240620",
        "api_key": "your-key",
    },
    "default": False,
}
# KH_LLMS["gemini"] = {
#     "spec": {
#         "__type__": "kotaemon.llms.chats.LCGeminiChat",
#         "model_name": "gemini-1.5-pro",
#         "api_key": "your-key",
#     },
#     "default": False,
# }
KH_LLMS["groq"] = {
    "spec": {
        "__type__": "kotaemon.llms.ChatOpenAI",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-8b-instant",
        "api_key": "your-key",
    },
    "default": False,
}

# additional embeddings configurations
KH_EMBEDDINGS["cohere"] = {
    "spec": {
        "__type__": "kotaemon.embeddings.LCCohereEmbeddings",
        "model": "embed-multilingual-v2.0",
        "cohere_api_key": "your-key",
        "user_agent": "default",
    },
    "default": False,
}
# KH_EMBEDDINGS["huggingface"] = {
#     "spec": {
#         "__type__": "kotaemon.embeddings.LCHuggingFaceEmbeddings",
#         "model_name": "sentence-transformers/all-mpnet-base-v2",
#     },
#     "default": False,
# }

KH_REASONINGS = [
    "ktem.reasoning.simple.FullQAPipeline",
    "ktem.reasoning.simple.FullDecomposeQAPipeline",
    "ktem.reasoning.react.ReactAgentPipeline",
    "ktem.reasoning.rewoo.RewooAgentPipeline",
]
KH_REASONINGS_USE_MULTIMODAL = False
KH_VLM_ENDPOINT = "{0}/openai/deployments/{1}/chat/completions?api-version={2}".format(
    config("AZURE_OPENAI_ENDPOINT", default=""),
    config("OPENAI_VISION_DEPLOYMENT_NAME", default="gpt-4o"),
    config("OPENAI_API_VERSION", default=""),
)


SETTINGS_APP: dict[str, dict] = {}


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
        "choices": [("English", "en"), ("Japanese", "ja"), ("Vietnamese", "vi")],
        "component": "dropdown",
    },
    "max_context_length": {
        "name": "Max context length (LLM)",
        "value": 32000,
        "component": "number",
    },
}


KH_INDEX_TYPES = [
    "ktem.index.file.FileIndex",
    "ktem.index.file.graph.GraphRAGIndex",
]
KH_INDICES = [
    {
        "name": "File",
        "config": {
            "supported_file_types": (
                ".png, .jpeg, .jpg, .tiff, .tif, .pdf, .xls, .xlsx, .doc, .docx, "
                ".pptx, .csv, .html, .mhtml, .txt, .md, .zip"
            ),
            "private": False,
        },
        "index_type": "ktem.index.file.FileIndex",
    },
    {
        "name": "GraphRAG",
        "config": {
            "supported_file_types": (
                ".png, .jpeg, .jpg, .tiff, .tif, .pdf, .xls, .xlsx, .doc, .docx, "
                ".pptx, .csv, .html, .mhtml, .txt, .md, .zip"
            ),
            "private": False,
        },
        "index_type": "ktem.index.file.graph.GraphRAGIndex",
    },
]
