from abc import abstractmethod
from typing import List, Optional

from kotaemon.base import LLMInterface
from kotaemon.base.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage


class BaseChatBot:
    @abstractmethod
    def run(self, messages: List[BaseMessage]) -> LLMInterface:
        ...

    def __call__(self, messages: List[BaseMessage]) -> LLMInterface:
        return self.run(messages)


class ChatConversation:
    def __init__(self, bot: BaseChatBot, *, system_message: str = "") -> None:
        self.system_message = system_message
        self.bot = bot
        self._history: List[BaseMessage] = []

    def run(self, message: HumanMessage) -> Optional[BaseMessage]:
        user_message = (
            HumanMessage(content=message) if isinstance(message, str) else message
        )
        self.history.append(user_message)
        output = self.bot(self.history).text
        if output is None:
            return None
        output_message = AIMessage(content=output)
        self.history.append(output_message)
        return output_message

    def __call__(self, message: HumanMessage) -> Optional[BaseMessage]:
        return self.run(message)

    @property
    def history(self):
        return self._history

    @history.setter
    def history(self, value):
        self._history = value
