# 📦 Kotaemon Project Context

## 🎯 Project Overview

**Kotaemon** is an open-source RAG (Retrieval-Augmented Generation) UI for chatting with documents. Built with Python and Gradio, it provides a clean, customizable interface for RAG-based question answering.

### Architecture

```
kotaemon/
├── libs/
│   ├── kotaemon/    # Core RAG library (LLMs, embeddings, retrievers, pipelines)
│   └── ktem/        # Web UI layer (Gradio-based frontend, user management, indexing)
├── scripts/         # Setup and utility scripts
├── ktem_app_data/   # Runtime data (SQLite DB, vector store, caches)
└── app.py           # Application entry point
```

### Key Technologies

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.10+ |
| **Package Manager** | `uv` (recommended) or `pip`/`conda` |
| **UI Framework** | Gradio |
| **Vector Stores** | ChromaDB, LanceDB, Milvus, Qdrant |
| **Document Stores** | Elasticsearch, LanceDB, SimpleFileDocumentStore |
| **LLM Providers** | OpenAI, Azure OpenAI, Ollama, Groq, Claude, Gemini, Cohere |
| **Container** | Docker (multi-platform: linux/amd64, linux/arm64) |

### Core Features

- **Hybrid RAG Pipeline**: Full-text + vector search with re-ranking
- **Multi-modal Support**: PDF, images, tables with OCR capabilities
- **Advanced Retrieval**: Question decomposition, ReAct/ReWoo agents
- **GraphRAG Integration**: NanoGraphRAG, LightRAG, MS GraphRAG
- **User Management**: Multi-user support with public/private collections
- **In-browser PDF Viewer**: Citations with highlights and relevance scores

---

## 🚀 Building and Running

### Quick Start (uv - Recommended)

```bash
# Clone and setup
git clone https://github.com/Cinnamon/kotaemon
cd kotaemon
bash scripts/run_uv.sh
```

This script:
- Installs `uv` if not present
- Creates Python 3.10 virtual environment
- Installs all dependencies
- Downloads PDF.js viewer
- Launches the application

### Manual Setup (conda/pip)

```bash
# Create environment
conda create -n kotaemon python=3.10
conda activate kotaemon

# Install packages
pip install -e "libs/kotaemon[all]"
pip install -e "libs/ktem"

# Optional: Download PDF.js for in-browser viewer
bash scripts/download_pdfjs.sh libs/ktem/ktem/assets/prebuilt/pdfjs-dist

# Start the app
python app.py
```

### Docker (Production)

```bash
# Lite version (smaller, basic file types)
docker run \
  -e GRADIO_SERVER_NAME=0.0.0.0 \
  -e GRADIO_SERVER_PORT=7860 \
  -v ./ktem_app_data:/app/ktem_app_data \
  -p 7860:7860 -it --rm \
  ghcr.io/cinnamon/kotaemon:main-lite

# Full version (supports .doc, .docx, etc.)
docker run <...> ghcr.io/cinnamon/kotaemon:main-full

# With Ollama for local RAG
docker run <...> ghcr.io/cinnamon/kotaemon:main-ollama
```

### Configuration

**Environment Variables** (via `.env` file):

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDINGS_MODEL=text-embedding-3-large

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-35-turbo
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=text-embedding-ada-002

# Local models (Ollama)
LOCAL_MODEL=qwen2.5:7b
LOCAL_MODEL_EMBEDDINGS=nomic-embed-text
KH_OLLAMA_URL=http://localhost:11434/v1/

# Optional features
KH_GRADIO_SHARE=false
KH_FEATURE_USER_MANAGEMENT=true
KH_FEATURE_USER_MANAGEMENT_ADMIN=admin
KH_FEATURE_USER_MANAGEMENT_PASSWORD=admin
```

**Main Configuration** (`flowsettings.py`):

- `KH_VECTORSTORE`: Vector store backend (ChromaDB, LanceDB, Milvus, Qdrant)
- `KH_DOCSTORE`: Document store backend (Elasticsearch, LanceDB, SimpleFileDocumentStore)
- `KH_LLMS`, `KH_EMBEDDINGS`, `KH_RERANKINGS`: Model configurations
- `KH_REASONINGS`: Reasoning pipelines (simple QA, decompose, ReAct, ReWoo)
- `KH_INDICES`: Indexing pipeline types (File, GraphRAG variants)

---

## 🧪 Development

### Install Development Dependencies

```bash
pip install -e "libs/kotaemon[dev]"
```

### Code Quality Tools

```bash
# Pre-commit hooks (runs all checks)
pre-commit run --all-files

# Individual tools
black .                          # Code formatting
isort .                          # Import sorting
flake8 .                         # Linting
mypy .                           # Type checking
codespell .                      # Spell checking
```

### Running Tests

```bash
pytest libs/kotaemon/tests/
```

### Commit Message Convention

Angular convention with gitmoji:

```
<gitmoji> <type>(<scope>): <subject>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `build`, `chore`, `ci`, `perf`, `refactor`, `revert`, `style`, `test`

**Example**:
```
✨ feat(retrieval): add hybrid search with re-ranking

- Implement BM25 + vector search combination
- Add Cohere reranker integration

Closes #123
```

### Pre-commit Configuration

Enabled hooks (`.pre-commit-config.yaml`):
- YAML/TOML validation
- End-of-file fixer
- Trailing whitespace remover
- AWS credential detector
- Private key detector
- Large file checker (>750KB)
- Black (formatting)
- isort (imports)
- flake8 (linting)
- autoflake (unused imports)
- Prettier (markdown/yaml)
- mypy (type checking)
- codespell (spelling)

---

## 📁 Key Files Reference

| File | Purpose |
|------|---------|
| `app.py` | Application entry point, launches Gradio app |
| `flowsettings.py` | Main configuration file (LLMs, stores, features) |
| `pyproject.toml` | Build system, dependencies, workspace config |
| `uv.lock` | Locked dependency versions (uv) |
| `Dockerfile` | Multi-stage Docker build (lite/full variants) |
| `.env.example` | Environment variable template |
| `settings.yaml.example` | Advanced settings template |
| `scripts/run_*.sh` | Platform-specific launch scripts |
| `libs/kotaemon/` | Core RAG library source |
| `libs/ktem/` | Web UI library source |

---

## 🔧 Common Tasks

### Add New LLM Provider

1. Add configuration in `flowsettings.py`:
```python
KH_LLMS["provider_name"] = {
    "spec": {
        "__type__": "kotaemon.llms.ChatProvider",
        "api_key": "your-key",
        ...
    },
    "default": False,
}
```

2. Update `.env.example` with new API key variable

### Add New Reasoning Pipeline

1. Create implementation in `libs/ktem/ktem/reasoning/`
2. Add to `KH_REASONINGS` list in `flowsettings.py`

### Enable GraphRAG

```bash
# NanoGraphRAG (recommended)
pip install nano-graphrag
USE_NANO_GRAPHRAG=true python app.py

# LightRAG
pip install git+https://github.com/HKUDS/LightRAG.git
USE_LIGHTRAG=true python app.py
```

### Setup Multimodal Parsing

- **Azure Document Intelligence**: Set Azure credentials
- **Adobe PDF Extract**: Set Adobe API key
- **Docling**: `pip install docling`

Select in UI: `Settings -> Retrieval Settings -> File loader`

---

## 📝 Notes

- **Data Storage**: All app data stored in `./ktem_app_data/` (SQLite, vector store, caches)
- **Default Credentials**: Username/password both `admin`
- **HF Models**: Cached in `KH_APP_DATA_DIR/huggingface`
- **PDF.js**: Required for in-browser PDF viewer with highlights
- **Unstructured**: Optional dependency for non-PDF file types (.doc, .pptx, etc.)

---

## 🔗 Useful Links

- **Documentation**: https://cinnamon.github.io/kotaemon/
- **GitHub**: https://github.com/Cinnamon/kotaemon
- **Docker Images**: https://github.com/Cinnamon/kotaemon/pkgs/container/kotaemon
- **Hugging Face Demo**: https://huggingface.co/spaces/cin-model/kotaemon
- **Colab Notebook**: https://colab.research.google.com/drive/1eTfieec_UOowNizTJA1NjawBJH9y_1nn

---

*Last updated: 2026-03-26*
