from dataclasses import dataclass, field

from ktem.llms.manager import llms

from kotaemon.base import Document, HumanMessage, SystemMessage
from kotaemon.llms import ChatLLM, PromptTemplate

DEFAULT_REWRITE_PROMPT = (
    "Given the following question, rephrase and expand it "
    "to help you do better answering. Maintain all information "
    "in the original question. Keep the question as concise as possible. "
    "Only output the rephrased question without additional information. "
    "Give answer in {lang}\n"
    "Original question: {question}\n"
    "Rephrased question: "
)


@dataclass(kw_only=True)
class RewriteQuestionPipeline:
    """Rewrite user question."""

    llm: ChatLLM = field(default_factory=lambda: llms.get_default())
    rewrite_template: str = DEFAULT_REWRITE_PROMPT
    lang: str = "English"

    def run(self, question: str) -> Document:  # type: ignore
        prompt_template = PromptTemplate(self.rewrite_template)
        prompt = prompt_template.populate(question=question, lang=self.lang)
        messages = [
            SystemMessage(content="You are a helpful assistant"),
            HumanMessage(content=prompt),
        ]
        return self.llm(messages)

    def __call__(self, **kwargs) -> Document:
        return self.run(**kwargs)
