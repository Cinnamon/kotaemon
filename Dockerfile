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

# Build device: cpu or gpu. Use at build time for torch/paddle backend choice.
# Example: docker build --build-arg BUILD_DEVICE=gpu ...
ARG BUILD_DEVICE=cpu
ENV BUILD_DEVICE=${BUILD_DEVICE}

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

# Torch: CPU or GPU based on BUILD_DEVICE
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/uv  \
    if [ "$BUILD_DEVICE" = "gpu" ]; then \
        uv pip install --python .venv torch torchvision torchaudio \
            --index-url https://download.pytorch.org/whl/cu121; \
    else \
        uv pip install --python .venv torch torchvision torchaudio \
            --index-url https://download.pytorch.org/whl/cpu; \
    fi

# Install additional pip packages (adv + unstructured)
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/uv  \
    uv pip install --python .venv "libs/kotaemon[adv]" \
    && uv pip install --python .venv unstructured[all-docs]

# Paddle backend first (CPU or GPU from BUILD_DEVICE), then PaddleOCR (order per upstream docs)
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/uv  \
    if [ "$BUILD_DEVICE" = "gpu" ]; then \
        uv pip install --python .venv paddlepaddle-gpu==3.3.0 \
            -i https://www.paddlepaddle.org.cn/packages/stable/cu130/; \
    else \
        uv pip install --python .venv paddlepaddle; \
    fi

# Optional readers via extras (docling); paddleocr after backend above to avoid pulling default paddle
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/uv  \
    uv pip install --python .venv "libs/kotaemon[docling]" \
    && uv pip install --python .venv paddleocr[all]

# Download NLTK data from LlamaIndex
RUN /app/.venv/bin/python -c "from llama_index.core.readers.base import BaseReader"

# RAG: lightRAG via extra
ENV USE_LIGHTRAG=true
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/uv  \
    uv pip install --python .venv "libs/kotaemon[lightrag]"

ENTRYPOINT ["sh", "/app/launch.sh"]

# Ollama-bundled version
FROM full AS ollama

# Install ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# RUN nohup bash -c "ollama serve &" && sleep 4 && ollama pull qwen2.5:7b
RUN nohup bash -c "ollama serve &" && sleep 4 && ollama pull nomic-embed-text

ENTRYPOINT ["sh", "/app/launch.sh"]
