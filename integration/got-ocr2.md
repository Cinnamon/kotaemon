## Extension Manager and GOT-OCR2.0 Loader

## Key Features

### 1. **GOCR2 as Image Reader**

- **GOCR2ImageReader** is a new class designed to read images using the [**GOCR-2.0** OCR engine](https://github.com/Ucas-HaoranWei/GOT-OCR2.0).
- This reader is initialized with an endpoint that defaults to `http://localhost:8881/ai/infer/` for the OCR service, but can be configured through an environment variable `GOCR2_ENDPOINT` or passed explicitly.
- It uses exponential backoff retry mechanisms to ensure robustness during API calls.
- Supports loading image files and extracting their text content, returning structured document data.

#### Setup

- We provide the docker image, with fastapi for serving the GOT-OCR2.0. Pull the image from:

```bash
docker run -d --gpus all -p 8881:8881 ghcr.io/phv2312/got-ocr2.0:main
```

- Detail implementation is placed at [ocr_loader.py](/libs/kotaemon/kotaemon/loaders/ocr_loader.py)

### 2. **Extension Manager**

- ExtensionManager allows users to dynamically manage multiple loaders for different file types.

- Users can switch between multiple loaders for the same file extension, such as using the GOCR2ImageReader or a
  different unstructured data parser for .png files. This provides the flexibility to choose the best-suited loader for the task at hand.

- To change the default loader, go to **Settings**, then **Extension settings**. It displays a grid of extensions and
  its supported loaders. Any modification will be saved to DB as other settings do.
