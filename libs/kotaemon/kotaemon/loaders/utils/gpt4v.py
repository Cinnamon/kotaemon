import json
import os
from typing import Any, List

import requests
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = (
    "https://bleh-dummy.openai.azure.com/openai/deployments/gpt-4-vision/"
    "chat/completions?api-version=2023-07-01-preview"
)


def generate_gpt4v(images: str | List[str], prompt: str, max_tokens: int = 512) -> str:
    # OpenAI API Key
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
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
        response = requests.post(ENDPOINT, headers=headers, json=payload)
        output = response.json()
        output = output["choices"][0]["message"]["content"]
    except Exception:
        output = ""
    return output


def generate_gpt4v_stream(
    images: str | List[str], prompt: str, max_tokens: int = 512
) -> Any:
    # OpenAI API Key
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    headers = {"Content-Type": "application/json", "api-key": api_key}

    if isinstance(images, str):
        images = [images]

    payload = {
        "model": "gpt-4-vision-preview",
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

    response = requests.post(ENDPOINT, headers=headers, json=payload, stream=True)
    assert response.status_code == 200, str(response.content)
    output = ""
    for line in response.iter_lines():
        if line:
            line = line[6:]
            try:
                line = json.loads(line)
            except Exception:
                break
            output += line["choices"][0]["delta"].get("content", "")
            yield output
