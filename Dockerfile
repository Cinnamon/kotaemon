FROM python:3.10-slim as base_image

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
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

WORKDIR /app

COPY scripts/download_pdfjs.sh /app/scripts/download_pdfjs.sh
RUN chmod +x /app/scripts/download_pdfjs.sh

ENV PDFJS_PREBUILT_DIR="/app/libs/ktem/ktem/assets/prebuilt/pdfjs-dist"
RUN bash scripts/download_pdfjs.sh $PDFJS_PREBUILT_DIR

# Lite
FROM base_image as lite

COPY . /app
RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/pip  \
    pip install -e "libs/kotaemon[all]" \
    && pip install -e "libs/ktem" \
    pip install graphrag future \
    && pip install "pdfservices-sdk@git+https://github.com/niallcm/pdfservices-python-sdk.git@bump-and-unfreeze-requirements"

RUN rm -rf /root/.cache/pip

CMD ["python", "app.py"]

# Full
FROM base_image as full

# Additional dependencies for full version
RUN apt-get update -qqy && \
    apt-get install -y --no-install-recommends \
      tesseract-ocr \
      tesseract-ocr-jpn \
      libsm6 \
      libxext6 \
      ffmpeg \
      libmagic-dev \
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/pip  \
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

COPY . /app

RUN --mount=type=ssh  \
    --mount=type=cache,target=/root/.cache/pip  \
    pip install -e "libs/kotaemon[all]" \
    && pip install -e "libs/ktem" \
    && pip install graphrag future unstructured[all-docs] \
    && pip install "pdfservices-sdk@git+https://github.com/niallcm/pdfservices-python-sdk.git@bump-and-unfreeze-requirements"

RUN rm -rf /root/.cache/pip

CMD ["python", "app.py"]
