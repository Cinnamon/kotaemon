"""Vision-based image reader using LLM with vision capabilities.

This reader uses GPT-4o or similar vision models to describe image content,
making it searchable and retrievable in the RAG system.
"""

import base64
import logging
from pathlib import Path
from typing import List, Optional

from decouple import config
from llama_index.core.readers.base import BaseReader

from kotaemon.base import Document

logger = logging.getLogger(__name__)

DEFAULT_IMAGE_DESCRIPTION_PROMPT = """Analyze this image in detail. Describe:
1. The main content and subject matter
2. Any text visible in the image (transcribe it exactly)
3. Key visual elements, diagrams, charts, or figures
4. Technical details if it's a technical diagram or schematic
5. Any other relevant information

Provide a comprehensive description that would help someone understand this image without seeing it."""


class VisionImageReader(BaseReader):
    """Read images using Vision Language Models (GPT-4o, etc.)

    This reader converts images to text descriptions using vision-capable LLMs,
    making the image content searchable in a RAG system.

    Args:
        api_key: OpenAI API key. If not provided, will use OPENAI_API_KEY env var.
        model: Vision model to use. Default is "gpt-4o".
        base_url: API base URL. Default is OpenAI's API.
        prompt: Custom prompt for image description.
        max_tokens: Maximum tokens for the response.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
        prompt: str = DEFAULT_IMAGE_DESCRIPTION_PROMPT,
        max_tokens: int = 1024,
    ):
        super().__init__()
        self.api_key = api_key or config("OPENAI_API_KEY", default="")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.prompt = prompt
        self.max_tokens = max_tokens

    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64 data URL."""
        suffix = image_path.suffix.lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
        }
        mime_type = mime_types.get(suffix, "image/png")

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        return f"data:{mime_type};base64,{image_data}"

    def _describe_image(self, image_path: Path) -> str:
        """Use vision model to describe the image."""
        import requests

        if not self.api_key:
            logger.warning("No API key provided for VisionImageReader")
            return ""

        image_url = self._encode_image(image_path)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url, "detail": "high"},
                        },
                    ],
                }
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0,
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error describing image {image_path}: {e}")
            return ""

    def load_data(
        self,
        file: Path,
        extra_info: Optional[dict] = None,
        **kwargs,
    ) -> List[Document]:
        """Load and describe an image file.

        Args:
            file: Path to the image file
            extra_info: Additional metadata to include

        Returns:
            List containing a single Document with the image description
        """
        file_path = Path(file).resolve()
        extra_info = extra_info or {}

        # Get image description from vision model
        description = self._describe_image(file_path)

        if not description:
            logger.warning(f"Could not generate description for {file_path}")
            description = f"Image file: {file_path.name}"

        # Create document with description
        metadata = {
            "file_name": file_path.name,
            "file_path": str(file_path),
            "file_type": "image",
            **extra_info,
        }

        return [Document(text=description, metadata=metadata)]
