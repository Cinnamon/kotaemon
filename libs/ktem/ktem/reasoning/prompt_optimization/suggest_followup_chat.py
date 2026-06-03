import logging

from ktem.llms.manager import llms

from kotaemon.base import AIMessage, BaseComponent, Document, HumanMessage, Node
from kotaemon.llms import ChatLLM, PromptTemplate

logger = logging.getLogger(__name__)


class SuggestFollowupQuesPipeline(BaseComponent):
    """Suggest a list of follow-up questions based on the chat history."""

    llm: ChatLLM = Node(default_callback=lambda _: llms.get_default())
    SUGGEST_QUESTIONS_PROMPT_TEMPLATE = (
        "Based on the chat history above. "
        "your task is to generate 3 to 5 relevant follow-up questions. "
        "These questions should be simple, very concise, "
        "and designed to guide the conversation further. "
        "Respond in JSON format with 'questions' key. "
        "Answer using the language {lang} same as the question. "
    )
    prompt_template: str = SUGGEST_QUESTIONS_PROMPT_TEMPLATE
    extra_prompt: str = """Example of valid response:
```json
{
    "questions": ["the weather is good", "what's your favorite city"]
}
```"""
    lang: str = "English"

    def run(self, chat_history: list[tuple[str, str]]) -> Document:
        prompt_template = PromptTemplate(self.prompt_template)
        prompt = prompt_template.populate(lang=self.lang) + self.extra_prompt

        messages = []
        for human, ai in chat_history[-3:]:
            messages.append(HumanMessage(content=human))
            messages.append(AIMessage(content=ai))

        messages.append(HumanMessage(content=prompt))

        return self.llm(messages)
