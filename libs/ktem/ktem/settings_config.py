"""Kotaemon application settings.

Replaces ``flowsettings.py``. All configuration is declared here as a
typed :class:`pydantic_settings.BaseSettings` subclass so that every
field can be overridden via environment variables or a ``.env`` file
without any code changes.

Usage::

    from ktem.settings_config import app_settings

    db_url = app_settings.KH_DATABASE
"""

from __future__ import annotations

import getpass
import os
import tempfile
from importlib.metadata import version
from pathlib import Path
from typing import Any, ClassVar

from typing_extensions import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from kotaemon.storages.docstores.factory import DocStoreVendor
from kotaemon.storages.vectorstores.factory import VectorStoreVendor

OPENAI_DEFAULT = "<YOUR_OPENAI_KEY>"
THEFLOW_DIR = ".theflow"
SUPPORTED_FILE_TYPES = (
    ".png, .jpeg, .jpg, .tiff, .tif, .pdf, .xls, .xlsx, .doc, .docx, "
    ".pptx, .csv, .html, .mhtml, .txt, .md, .zip"
)


def resolve_project_root() -> Path:
    """Resolve Kotaemon project root directory.

    Priority:
    1. ``KH_PROJECT_ROOT`` environment variable.
    2. Nearest ancestor that has both ``pyproject.toml`` and ``app.py``.
    3. Current working directory.
    """
    env_root = os.getenv("KH_PROJECT_ROOT")
    if env_root:
        return Path(env_root)

    cwd = Path.cwd()
    for candidate in (cwd, *cwd.parents):
        if (candidate / "pyproject.toml").exists() and (
            candidate / "app.py"
        ).exists():
            return candidate

    return cwd


def _temp_path() -> str:
    default = os.environ.get("THEFLOW_TEMP_PATH", "")
    if not default:
        try:
            username = getpass.getuser()
        except Exception:
            username = ""
        path = Path(tempfile.gettempdir(), f"theflow_{username}")
    else:
        path = Path(default)
    path.mkdir(exist_ok=True, parents=True)
    return str(path)


def _default_theflow_path(project_root: Path) -> Path:
    loc = project_root
    while loc != loc.parent:
        if (loc / THEFLOW_DIR).exists():
            return loc / THEFLOW_DIR
        loc = loc.parent

    flow_path = project_root / THEFLOW_DIR
    flow_path.mkdir(exist_ok=True, parents=True)
    return flow_path


class AppSettings(BaseSettings):
    """Feature flags and top-level application knobs."""

    KH_PACKAGE_NAME: str = "kotaemon_app"
    KH_APP_VERSION: str | None = None
    KH_APP_NAME: str = "Kotaemon"
    KH_GRADIO_SHARE: bool = False
    KH_ENABLE_FIRST_SETUP: bool = True
    KH_DEMO_MODE: bool = False
    KH_OLLAMA_URL: str = "http://localhost:11434/v1/"
    KH_PROJECT_ROOT: Path | None = None
    KH_MODE: str = "dev"
    KH_SSO_ENABLED: bool = False
    KH_FEATURE_CHAT_SUGGESTION: bool = False
    KH_FEATURE_USER_MANAGEMENT: bool = True
    KH_USER_CAN_SEE_PUBLIC: str | None = None
    KH_FEATURE_USER_MANAGEMENT_ADMIN: str = "admin"
    KH_FEATURE_USER_MANAGEMENT_PASSWORD: str = "admin"
    KH_ENABLE_ALEMBIC: bool = False
    KH_WEB_SEARCH_BACKEND: str = (
        "kotaemon.indices.retrievers.tavily_web_search.WebSearch"
    )
    N_PROMPT_OPT_EXAMPLES: int = 3


class AzureOpenAISettings(BaseSettings):
    """Azure OpenAI provider credentials."""

    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_CHAT_DEPLOYMENT: str = ""
    AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT: str = ""
    OPENAI_API_VERSION: str = ""
    OPENAI_VISION_DEPLOYMENT_NAME: str = "gpt-4o"


class OpenAISettings(BaseSettings):
    """OpenAI provider credentials."""

    OPENAI_API_KEY: str = OPENAI_DEFAULT
    OPENAI_API_BASE: str = ""
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDINGS_MODEL: str = "text-embedding-3-large"


class ProviderAPISettings(BaseSettings):
    """Third-party API keys and model name overrides."""

    GOOGLE_API_KEY: str = "your-key"
    VOYAGE_API_KEY: str = ""
    VOYAGE_EMBEDDINGS_MODEL: str = "voyage-3-large"
    COHERE_API_KEY: str = "your-key"
    MISTRAL_API_KEY: str = "your-key"
    LOCAL_MODEL: str = ""
    LOCAL_MODEL_EMBEDDINGS: str = "nomic-embed-text"
    USE_MULTIMODAL: bool = False


class KotaemonSettings(
    AppSettings,
    AzureOpenAISettings,
    OpenAISettings,
    ProviderAPISettings,
):
    """Composed Kotaemon settings loaded from environment variables.

    All ``KH_*`` variables can be overridden via environment or
    a ``.env`` file next to ``app.py``.
    """

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    OPENAI_DEFAULT: ClassVar[str] = OPENAI_DEFAULT

    # Derived path fields — populated by :meth:`finalize`.
    KH_APP_DATA_DIR: Path = Field(default_factory=Path)
    KH_APP_DATA_EXISTS: bool = False
    KH_USER_DATA_DIR: Path = Field(default_factory=Path)
    KH_MARKDOWN_OUTPUT_DIR: Path = Field(default_factory=Path)
    KH_CHUNKS_OUTPUT_DIR: Path = Field(default_factory=Path)
    KH_ZIP_OUTPUT_DIR: Path = Field(default_factory=Path)
    KH_ZIP_INPUT_DIR: Path = Field(default_factory=Path)
    KH_DOC_DIR: Path = Field(default_factory=Path)
    KH_DATABASE: str = ""
    KH_FILESTORAGE_PATH: str = ""

    # Storage back-ends — vendor selects the class; spec holds
    # constructor kwargs (path, etc.).  collection_name is injected
    # at call time by get_docstore() / get_vectorstore().
    KH_DOCSTORE_VENDOR: DocStoreVendor = DocStoreVendor.LANCEDB
    KH_DOCSTORE_SPEC: dict[str, Any] = Field(default_factory=dict)
    KH_VECTORSTORE_VENDOR: VectorStoreVendor = VectorStoreVendor.CHROMA
    KH_VECTORSTORE_SPEC: dict[str, Any] = Field(default_factory=dict)

    # Model pools — populated by :meth:`_build_*` helpers.
    KH_LLMS: dict[str, dict[str, Any]] = Field(default_factory=dict)
    KH_EMBEDDINGS: dict[str, dict[str, Any]] = Field(default_factory=dict)
    KH_RERANKINGS: dict[str, dict[str, Any]] = Field(default_factory=dict)

    # Reasoning and UI settings.
    KH_REASONINGS: list[str] = Field(default_factory=list)
    KH_REASONINGS_USE_MULTIMODAL: bool = False
    KH_VLM_ENDPOINT: str = ""
    SETTINGS_APP: dict[str, dict[str, Any]] = Field(default_factory=dict)
    SETTINGS_REASONING: dict[str, dict[str, Any]] = Field(
        default_factory=dict
    )

    # Index types and default indices.
    KH_INDEX_TYPES: list[str] = Field(default_factory=list)
    KH_INDICES: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def is_openai_default(self) -> bool:
        """True when OPENAI_API_KEY looks like a real key."""
        return (
            len(self.OPENAI_API_KEY) > 0
            and self.OPENAI_API_KEY != OPENAI_DEFAULT
        )

    @model_validator(mode="after")
    def finalize(self) -> Self:
        """Derive all path and model-pool fields from primitive inputs."""
        project_root = self.KH_PROJECT_ROOT or resolve_project_root()
        object.__setattr__(self, "KH_PROJECT_ROOT", project_root)

        app_data_dir = project_root / "ktem_app_data"
        app_data_exists = app_data_dir.exists()
        user_data_dir = app_data_dir / "user_data"
        markdown_dir = app_data_dir / "markdown_cache_dir"
        chunks_dir = app_data_dir / "chunks_cache_dir"
        zip_out_dir = app_data_dir / "zip_cache_dir"
        zip_in_dir = app_data_dir / "zip_cache_dir_in"
        doc_dir = project_root / "docs"

        for path in (
            app_data_dir,
            user_data_dir,
            markdown_dir,
            chunks_dir,
            zip_out_dir,
            zip_in_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

        hf_home = app_data_dir / "huggingface"
        os.environ["HF_HOME"] = str(hf_home)
        os.environ["HF_HUB_CACHE"] = str(hf_home)

        app_version = self.KH_APP_VERSION
        if not app_version:
            try:
                app_version = version(self.KH_PACKAGE_NAME)
            except Exception:
                app_version = "local"
        object.__setattr__(self, "KH_APP_VERSION", app_version)

        object.__setattr__(self, "KH_APP_DATA_DIR", app_data_dir)
        object.__setattr__(self, "KH_APP_DATA_EXISTS", app_data_exists)
        object.__setattr__(self, "KH_USER_DATA_DIR", user_data_dir)
        object.__setattr__(self, "KH_MARKDOWN_OUTPUT_DIR", markdown_dir)
        object.__setattr__(self, "KH_CHUNKS_OUTPUT_DIR", chunks_dir)
        object.__setattr__(self, "KH_ZIP_OUTPUT_DIR", zip_out_dir)
        object.__setattr__(self, "KH_ZIP_INPUT_DIR", zip_in_dir)
        object.__setattr__(self, "KH_DOC_DIR", doc_dir)
        object.__setattr__(
            self,
            "KH_DATABASE",
            f"sqlite:///{user_data_dir / 'sql.db'}",
        )
        object.__setattr__(
            self,
            "KH_FILESTORAGE_PATH",
            str(user_data_dir / "files"),
        )
        object.__setattr__(
            self,
            "KH_DOCSTORE_SPEC",
            {"path": str(user_data_dir / "docstore")},
        )
        object.__setattr__(
            self,
            "KH_VECTORSTORE_SPEC",
            {"path": str(user_data_dir / "vectorstore")},
        )
        object.__setattr__(
            self,
            "KH_REASONINGS_USE_MULTIMODAL",
            self.USE_MULTIMODAL,
        )
        object.__setattr__(self, "KH_LLMS", self._build_llms())
        object.__setattr__(self, "KH_EMBEDDINGS", self._build_embeddings())
        object.__setattr__(
            self, "KH_RERANKINGS", self._build_rerankings()
        )
        object.__setattr__(
            self,
            "KH_VLM_ENDPOINT",
            "{0}/openai/deployments/{1}/chat/completions?api-version={2}".format(
                self.AZURE_OPENAI_ENDPOINT,
                self.OPENAI_VISION_DEPLOYMENT_NAME,
                self.OPENAI_API_VERSION,
            ),
        )
        object.__setattr__(
            self,
            "KH_REASONINGS",
            [
                "ktem.reasoning.simple.FullQAPipeline",
                "ktem.reasoning.simple.FullDecomposeQAPipeline",
                "ktem.reasoning.react.ReactAgentPipeline",
                "ktem.reasoning.rewoo.RewooAgentPipeline",
            ],
        )
        object.__setattr__(
            self,
            "SETTINGS_REASONING",
            self._build_settings_reasoning(),
        )
        object.__setattr__(self, "SETTINGS_APP", {})
        object.__setattr__(
            self,
            "KH_INDEX_TYPES",
            ["ktem.collections.file.FileIndex"],
        )
        object.__setattr__(
            self,
            "KH_INDICES",
            self._build_indices(),
        )

        return self

    # ------------------------------------------------------------------
    # Private builder helpers
    # ------------------------------------------------------------------

    def _build_llms(self) -> dict[str, dict[str, Any]]:
        llms: dict[str, dict[str, Any]] = {}

        if self.AZURE_OPENAI_API_KEY and self.AZURE_OPENAI_ENDPOINT:
            if self.AZURE_OPENAI_CHAT_DEPLOYMENT:
                llms["azure"] = {
                    "spec": {
                        "__type__": "kotaemon.llms.AzureChatOpenAI",
                        "temperature": 0,
                        "azure_endpoint": self.AZURE_OPENAI_ENDPOINT,
                        "api_key": self.AZURE_OPENAI_API_KEY,
                        "api_version": (
                            self.OPENAI_API_VERSION
                            or "2024-02-15-preview"
                        ),
                        "azure_deployment": (
                            self.AZURE_OPENAI_CHAT_DEPLOYMENT
                        ),
                        "timeout": 20,
                    },
                    "default": False,
                }

        if self.OPENAI_API_KEY:
            llms["openai"] = {
                "spec": {
                    "__type__": "kotaemon.llms.ChatOpenAI",
                    "temperature": 0,
                    "base_url": (
                        self.OPENAI_API_BASE
                        or "https://api.openai.com/v1"
                    ),
                    "api_key": self.OPENAI_API_KEY,
                    "model": self.OPENAI_CHAT_MODEL,
                    "timeout": 20,
                },
                "default": self.is_openai_default,
            }

        if self.LOCAL_MODEL:
            llms["ollama"] = {
                "spec": {
                    "__type__": "kotaemon.llms.ChatOpenAI",
                    "base_url": self.KH_OLLAMA_URL,
                    "model": self.LOCAL_MODEL,
                    "api_key": "ollama",
                },
                "default": False,
            }
            llms["ollama-long-context"] = {
                "spec": {
                    "__type__": "kotaemon.llms.LCOllamaChat",
                    "base_url": self.KH_OLLAMA_URL.replace("v1/", ""),
                    "model": self.LOCAL_MODEL,
                    "num_ctx": 8192,
                },
                "default": False,
            }

        llms["claude"] = {
            "spec": {
                "__type__": "kotaemon.llms.chats.LCAnthropicChat",
                "model_name": "claude-3-5-sonnet-20240620",
                "api_key": "your-key",
            },
            "default": False,
        }
        llms["google"] = {
            "spec": {
                "__type__": "kotaemon.llms.chats.LCGeminiChat",
                "model_name": "gemini-1.5-flash",
                "api_key": self.GOOGLE_API_KEY,
            },
            "default": not self.is_openai_default,
        }
        llms["groq"] = {
            "spec": {
                "__type__": "kotaemon.llms.ChatOpenAI",
                "base_url": "https://api.groq.com/openai/v1",
                "model": "llama-3.1-8b-instant",
                "api_key": "your-key",
            },
            "default": False,
        }
        llms["cohere"] = {
            "spec": {
                "__type__": "kotaemon.llms.chats.LCCohereChat",
                "model_name": "command-r-plus-08-2024",
                "api_key": self.COHERE_API_KEY,
            },
            "default": False,
        }
        llms["mistral"] = {
            "spec": {
                "__type__": "kotaemon.llms.ChatOpenAI",
                "base_url": "https://api.mistral.ai/v1",
                "model": "ministral-8b-latest",
                "api_key": self.MISTRAL_API_KEY,
            },
            "default": False,
        }

        return llms

    def _build_embeddings(self) -> dict[str, dict[str, Any]]:
        embeddings: dict[str, dict[str, Any]] = {}

        if self.AZURE_OPENAI_API_KEY and self.AZURE_OPENAI_ENDPOINT:
            if self.AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT:
                embeddings["azure"] = {
                    "spec": {
                        "__type__": (
                            "kotaemon.embeddings.AzureOpenAIEmbeddings"
                        ),
                        "azure_endpoint": self.AZURE_OPENAI_ENDPOINT,
                        "api_key": self.AZURE_OPENAI_API_KEY,
                        "api_version": (
                            self.OPENAI_API_VERSION
                            or "2024-02-15-preview"
                        ),
                        "azure_deployment": (
                            self.AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT
                        ),
                        "timeout": 10,
                    },
                    "default": False,
                }

        if self.OPENAI_API_KEY:
            embeddings["openai"] = {
                "spec": {
                    "__type__": "kotaemon.embeddings.OpenAIEmbeddings",
                    "base_url": (
                        self.OPENAI_API_BASE
                        or "https://api.openai.com/v1"
                    ),
                    "api_key": self.OPENAI_API_KEY,
                    "model": self.OPENAI_EMBEDDINGS_MODEL,
                    "timeout": 10,
                    "context_length": 8191,
                },
                "default": self.is_openai_default,
            }

        if self.VOYAGE_API_KEY:
            embeddings["voyageai"] = {
                "spec": {
                    "__type__": (
                        "kotaemon.embeddings.VoyageAIEmbeddings"
                    ),
                    "api_key": self.VOYAGE_API_KEY,
                    "model": self.VOYAGE_EMBEDDINGS_MODEL,
                },
                "default": False,
            }

        if self.LOCAL_MODEL:
            embeddings["ollama"] = {
                "spec": {
                    "__type__": "kotaemon.embeddings.OpenAIEmbeddings",
                    "base_url": self.KH_OLLAMA_URL,
                    "model": self.LOCAL_MODEL_EMBEDDINGS,
                    "api_key": "ollama",
                },
                "default": False,
            }
            embeddings["fast_embed"] = {
                "spec": {
                    "__type__": (
                        "kotaemon.embeddings.FastEmbedEmbeddings"
                    ),
                    "model_name": "BAAI/bge-base-en-v1.5",
                },
                "default": False,
            }

        embeddings["cohere"] = {
            "spec": {
                "__type__": "kotaemon.embeddings.LCCohereEmbeddings",
                "model": "embed-multilingual-v3.0",
                "cohere_api_key": self.COHERE_API_KEY,
                "user_agent": "default",
            },
            "default": False,
        }
        embeddings["google"] = {
            "spec": {
                "__type__": "kotaemon.embeddings.LCGoogleEmbeddings",
                "model": "models/text-embedding-004",
                "google_api_key": self.GOOGLE_API_KEY,
            },
            "default": not self.is_openai_default,
        }
        embeddings["mistral"] = {
            "spec": {
                "__type__": "kotaemon.embeddings.LCMistralEmbeddings",
                "model": "mistral-embed",
                "api_key": self.MISTRAL_API_KEY,
            },
            "default": False,
        }

        return embeddings

    def _build_rerankings(self) -> dict[str, dict[str, Any]]:
        rerankings: dict[str, dict[str, Any]] = {}

        if self.VOYAGE_API_KEY:
            rerankings["voyageai"] = {
                "vendor": "VoyageAIReranking",
                "spec": {
                    "model_name": "rerank-2",
                    "api_key": self.VOYAGE_API_KEY,
                },
                "default": False,
            }

        rerankings["cohere"] = {
            "vendor": "CohereReranking",
            "spec": {
                "model_name": "rerank-v4.0-fast",
                "cohere_api_key": self.COHERE_API_KEY,
            },
            "default": True,
        }

        return rerankings

    def _build_settings_reasoning(self) -> dict[str, dict[str, Any]]:
        from ktem.utils.lang import SUPPORTED_LANGUAGE_MAP

        return {
            "use": {
                "name": "Reasoning options",
                "value": None,
                "choices": [],
                "component": "radio",
            },
            "lang": {
                "name": "Language",
                "value": "en",
                "choices": [
                    (lang, code)
                    for code, lang in SUPPORTED_LANGUAGE_MAP.items()
                ],
                "component": "dropdown",
            },
            "max_context_length": {
                "name": "Max context length (LLM)",
                "value": 32000,
                "component": "number",
            },
        }

    def _build_indices(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "File Collection",
                "config": {
                    "supported_file_types": SUPPORTED_FILE_TYPES,
                    "private": True,
                },
                "index_type": "ktem.collections.file.FileIndex",
            },
        ]


app_settings = KotaemonSettings()
