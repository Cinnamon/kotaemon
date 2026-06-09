from __future__ import annotations

import logging
from dataclasses import dataclass

from kotaemon.base.describe import DataclassDescribe, describe_dataclass
from kotaemon.llms.base import BaseLLM

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class ChatLLM(BaseLLM):
    @classmethod
    def describe(cls) -> DataclassDescribe:
        return describe_dataclass(cls)
