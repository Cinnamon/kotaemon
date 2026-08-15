# Lite version
FROM python:3.11-slim AS lite

# Common dependencies
RUN apt-get update -qqy && \
    apt-get install -y --no-install-recommends \
        ssh \
        git \
        gcc \
        g++ \
        poppler-utils \
        libpoppler-dev \
        unzip \
        curl \
        cargo \
        && \
    apt-get autoremove && apt-get clean && rm -rf /var/lib/apt/lists/*

# Setup args
ARG TARGETPLATFORM
ARG TARGETARCH

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8
ENV TARGETARCH=${TARGETARCH}

# Create working directory
WORKDIR /app

# Download pdfjs
COPY scripts/download_pdfjs.sh /app/scripts/download_pdfjs.sh
RUN chmod +x /app/scripts/download_pdfjs.sh
ENV PDFJS_PREBUILT_DIR="/app/libs/ktem/ktem/assets/prebuilt/pdfjs-dist"
RUN bash scripts/download_pdfjs.sh $PDFJS_PREBUILT_DIR

# Install uv dependencies
RUN pip install --no-cache-dir "uv"

# Copy contents
COPY . /app
COPY launch.sh /app/launch.sh
COPY .env.example /app/.env

# Install pip packages
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/uv  \
    uv sync --frozen --no-cache \
    && uv pip install --python .venv "pdfservices-sdk@git+https://github.com/niallcm/pdfservices-python-sdk.git@bump-and-unfreeze-requirements"

RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/uv  \
    if [ "$TARGETARCH" = "amd64" ]; then uv pip install --python .venv "graphrag<=0.3.6" future; fi

ENTRYPOINT ["sh", "/app/launch.sh"]

# Full version
FROM lite AS full

# Additional dependencies for full version
RUN apt-get update -qqy && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-jpn \
        libsm6 \
        libxext6 \
        libreoffice \
        ffmpeg \
        libmagic-dev \
        && \
    apt-get autoremove && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install torch and torchvision for unstructured
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/uv  \
    uv pip install --python .venv torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install additional pip packages (adv + unstructured)
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/uv  \
    uv pip install --python .venv "libs/kotaemon[adv]" \
    && uv pip install --python .venv unstructured[all-docs]

# Download NLTK data from LlamaIndex
RUN /app/.venv/bin/python -c "from llama_index.core.readers.base import BaseReader"

# Optional reader: docling
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/uv  \
    uv pip install --python .venv "libs/kotaemon[docling]"

# Optional RAG: lightRAG
ENV USE_LIGHTRAG=true
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/uv  \
    uv pip install --python .venv "libs/kotaemon[lightrag]"

ENTRYPOINT ["sh", "/app/launch.sh"]

# PaddleOCR version (GPU-only)
FROM full AS paddle

ARG CUDA_VERSION=130

# Install paddlepaddle and paddleocr
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/uv  \
    uv pip install --python .venv paddlepaddle-gpu==3.3.0 \
        -i "https://www.paddlepaddle.org.cn/packages/stable/cu${CUDA_VERSION}/" \
    && uv pip install --python .venv "libs/kotaemon[paddleocr]"

ENTRYPOINT ["sh", "/app/launch.sh"]

# Ollama-bundled version
FROM full AS ollama

# Install ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# RUN nohup bash -c "ollama serve &" && sleep 4 && ollama pull qwen2.5:7b
RUN nohup bash -c "ollama serve &" && sleep 4 && ollama pull nomic-embed-text

ENTRYPOINT ["sh", "/app/launch.sh"]
