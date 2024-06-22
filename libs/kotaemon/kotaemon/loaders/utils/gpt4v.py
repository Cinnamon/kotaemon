import json
import logging
from typing import Any, List

import requests
from decouple import config

logger = logging.getLogger(__name__)


def generate_gpt4v(
    endpoint: str,
    images: str | List[str],
    prompt: str,
    max_tokens: int = 512,
    max_images: int = 10,
) -> str:
    # OpenAI API Key
    api_key = config("AZURE_OPENAI_API_KEY", default="")
    headers = {"Content-Type": "application/json", "api-key": api_key}

    if isinstance(images, str):
        images = [images]

    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ]
                + [
                    {
                        "type": "image_url",
                        "image_url": {"url": image},
                    }
                    for image in images[:max_images]
                ],
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0,
    }

    if len(images) > max_images:
        print(f"Truncated to {max_images} images (original {len(images)} images")

    response = requests.post(endpoint, headers=headers, json=payload)

    try:
        response.raise_for_status()
    except Exception as e:
        logger.exception(f"Error generating gpt4v: {response.text}; error {e}")
        return ""

    output = response.json()
    output = output["choices"][0]["message"]["content"]
    return output


def stream_gpt4v(
    endpoint: str,
    images: str | List[str],
    prompt: str,
    max_tokens: int = 512,
    max_images: int = 10,
) -> Any:
    # OpenAI API Key
    api_key = config("AZURE_OPENAI_API_KEY", default="")
    headers = {"Content-Type": "application/json", "api-key": api_key}

    if isinstance(images, str):
        images = [images]

    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ]
                + [
                    {
                        "type": "image_url",
                        "image_url": {"url": image},
                    }
                    for image in images[:max_images]
                ],
            }
        ],
        "max_tokens": max_tokens,
        "stream": True,
        "logprobs": True,
        "temperature": 0,
    }
    if len(images) > max_images:
        print(f"Truncated to {max_images} images (original {len(images)} images")
    try:
        response = requests.post(endpoint, headers=headers, json=payload, stream=True)
        assert response.status_code == 200, str(response.content)
        output = ""
        logprobs = []
        for line in response.iter_lines():
            if line:
                if line.startswith(b"\xef\xbb\xbf"):
                    line = line[9:]
                else:
                    line = line[6:]
                try:
                    if line == "[DONE]":
                        break
                    line = json.loads(line.decode("utf-8"))
                except Exception:
                    break
                if len(line["choices"]):
                    if line["choices"][0].get("logprobs") is None:
                        _logprobs = []
                    else:
                        _logprobs = [
                            logprob["logprob"]
                            for logprob in line["choices"][0]["logprobs"].get(
                                "content", []
                            )
                        ]

                    output += line["choices"][0]["delta"].get("content", "")
                    logprobs += _logprobs
                    yield line["choices"][0]["delta"].get("content", ""), _logprobs

    except Exception as e:
        logger.error(f"Error streaming gpt4v {e}")
        logprobs = []
        output = ""

    return output, logprobs
