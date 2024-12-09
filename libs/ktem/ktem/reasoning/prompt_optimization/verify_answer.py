import http.client
import json
from typing import Any

from decouple import config

AZURE_CONTENT_SAFETY_ENDPOINT = config("AZURE_CONTENT_SAFETY_ENDPOINT", default="")
AZURE_CONTENT_SAFETY_KEY = config("AZURE_CONTENT_SAFETY_KEY", default="")
AZURE_OPENAI_ENDPOINT_REASONING = config("AZURE_OPENAI_ENDPOINT_REASONING", default="")
AZURE_OPENAI_DEPLOYMENT_NAME_REASONING = config(
    "AZURE_OPENAI_DEPLOYMENT_NAME_REASONING", default=""
)


def verify_answer_groundedness_azure(
    query: str,
    answer: str,
    docs: list[str],
) -> dict[str, Any]:
    conn = http.client.HTTPSConnection(AZURE_CONTENT_SAFETY_ENDPOINT)
    payload = json.dumps(
        {
            "domain": "Generic",
            "task": "QnA",
            "qna": {"query": query},
            "text": answer,
            "groundingSources": docs,
            "reasoning": True,
            "llmResource": {
                "resourceType": "AzureOpenAI",
                "azureOpenAIEndpoint": AZURE_OPENAI_ENDPOINT_REASONING,
                "azureOpenAIDeploymentName": AZURE_OPENAI_DEPLOYMENT_NAME_REASONING,
            },
        }
    )
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_CONTENT_SAFETY_KEY,
        "Content-Type": "application/json",
    }
    conn.request(
        "POST",
        "/contentsafety/text:detectGroundedness?api-version=2024-09-15-preview",
        payload,
        headers,
    )
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    return json.loads(data)
