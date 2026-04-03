# Docling

Kotaemon provides a [Docling](https://github.com/DS4SD/docling) reader to enable local document ingestion with structure-aware parsing, including text, tables, and figures.
The reader is located under `kotaemon/loaders/docling_loader`.

## Prerequisites

- Install Docling:

```bash
pip install -e "libs/kotaemon[docling]"
```

- Configure optional figure captioning:

Docling can generate figure captions when a VLM endpoint is available. Set `KH_VLM_ENDPOINT` in your `.env` file or application settings to enable captioning.

```bash
KH_VLM_ENDPOINT=http://your-vlm-endpoint
```

If `KH_VLM_ENDPOINT` is not set, Docling will still extract text, tables, and figure metadata, but it will skip generated figure captions.

## Configure the loader

1. Run Kotaemon and open the app UI.
2. Navigate to Settings → Retrieval Settings → File loader.
3. Select `Docling (figure+table extraction)`.
4. Save the settings, then upload or ingest a document. Kotaemon will use Docling during indexing and convert extracted content into `Document` objects.
