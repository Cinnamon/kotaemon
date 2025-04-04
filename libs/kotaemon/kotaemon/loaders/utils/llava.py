import json
import logging
from typing import Any, List

import requests
from decouple import config

logger = logging.getLogger(__name__)


def generate_llava(
    endpoint: str,
    images: str | List[str],
    prompt: str,
    max_tokens: int = 512,
    max_images: int = 10,
) -> str:
    # TODO: Figure out what to put here
    api_key = config("AZURE_OPENAI_API_KEY", default="")
    headers = {"Content-Type": "application/json", "api-key": api_key}

    if isinstance(images, str):
        images = [images]

    payload = {
        "model": "llava:7b",
        "prompt": prompt,
        "images": [image for image in images[:max_images]],
        "stream": False
    }

    if len(images) > max_images:
        print(f"Truncated to {max_images} images (original {len(images)} images")

    response = requests.post(endpoint, headers=headers, json=payload)
    output = response.json()
    output = output["response"]

    try:
        response.raise_for_status()
    except Exception as e:
        logger.exception(f"Error generating llava: {response.text}; error {e}")
        return ""

    return output
