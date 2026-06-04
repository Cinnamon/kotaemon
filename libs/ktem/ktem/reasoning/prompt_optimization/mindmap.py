import logging
from dataclasses import dataclass, field
from textwrap import dedent

from ktem.llms.manager import llms

from kotaemon.base import Document, HumanMessage, SystemMessage
from kotaemon.llms import ChatLLM, PromptTemplate

logger = logging.getLogger(__name__)

MINDMAP_HTML_EXPORT_TEMPLATE = dedent(
    """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Mindmap</title>
    <style>
      svg.markmap { width: 100%; height: 100vh; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@0.16"></script>
  </head>
  <body>{markmap_div}</body>
</html>
"""
)


@dataclass(kw_only=True)
class CreateMindmapPipeline:
    llm: ChatLLM = field(default_factory=lambda: llms.get_default())
    SYSTEM_PROMPT: str = (
        'From now on you will behave as "MapGPT" and create PlantUML mind maps.'
    )
    MINDMAP_PROMPT_TEMPLATE: str = (
        "Question:\n{question}\n\nContext:\n{context}\n\n"
        "Generate PlantUML mindmap using @startmindmap ... @endmindmap."
    )
    prompt_template: str = MINDMAP_PROMPT_TEMPLATE

    @classmethod
    def convert_uml_to_markdown(cls, text: str) -> str:
        try:
            text = text.split("@startmindmap")[-1].split("@endmindmap")[0]
            return text.strip().replace("*", "#")
        except IndexError:
            return ""

    def run(self, question: str, context: str) -> Document:  # type: ignore
        prompt = PromptTemplate(self.prompt_template).populate(
            question=question, context=context
        )
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        uml_text = self.llm(messages).text
        return Document(text=self.convert_uml_to_markdown(uml_text))

    def __call__(self, question: str, context: str) -> Document:
        return self.run(question, context)
