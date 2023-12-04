from __future__ import annotations

import logging

from kotaemon.base import BaseComponent

logger = logging.getLogger(__name__)


class ChatLLM(BaseComponent):
    def flow(self):
        if self.inflow is None:
            raise ValueError("No inflow provided.")

        if not isinstance(self.inflow, BaseComponent):
            raise ValueError(
                f"inflow must be a BaseComponent, found {type(self.inflow)}"
            )

        text = self.inflow.flow().text
        return self.__call__(text)
