from typing import Optional

from kotaemon.base import Param

from .openai import ChatOpenAI


class ChatMiniMax(ChatOpenAI):
    """MiniMax chat model, using the OpenAI-compatible API

    MiniMax provides large language models accessible via an OpenAI-compatible
    endpoint. Supported models: MiniMax-M2.7, MiniMax-M2.7-highspeed,
    MiniMax-M2.5, MiniMax-M2.5-highspeed.

    Both models support a 204,800-token context window.

    Note:
        - Temperature must be in (0.0, 1.0]; zero is not accepted.
        - The ``response_format`` parameter is not supported and will be
          removed from requests automatically.

    Attributes:
        base_url: API base URL. Defaults to the global endpoint
            ``https://api.minimax.io/v1``. The China endpoint
            ``https://api.minimaxi.com/v1`` is also available.
        model: Model ID to use. Defaults to ``MiniMax-M2.7``.
        api_key: MiniMax API key (``MINIMAX_API_KEY``).
    """

    base_url: Optional[str] = Param(
        "https://api.minimax.io/v1",
        help=(
            "MiniMax API base URL. Use https://api.minimax.io/v1 (global) "
            "or https://api.minimaxi.com/v1 (China)."
        ),
    )
    model: str = Param(
        "MiniMax-M2.7",
        help="MiniMax model ID (MiniMax-M2.7, MiniMax-M2.7-highspeed, MiniMax-M2.5, or MiniMax-M2.5-highspeed)",
        required=True,
    )
    temperature: Optional[float] = Param(
        1.0,
        help=(
            "Sampling temperature. Must be in (0.0, 1.0]. "
            "MiniMax does not accept 0."
        ),
    )

    def prepare_params(self, **kwargs):
        params = super().prepare_params(**kwargs)
        # MiniMax does not support response_format
        params.pop("response_format", None)
        # Clamp temperature: MiniMax rejects 0
        if "temperature" in params and params["temperature"] is not None:
            if params["temperature"] <= 0:
                params["temperature"] = 0.01
        return params
