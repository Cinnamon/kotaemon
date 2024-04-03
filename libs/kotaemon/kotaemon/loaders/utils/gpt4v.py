import json
from typing import Any, List

import requests
from decouple import config


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

    try:
        response = requests.post(endpoint, headers=headers, json=payload)
        output = response.json()
        output = output["choices"][0]["message"]["content"]
    except Exception:
        output = ""
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
    }
    try:
        response = requests.post(endpoint, headers=headers, json=payload, stream=True)
        assert response.status_code == 200, str(response.content)
        output = ""
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
                    output += line["choices"][0]["delta"].get("content", "")
                    yield line["choices"][0]["delta"].get("content", "")
    except Exception:
        output = ""
    return output
