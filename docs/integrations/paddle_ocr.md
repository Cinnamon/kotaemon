# PaddleOCR

Kotaemon provides two [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) readers to enable document ingestion with full layout understanding, including multilingual text, tables, figures, formulas, and seals.

- `PaddleOCRVLReader`: Wraps the PaddleOCR-VL 1.5 visual-language model for robust layout and VQA-based parsing.
- `PPStructureV3Reader`: Uses the PPStructureV3 pipeline for structured layout analysis, including table and chart detection.

Both readers are located under `kotaemon/loaders/paddleocr_loader`.

## Prerequisites

- Install PaddlePaddle:
  - Ensure that the installed PaddlePaddle version matches your system configuration and hardware (CPU/GPU). For additional wheel options, refer to the [PaddlePaddle official website](https://www.paddlepaddle.org.cn/install/quick?docurl=undefined).
  - Check device support for [PaddleOCR-VL](https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/PaddleOCR-VL.html#inference-device-support-for-paddleocr-vl).

```bash
# CPU
pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

# gpu，requires GPU driver version ≥550.54.14 (Linux) or ≥550.54.14 (Windows)
pip install paddlepaddle-gpu==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu130/
```

- Install the PaddleOCR doc parser extras:

```bash
pip install -e "libs/kotaemon[paddleocr]"
```

- Configure the device: You can set the `PADDLE_DEVICE` environment variable in your .env file to control the execution device.

```bash
PADDLE_DEVICE=gpu # cpu, gpu:0
```

## Configure the loader

1. Run Kotaemon and open the app UI.
2. Navigate to Settings → File Loader (under indexing or ingestion settings).
3. Select one of the PaddleOCR loaders:
   - `PaddleOCR PPStructureV3 (table+figure extraction)`
   - `PaddleOCR-VL (VLM document parsing)`
4. Save the settings, then upload or ingest a document. Kotaemon will automatically use the selected PaddleOCR loader during indexing and convert extracted content into Document objects.
