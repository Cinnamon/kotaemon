from __future__ import annotations

from dataclasses import dataclass

from kotaemon.base.describe import DataclassDescribe, describe_dataclass
from kotaemon.llms.base import BaseLLM


@dataclass(kw_only=True)
class LLM(BaseLLM):
    @classmethod
    def describe(cls) -> DataclassDescribe:
        return describe_dataclass(cls)
