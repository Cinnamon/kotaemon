import html
import logging
from difflib import SequenceMatcher
from typing import AnyStr, Generator, Optional, Type

from ktem.llms.manager import llms
from ktem.reasoning.base import BaseReasoning
from ktem.utils.generator import Generator as GeneratorWrapper
from ktem.utils.render import Render
from langchain.text_splitter import CharacterTextSplitter
from pydantic import BaseModel, Field

from kotaemon.agents import (
    BaseTool,
    GoogleSearchTool,
    LLMTool,
    RewooAgent,
    WikipediaTool,
)
from kotaemon.base import BaseComponent, Document, HumanMessage, Node, SystemMessage
from kotaemon.llms import ChatLLM, PromptTemplate

from ..utils import SUPPORTED_LANGUAGE_MAP

logger = logging.getLogger(__name__)
DEFAULT_AGENT_STEPS = 4


DEFAULT_PLANNER_PROMPT = (
    "You are an AI agent who makes step-by-step plans to solve a problem under the "
    "help of external tools. For each step, make one plan followed by one tool-call, "
    "which will be executed later to retrieve evidence for that step.\n"
    "You should store each evidence into a distinct variable #E1, #E2, #E3 ... that "
    "can be referred to in later tool-call inputs.\n\n"
    "##Available Tools##\n"
    "{tool_description}\n\n"
    "##Output Format (Replace '<...>')##\n"
    "#Plan1: <describe your plan here>\n"
    "#E1: <toolname>[<input here>] (eg. Search[What is Python])\n"
    "#Plan2: <describe next plan>\n"
    "#E2: <toolname>[<input here, you can use #E1 to represent its expected output>]\n"
    "And so on...\n\n"
    "##Your Task##\n"
    "{task}\n\n"
    "##Now Begin##\n"
)

DEFAULT_SOLVER_PROMPT = (
    "You are an AI agent who solves a problem with my assistance. I will provide "
    "step-by-step plans(#Plan) and evidences(#E) that could be helpful.\n"
    "Your task is to briefly summarize each step, then make a short final conclusion "
    "for your task. Give answer in {lang}.\n\n"
    "##My Plans and Evidences##\n"
    "{plan_evidence}\n\n"
    "##Example Output##\n"
    "First, I <did something> , and I think <...>; Second, I <...>, "
    "and I think <...>; ....\n"
    "So, <your conclusion>.\n\n"
    "##Your Task##\n"
    "{task}\n\n"
    "##Now Begin##\n"
)


class DocSearchArgs(BaseModel):
    query: str = Field(..., description="a search query as input to the doc search")


class DocSearchTool(BaseTool):
    name: str = "docsearch"
    description: str = (
        "A storage that contains internal documents. If you lack any specific "
        "private information to answer the question, you can search in this "
        "document storage. Furthermore, if you are unsure about which document that "
        "the user refers to, likely the user already selects the target document in "
        "this document storage, you just need to do normal search. If possible, "
        "formulate the search query as specific as possible."
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

    def prepare_evidence(self, docs, trim_len: int = 3000):
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
                # PWS doesn't support VLM for images, we will just store the caption
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

            print("Retrieved #{}: {}".format(_id, retrieved_content))
            print("Score", retrieved_item.metadata.get("cohere_reranking_score", None))

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


def find_text(llm_output, context):
    sentence_list = llm_output.split("\n")
    matches = []
    for sentence in sentence_list:
        match = SequenceMatcher(
            None, sentence, context, autojunk=False
        ).find_longest_match()
        matches.append((match.b, match.b + match.size))
    return matches


class RewooAgentPipeline(BaseReasoning):
    """Question answering pipeline using ReWOO Agent."""

    class Config:
        allow_extra = True

    retrievers: list[BaseComponent]
    agent: RewooAgent = RewooAgent.withx()
    rewrite_pipeline: RewriteQuestionPipeline = RewriteQuestionPipeline.withx()
    use_rewrite: bool = False
    enable_citation: bool = False

    def format_info_panel_evidence(self, worker_log):
        header = ""
        content = []

        for line in worker_log.splitlines():
            if line.startswith("#Plan"):
                # line starts with #Plan should be marked as a new segment
                header = line
            elif line.startswith("#Action"):
                # small fix for markdown output
                line = "\\" + line + "<br>"
                content.append(line)
            elif line.startswith("#"):
                # stop markdown from rendering big headers
                line = "\\" + line
                content.append(line)
            else:
                content.append(line)

        if not header:
            return

        return Document(
            channel="info",
            content=Render.collapsible(
                header=header,
                content=Render.table("\n".join(content)),
                open=False,
            ),
        )

    def format_info_panel_planner(self, planner_output):
        planner_output = planner_output.replace("\n", "<br>")
        return Document(
            channel="info",
            content=Render.collapsible(
                header="Planner Output",
                content=planner_output,
                open=True,
            ),
        )

    def prepare_citation(self, answer) -> list[Document]:
        """Prepare citation to show on the UI"""
        segments = []
        split_indices = [
            0,
        ]
        start_indices = set()
        text = ""

        if "citation" in answer.metadata and answer.metadata["citation"] is not None:
            context = answer.metadata["worker_log"]
            for fact_with_evidence in answer.metadata["citation"].answer:
                for quote in fact_with_evidence.substring_quote:
                    matches = find_text(quote, context)
                    for match in matches:
                        split_indices.append(match[0])
                        split_indices.append(match[1])
                        start_indices.add(match[0])
            split_indices = sorted(list(set(split_indices)))
            spans = []
            prev = 0
            for index in split_indices:
                if index > prev:
                    spans.append(context[prev:index])
                    prev = index
            spans.append(context[split_indices[-1] :])

            prev = 0
            for span, start_idx in list(zip(spans, split_indices)):
                if start_idx in start_indices:
                    text += Render.highlight(span)
                else:
                    text += span

        else:
            text = answer.metadata["worker_log"]

        # separate text by detect header: #Plan
        for line in text.splitlines():
            if line.startswith("#Plan"):
                # line starts with #Plan should be marked as a new segment
                new_segment = [line]
                segments.append(new_segment)
            elif line.startswith("#Action"):
                # small fix for markdown output
                line = "\\" + line + "<br>"
                segments[-1].append(line)
            elif line.startswith("#"):
                # stop markdown from rendering big headers
                line = "\\" + line
                segments[-1].append(line)
            else:
                if segments:
                    segments[-1].append(line)
                else:
                    segments.append([line])

        outputs = []
        for segment in segments:
            outputs.append(
                Document(
                    channel="info",
                    content=Render.collapsible(
                        header=segment[0],
                        content=Render.table("\n".join(segment[1:])),
                        open=True,
                    ),
                )
            )

        return outputs

    async def ainvoke(  # type: ignore
        self, message, conv_id: str, history: list, **kwargs  # type: ignore
    ) -> Document:
        answer = self.agent(message, use_citation=True)
        self.report_output(Document(content=answer.text, channel="chat"))

        refined_citations = self.prepare_citation(answer)
        for _ in refined_citations:
            self.report_output(_)

        self.report_output(None)
        return answer

    def stream(  # type: ignore
        self, message, conv_id: str, history: list, **kwargs  # type: ignore
    ) -> Generator[Document, None, Document] | None:
        if self.use_rewrite:
            rewrite = self.rewrite_pipeline(question=message)
            message = rewrite.text
            yield Document(
                channel="info",
                content=f"Rewrote the message to: {rewrite.text}",
            )

        output_stream = GeneratorWrapper(
            self.agent.stream(message, use_citation=self.enable_citation)
        )
        for item in output_stream:
            if item.intermediate_steps:
                for step in item.intermediate_steps:
                    if "planner_log" in step:
                        yield Document(
                            channel="info",
                            content=self.format_info_panel_planner(step["planner_log"]),
                        )
                    else:
                        yield Document(
                            channel="info",
                            content=self.format_info_panel_evidence(step["worker_log"]),
                        )
            if item.text:
                # final answer
                yield Document(channel="chat", content=item.text)

        answer = output_stream.value
        yield Document(channel="info", content=None)
        yield from self.prepare_citation(answer)

        return answer

    @classmethod
    def get_pipeline(
        cls, settings: dict, states: dict, retrievers: list | None = None
    ) -> BaseReasoning:
        _id = cls.get_info()["id"]
        prefix = f"reasoning.options.{_id}"
        pipeline = RewooAgentPipeline(retrievers=retrievers)

        max_context_length_setting = settings.get("reasoning.max_context_length", None)

        planner_llm_name = settings[f"{prefix}.planner_llm"]
        planner_llm = llms.get(planner_llm_name, llms.get_default())
        solver_llm_name = settings[f"{prefix}.solver_llm"]
        solver_llm = llms.get(solver_llm_name, llms.get_default())

        pipeline.agent.planner_llm = planner_llm
        pipeline.agent.solver_llm = solver_llm
        if max_context_length_setting:
            pipeline.agent.max_context_length = (
                max_context_length_setting // DEFAULT_AGENT_STEPS
            )

        tools = []
        for tool_name in settings[f"{prefix}.tools"]:
            tool = TOOL_REGISTRY[tool_name]
            if tool_name == "SearchDoc":
                tool.retrievers = retrievers
            elif tool_name == "LLM":
                tool.llm = solver_llm
            tools.append(tool)
        pipeline.agent.plugins = tools
        pipeline.agent.output_lang = SUPPORTED_LANGUAGE_MAP.get(
            settings["reasoning.lang"], "English"
        )
        pipeline.agent.prompt_template["Planner"] = PromptTemplate(
            settings[f"{prefix}.planner_prompt"]
        )
        pipeline.agent.prompt_template["Solver"] = PromptTemplate(
            settings[f"{prefix}.solver_prompt"]
        )

        pipeline.enable_citation = settings[f"{prefix}.highlight_citation"]
        pipeline.use_rewrite = states.get("app", {}).get("regen", False)
        pipeline.rewrite_pipeline.llm = (
            planner_llm  # TODO: separate llm for rewrite if needed
        )

        return pipeline

    @classmethod
    def get_user_settings(cls) -> dict:

        llm = ""
        llm_choices = [("(default)", "")]
        try:
            llm_choices += [(_, _) for _ in llms.options().keys()]
        except Exception as e:
            logger.exception(f"Failed to get LLM options: {e}")

        tool_choices = ["Wikipedia", "Google", "LLM", "SearchDoc"]

        return {
            "planner_llm": {
                "name": "Language model for Planner",
                "value": llm,
                "component": "dropdown",
                "choices": llm_choices,
                "special_type": "llm",
                "info": (
                    "The language model to use for planning. "
                    "This model will generate a plan based on the "
                    "instruction to find the answer."
                ),
            },
            "solver_llm": {
                "name": "Language model for Solver",
                "value": llm,
                "component": "dropdown",
                "choices": llm_choices,
                "special_type": "llm",
                "info": (
                    "The language model to use for solving. "
                    "This model will generate the answer based on the "
                    "plan generated by the planner and evidences found by the tools."
                ),
            },
            "highlight_citation": {
                "name": "Highlight Citation",
                "value": False,
                "component": "checkbox",
            },
            "tools": {
                "name": "Tools for knowledge retrieval",
                "value": ["SearchDoc", "LLM"],
                "component": "checkboxgroup",
                "choices": tool_choices,
            },
            "planner_prompt": {
                "name": "Planner Prompt",
                "value": DEFAULT_PLANNER_PROMPT,
            },
            "solver_prompt": {
                "name": "Solver Prompt",
                "value": DEFAULT_SOLVER_PROMPT,
            },
        }

    @classmethod
    def get_info(cls) -> dict:
        return {
            "id": "ReWOO",
            "name": "ReWOO Agent",
            "description": (
                "Implementing ReWOO paradigm: https://arxiv.org/abs/2305.18323. "
                "The ReWOO agent makes a step by step plan in the first stage, "
                "then solves each step in the second stage. The agent can use "
                "external tools to help in the reasoning process. Once all stages "
                "are completed, the agent will summarize the answer."
            ),
        }
