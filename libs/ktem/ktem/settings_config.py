from __future__ import annotations

import os
from importlib.metadata import version
from pathlib import Path
from typing import Any, ClassVar

from ktem.settings import SettingItem
from ktem.utils.lang import SUPPORTED_LANGUAGE_MAP
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# from kotaemon.storages.docstores.factory import DocStoreVendor
# from kotaemon.storages.vectorstores.factory import VectorStoreVendor

# from ktem.collections.registry import IndexKind
# from ktem.reasoning.registry import ReasoningKind

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
        if (candidate / "pyproject.toml").exists() and (candidate / "app.py").exists():
            return candidate

    return cwd


class _AppBaseSettings(BaseSettings):
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


class AppSettings(
    _AppBaseSettings,
    AzureOpenAISettings,
    OpenAISettings,
    ProviderAPISettings,
):
    __ROOT: ClassVar[Path] = Path.cwd()

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    # Storage back-end vendors — constructor kwargs are computed below.
    KH_DOCSTORE_VENDOR: str = "LanceDBDocumentStore"
    KH_VECTORSTORE_VENDOR: str = "ChromaVectorStore"

    # Static reasoning / index configuration.
    KH_REASONINGS: list[str] = [
        "FullQAPipeline",
    ]
    KH_INDEX_TYPES: list[str] = ["FileIndex"]
    SETTINGS_APP: dict[str, SettingItem] = Field(default_factory=dict)
    SETTINGS_REASONING: dict[str, SettingItem] = Field(
        default_factory=lambda: {
            "use": SettingItem(
                name="Reasoning options",
                value=None,
                choices=[],
                component="radio",
            ),
            "lang": SettingItem(
                name="Language",
                value="en",
                choices=[(lang, code) for code, lang in SUPPORTED_LANGUAGE_MAP.items()],
                component="dropdown",
            ),
            "max_context_length": SettingItem(
                name="Max context length (LLM)",
                value=32000,
                component="number",
            ),
        }
    )

    KH_APP_DATA_DIR: Path = Field(
        default_factory=lambda: AppSettings.__ROOT / "ktem_app_data"
    )
    KH_USER_DATA_DIR: Path = Field(
        default_factory=lambda: AppSettings.__ROOT / "ktem_user_data"
    )
    KH_MARKDOWN_OUTPUT_DIR: Path = Field(
        default_factory=lambda: AppSettings.__ROOT / "ktem_markdown_output"
    )
    KH_CHUNKS_OUTPUT_DIR: Path = Field(
        default_factory=lambda: AppSettings.__ROOT / "ktem_chunks_output"
    )
    KH_ZIP_OUTPUT_DIR: Path = Field(
        default_factory=lambda: AppSettings.__ROOT / "ktem_zip_output"
    )
    KH_ZIP_INPUT_DIR: Path = Field(
        default_factory=lambda: AppSettings.__ROOT / "ktem_zip_input"
    )
    KH_DOC_DIR: Path = Field(default_factory=lambda: AppSettings.__ROOT / "docs")
    KH_DATABASE: str = Field(
        default_factory=lambda: f"sqlite:///{AppSettings.__ROOT / 'sql.db'}"
    )
    KH_FILESTORAGE_PATH: str = Field(
        default_factory=lambda: str(AppSettings.__ROOT / "files")
    )
    KH_VLM_ENDPOINT: str = ""

    # ------------------------------------------------------------------
    # Computed model / reasoning fields
    # ------------------------------------------------------------------

    # keep
    @computed_field  # type: ignore[misc]
    @property
    def KH_INDICES(self) -> list[dict[str, Any]]:
        return self._build_indices()

    # ------------------------------------------------------------------
    # Startup side-effects
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Create app directories, set HF env vars, resolve version.

        Call once at application startup::

            app_settings.initialize()

        All derived path and storage fields are computed automatically
        from :attr:`KH_PROJECT_ROOT`; this method only performs the
        side-effects that cannot be expressed as field defaults.
        """
        for path in (
            self.KH_APP_DATA_DIR,
            self.KH_USER_DATA_DIR,
            self.KH_MARKDOWN_OUTPUT_DIR,
            self.KH_CHUNKS_OUTPUT_DIR,
            self.KH_ZIP_OUTPUT_DIR,
            self.KH_ZIP_INPUT_DIR,
        ):
            path.mkdir(parents=True, exist_ok=True)

        hf_home = self.KH_APP_DATA_DIR / "huggingface"
        os.environ["HF_HOME"] = str(hf_home)
        os.environ["HF_HUB_CACHE"] = str(hf_home)

        if not self.KH_APP_VERSION:
            try:
                self.KH_APP_VERSION = version(self.KH_PACKAGE_NAME)
            except Exception:
                self.KH_APP_VERSION = "local"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_indices(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "File Collection",
                "config": {
                    "supported_file_types": SUPPORTED_FILE_TYPES,
                    "private": True,
                },
                "index_type": "FileIndex",
            },
        ]


app_settings = AppSettings()
app_settings.initialize()
