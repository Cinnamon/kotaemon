import logging
from dataclasses import dataclass, field

from ktem.llms.manager import llms

from kotaemon.base import AIMessage, Document, HumanMessage
from kotaemon.llms import ChatLLM, PromptTemplate

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class SuggestConvNamePipeline:
    llm: ChatLLM = field(default_factory=lambda: llms.get_default())
    prompt_template: str = (
        "Suggest a good conversation name (max 10 words) in {lang}. "
        "Output only the name."
    )
    lang: str = "English"

    def run(self, chat_history: list[tuple[str, str]]) -> Document:  # type: ignore
        prompt = PromptTemplate(self.prompt_template).populate(lang=self.lang)
        messages = []
        for human, ai in chat_history:
            messages.append(HumanMessage(content=human))
            messages.append(AIMessage(content=ai))
        messages.append(HumanMessage(content=prompt))
        return self.llm(messages)

    def __call__(self, chat_history: list[tuple[str, str]]) -> Document:
        return self.run(chat_history)
