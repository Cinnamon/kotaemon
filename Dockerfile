FROM ghcr.io/bookandlover/kotaemon:main-full

RUN apt-get update -qqy && \
   apt-get install -y --no-install-recommends \
   build-essential \
   python3-dev \
   && apt-get clean \
   && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
   "graphrag<=0.3.6" \
   future \
   && pip install --no-cache-dir nano-graphrag \
   && pip uninstall -y hnswlib chroma-hnswlib \
   && pip install --no-cache-dir chroma-hnswlib \
   && pip install --no-cache-dir "docling<=2.5.2" \
   && rm -rf ~/.cache/pip

CMD ["python", "app.py"]