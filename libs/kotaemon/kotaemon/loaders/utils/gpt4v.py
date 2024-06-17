import json
import logging
from typing import Any, List

import numpy as np
import requests
from decouple import config

logger = logging.getLogger(__name__)


def generate_gpt4v(
    endpoint: str, images: str | List[str], prompt: str, max_tokens: int = 512
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
                    for image in images
                ],
            }
        ],
        "max_tokens": max_tokens,
    }

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
    endpoint: str, images: str | List[str], prompt: str, max_tokens: int = 512
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
                    for image in images
                ],
            }
        ],
        "max_tokens": max_tokens,
        "stream": True,
        "logprobs": True,
        "top_logprobs": 1,
    }
    try:
        response = requests.post(endpoint, headers=headers, json=payload, stream=True)
        assert response.status_code == 200, str(response.content)
        output = ""
        probs = []
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
                    _probs = []
                    for top_logprob in line["choices"][0]["logprobs"].get(
                        "content", []
                    ):
                        _probs.append(
                            np.round(
                                np.exp(top_logprob["top_logprobs"][0]["logprob"]), 2
                            )
                        )

                    output += line["choices"][0]["delta"].get("content", "")
                    probs += _probs
                    yield line["choices"][0]["delta"].get("content", ""), _probs

    except Exception as e:
        logger.error(f"Error streaming gpt4v {e}")
        output = ""

    return output, probs
