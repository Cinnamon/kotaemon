from __future__ import annotations

import logging
from dataclasses import dataclass

from kotaemon.base import BaseComponent
from kotaemon.base.describe import DataclassDescribe, describe_dataclass
from kotaemon.llms.base import BaseLLM

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class ChatLLM(BaseLLM):
    @classmethod
    def describe(cls) -> DataclassDescribe:
        return describe_dataclass(cls)

    def flow(self):
        if self.inflow is None:
            raise ValueError("No inflow provided.")

        if not isinstance(self.inflow, BaseComponent):
            raise ValueError(
                f"inflow must be a BaseComponent, found {type(self.inflow)}"
            )

        text = self.inflow.flow().text
        return self.__call__(text)
