from ..llms import ChatLLM
from .base import BaseChatBot


class SimpleRespondentChatbot(BaseChatBot):
    """Simple text respondent chatbot that essentially wraps around a chat LLM"""

    llm: ChatLLM

    def _get_message(self) -> str:
        return self.llm(self.history).text
