# Docling

Kotaemon provides a [Docling](https://github.com/DS4SD/docling) reader to enable local document ingestion with structure-aware parsing, including text, tables, and figures.
The reader is located under `kotaemon/loaders/docling_loader`.

## Prerequisites

- Install Docling:

```bash
uv pip install -e "libs/kotaemon[docling]"
```

- Configure optional figure captioning:

Docling can generate figure captions when a VLM endpoint is available. Set `KH_VLM_ENDPOINT` in your `.env` file or application settings to enable captioning.

```bash
KH_VLM_ENDPOINT=http://your-vlm-endpoint
```

If `KH_VLM_ENDPOINT` is not set, Docling will still extract text, tables, and figure metadata, but it will skip generated figure captions.

### Configure offline models and OCR

Docling can use pre-downloaded model artifacts instead of fetching them during
document ingestion. The OCR engine and its languages can also be selected with
environment variables:

```env
KH_DOCLING_ARTIFACTS_PATH=/opt/docling-models
KH_DOCLING_OCR_ENGINE=tesseract_cli
KH_DOCLING_OCR_LANGUAGES=eng,fra
```

Supported OCR engines are `easyocr`, `tesseract`, `tesseract_cli`, and `ocrmac`.
Install the selected engine and its language data separately. When these settings
are omitted, Kotaemon keeps Docling's default behavior.

## Configure the loader

1. Run Kotaemon and open the app UI.
2. Navigate to Settings → Retrieval Settings → File loader.
3. Select `Docling (figure+table extraction)`.
4. Save the settings, then upload or ingest a document. Kotaemon will use Docling during indexing and convert extracted content into `Document` objects.
