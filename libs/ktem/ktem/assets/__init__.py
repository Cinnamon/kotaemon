import os
from pathlib import Path

PDFJS_VERSION_DIST: str = os.getenv("PDFJS_VERSION_DIST", "pdfjs-4.0.379-dist")
PDFJS_PREBUILT_DIR: Path = Path(__file__).parent / "prebuilt" / PDFJS_VERSION_DIST
