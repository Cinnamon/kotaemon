import html
import logging
from typing import AnyStr, Optional, Type

from ktem.llms.manager import llms
from ktem.reasoning.base import BaseReasoning
from ktem.utils.render import Render
from langchain.text_splitter import CharacterTextSplitter
from pydantic import BaseModel, Field

from kotaemon.agents import (
    BaseTool,
    GoogleSearchTool,
    LLMTool,
    ReactAgent,
    WikipediaTool,
)
from kotaemon.base import BaseComponent, Document, HumanMessage, Node, SystemMessage
from kotaemon.llms import ChatLLM, PromptTemplate

logger = logging.getLogger(__name__)


class DocSearchArgs(BaseModel):
    query: str = Field(..., description="a search query as input to the doc search")


class DocSearchTool(BaseTool):
    name: str = "docsearch"
    description: str = (
        "A vector store that searches for similar and related content in a list "
        "of documents. The result is a huge chunk of text related to your search "
        "but can also contain irrelevant info. Input should be a search query about "
        "specific topic, do not include general query such as "
        "'SearchDoc[insurance policy terms & conditions]'."
    )
    args_schema: Optional[Type[BaseModel]] = DocSearchArgs
    retrievers: list[BaseComponent] = []

    def _run_tool(self, query: AnyStr) -> AnyStr:
        docs = []
        doc_ids = []
        for retriever in self.retrievers:
            for doc in retriever(text=query):
                if doc.doc_id not in doc_ids:
                    docs.append(doc)
                    doc_ids.append(doc.doc_id)

        return self.prepare_evidence(docs)

    def prepare_evidence(self, docs, trim_len: int = 4000):
        evidence = ""
        table_found = 0

        for _id, retrieved_item in enumerate(docs):
            retrieved_content = ""
            page = retrieved_item.metadata.get("page_label", None)
            source = filename = retrieved_item.metadata.get("file_name", "-")
            if page:
                source += f" (Page {page})"
            if retrieved_item.metadata.get("type", "") == "table":
                if table_found < 5:
                    retrieved_content = retrieved_item.metadata.get("table_origin", "")
                    if retrieved_content not in evidence:
                        table_found += 1
                        evidence += (
                            f"<br><b>Table from {source}</b>\n"
                            + retrieved_content
                            + "\n<br>"
                        )
            elif retrieved_item.metadata.get("type", "") == "chatbot":
                retrieved_content = retrieved_item.metadata["window"]
                evidence += (
                    f"<br><b>Chatbot scenario from {filename} (Row {page})</b>\n"
                    + retrieved_content
                    + "\n<br>"
                )
            elif retrieved_item.metadata.get("type", "") == "image":
                retrieved_content = retrieved_item.metadata.get("image_origin", "")
                retrieved_caption = html.escape(retrieved_item.get_content())
                # evidence += (
                #     f"<br><b>Figure from {source}</b>\n"
                #     + f"<img width='85%' src='{retrieved_content}' "
                #     + f"alt='{retrieved_caption}'/>"
                #     + "\n<br>"
                # )
                evidence += (
                    f"<br><b>Figure from {source}</b>\n" + retrieved_caption + "\n<br>"
                )
            else:
                if "window" in retrieved_item.metadata:
                    retrieved_content = retrieved_item.metadata["window"]
                else:
                    retrieved_content = retrieved_item.text
                retrieved_content = retrieved_content.replace("\n", " ")
                if retrieved_content not in evidence:
                    evidence += (
                        f"<br><b>Content from {source}: </b> "
                        + retrieved_content
                        + " \n<br>"
                    )

            print("Retrieved #{}: {}".format(_id, retrieved_content[:100]))
            print("Score", retrieved_item.metadata.get("relevance_score", None))

        # trim context by trim_len
        if evidence:
            text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
                chunk_size=trim_len,
                chunk_overlap=0,
                separator=" ",
                model_name="gpt-3.5-turbo",
            )
        texts = text_splitter.split_text(evidence)
        evidence = texts[0]

        return Document(content=evidence)


TOOL_REGISTRY = {
    "Google": GoogleSearchTool(),
    "Wikipedia": WikipediaTool(),
    "LLM": LLMTool(),
    "SearchDoc": DocSearchTool(),
}

DEFAULT_REWRITE_PROMPT = (
    "Given the following question, rephrase and expand it "
    "to help you do better answering. Maintain all information "
    "in the original question. Keep the question as concise as possible. "
    "Give answer in {lang}\n"
    "Original question: {question}\n"
    "Rephrased question: "
)


class RewriteQuestionPipeline(BaseComponent):
    """Rewrite user question

    Args:
        llm: the language model to rewrite question
        rewrite_template: the prompt template for llm to paraphrase a text input
        lang: the language of the answer. Currently support English and Japanese
    """

    llm: ChatLLM = Node(default_callback=lambda _: llms.get_default())
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


class ReactAgentPipeline(BaseReasoning):
    """Question answering pipeline using ReAct agent."""

    class Config:
        allow_extra = True

    retrievers: list[BaseComponent]
    agent: ReactAgent = ReactAgent.withx()
    rewrite_pipeline: RewriteQuestionPipeline = RewriteQuestionPipeline.withx()
    use_rewrite: bool = False

    def prepare_citation(self, all_steps) -> list[Document]:
        outputs = []
        for step_id, (step, output) in enumerate(all_steps):
            header = "<b>Step {id}</b>: {log}".format(id=step_id + 1, log=step.log)
            content = (
                "<b>Action</b>: <em>{tool}[{input}]</em>\n\n<b>Output</b>: {output}"
            ).format(
                tool=step.tool if step_id < len(all_steps) - 1 else "",
                input=step.tool_input.replace("\n", "")
                if step_id < len(all_steps) - 1
                else "",
                output=output if step_id < len(all_steps) - 1 else "Finished",
            )
            outputs.append(
                Document(
                    channel="info",
                    content=Render.collapsible(
                        header=header,
                        content=Render.table(content),
                        open=True,
                    ),
                )
            )
        return outputs

    async def ainvoke(  # type: ignore
        self, message, conv_id: str, history: list, **kwargs  # type: ignore
    ) -> Document:
        if self.use_rewrite:
            rewrite = await self.rewrite_pipeline(question=message)
            message = rewrite.text

        answer = self.agent(message)
        self.report_output(Document(content=answer.text, channel="chat"))

        intermediate_steps = answer.intermediate_steps
        for _ in self.prepare_citation(intermediate_steps):
            self.report_output(_)

        self.report_output(None)
        return answer

    def stream(self, message, conv_id: str, history: list, **kwargs):
        if self.use_rewrite:
            rewrite = self.rewrite_pipeline(question=message)
            message = rewrite.text

        for answer in self.agent.stream(message):
            yield Document(channel="chat", content=answer.text)

        for _ in self.prepare_citation(answer.intermediate_steps):
            yield _

        yield None
        return answer

    @classmethod
    def get_pipeline(
        cls, settings: dict, states: dict, retrievers: list | None = None
    ) -> BaseReasoning:
        print(f"Settings: {settings}")
        _id = cls.get_info()["id"]

        pipeline = ReactAgentPipeline(retrievers=retrievers)
        pipeline.agent.llm = llms.get_default()
        tools = []
        for tool_name in settings[f"reasoning.options.{_id}.tools"]:
            tool = TOOL_REGISTRY[tool_name]
            if tool_name == "SearchDoc":
                tool.retrievers = retrievers
            tools.append(tool)
        pipeline.agent.plugins = tools
        pipeline.agent.output_lang = {"en": "English", "ja": "Japanese"}.get(
            settings["reasoning.lang"], "English"
        )
        pipeline.use_rewrite = states.get("app", {}).get("regen", False)

        return pipeline

    @classmethod
    def get_user_settings(cls) -> dict:
        tool_choices = ["Wikipedia", "Google", "LLM", "SearchDoc"]

        return {
            "tools": {
                "name": "Tools for knowledge retrieval",
                "value": ["SearchDoc", "LLM"],
                "component": "checkboxgroup",
                "choices": tool_choices,
            },
        }

    @classmethod
    def get_info(cls) -> dict:
        return {
            "id": "ReAct",
            "name": "ReAct Agent",
            "description": "Implementing ReAct paradigm",
        }
