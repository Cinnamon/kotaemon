from abc import abstractmethod
from typing import List, Optional

from theflow import SessionFunction

from kotaemon.base import BaseComponent, LLMInterface
from kotaemon.base.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage


class BaseChatBot(BaseComponent):
    @abstractmethod
    def run(self, messages: List[BaseMessage]) -> LLMInterface:
        ...


def session_chat_storage(obj):
    """Store using the bot location rather than the session location"""
    return obj._store_result


class ChatConversation(SessionFunction):
    """Base implementation of a chat bot component

    A chatbot component should:
        - handle internal state, including history messages
        - return output for a given input
    """

    class Config:
        store_result = session_chat_storage

    system_message: str = ""
    bot: BaseChatBot

    def __init__(self, *args, **kwargs):
        self._history: List[BaseMessage] = []
        self._store_result = (
            f"{self.__module__}.{self.__class__.__name__},uninitiated_bot"
        )
        super().__init__(*args, **kwargs)

    def run(self, message: HumanMessage) -> Optional[BaseMessage]:
        """Chat, given a message, return a response

        Args:
            message: The message to respond to

        Returns:
            The response to the message. If None, no response is sent.
        """
        user_message = (
            HumanMessage(content=message) if isinstance(message, str) else message
        )
        self.history.append(user_message)

        output = self.bot(self.history).text
        output_message = None
        if output is not None:
            output_message = AIMessage(content=output)
            self.history.append(output_message)

        return output_message

    def start_session(self):
        self._store_result = self.bot.config.store_result
        super().start_session()
        if not self.history and self.system_message:
            system_message = SystemMessage(content=self.system_message)
            self.history.append(system_message)

    def end_session(self):
        super().end_session()
        self._history = []

    def check_end(
        self,
        history: Optional[List[BaseMessage]] = None,
        user_message: Optional[HumanMessage] = None,
        bot_message: Optional[AIMessage] = None,
    ) -> bool:
        """Check if a conversation should end"""
        if user_message is not None and user_message.content == "":
            return True

        return False

    def terminal_session(self):
        """Create a terminal session"""
        self.start_session()
        print(">> Start chat:")

        while True:
            human = HumanMessage(content=input("Human: "))
            if self.check_end(history=self.history, user_message=human):
                break

            output = self(human)
            if output is None:
                print("AI: <No response>")
            else:
                print("AI:", output.content)

            if self.check_end(history=self.history, bot_message=output):
                break

        self.end_session()

    @property
    def history(self):
        return self._history

    @history.setter
    def history(self, value):
        self._history = value
        self._variablex()
