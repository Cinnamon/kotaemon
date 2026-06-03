import logging
from dataclasses import dataclass, field

from ktem.llms.manager import llms

from kotaemon.base import AIMessage, Document, HumanMessage
from kotaemon.llms import ChatLLM, PromptTemplate

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class SuggestFollowupQuesPipeline:
    llm: ChatLLM = field(default_factory=lambda: llms.get_default())
    prompt_template: str = (
        "Based on the chat history above, generate 3 to 5 follow-up questions. "
        "Respond in JSON with 'questions' key. Answer in {lang}."
    )
    extra_prompt: str = (
        'Example: {"questions": ["question 1", "question 2"]}'
    )
    lang: str = "English"

    def run(self, chat_history: list[tuple[str, str]]) -> Document:
        prompt = (
            PromptTemplate(self.prompt_template).populate(lang=self.lang)
            + self.extra_prompt
        )
        messages = []
        for human, ai in chat_history[-3:]:
            messages.append(HumanMessage(content=human))
            messages.append(AIMessage(content=ai))
        messages.append(HumanMessage(content=prompt))
        return self.llm(messages)
