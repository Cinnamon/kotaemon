import logging
import threading
from textwrap import dedent
from typing import Generator

from decouple import config
from ktem.embeddings.manager import embedding_models_manager as embeddings
from ktem.llms.manager import llms
from ktem.reasoning.prompt_optimization import (
    DecomposeQuestionPipeline,
    RewriteQuestionPipeline,
)
from ktem.utils.render import Render
from ktem.utils.visualize_cited import CreateCitationVizPipeline
from plotly.io import to_json

from kotaemon.base import (
    AIMessage,
    BaseComponent,
    Document,
    HumanMessage,
    Node,
    RetrievedDocument,
    SystemMessage,
)
from kotaemon.indices.knowledge.retrieval.context_budget import (
    GenerationBudget,
    pack_evidence,
    serialize_chat_messages,
)
from kotaemon.indices.knowledge.retrieval.expansion import EvidenceBundle
from kotaemon.indices.knowledge.retrieval.trace import trace_event, trace_scoped
from kotaemon.indices.qa.citation_qa import (
    CONTEXT_RELEVANT_WARNING_SCORE,
    DEFAULT_QA_TEXT_PROMPT,
    AnswerWithContextPipeline,
)
from kotaemon.indices.qa.citation_qa_inline import AnswerWithInlineCitation
from kotaemon.indices.qa.format_context import PrepareEvidencePipeline
from kotaemon.indices.qa.utils import replace_think_tag_with_details
from kotaemon.llms import ChatLLM

from ..local_qa_conversation import (
    DEFAULT_HISTORY_TOKEN_LIMIT,
    DEFAULT_MAX_TURNS,
    user_turns_from_history,
)
from ..utils import SUPPORTED_LANGUAGE_MAP
from .base import BaseReasoning

logger = logging.getLogger(__name__)


class AddQueryContextPipeline(BaseComponent):

    n_last_interactions: int = 5
    llm: ChatLLM = Node(default_callback=lambda _: llms.get_default())

    def run(self, question: str, history: list) -> Document:
        messages = [
            SystemMessage(
                content="Below is a history of the conversation so far, and a new "
                "question asked by the user that needs to be answered by searching "
                "in a knowledge base.\nYou have access to a Search index "
                "with 100's of documents.\nGenerate a search query based on the "
                "conversation and the new question.\nDo not include cited source "
                "filenames and document names e.g info.txt or doc.pdf in the search "
                "query terms.\nDo not include any text inside [] or <<>> in the "
                "search query terms.\nDo not include any special characters like "
                "'+'.\nIf the question is not in English, rewrite the query in "
                "the language used in the question.\n If the question contains enough "
                "information, return just the number 1\n If it's unnecessary to do "
                "the searching, return just the number 0."
            ),
            HumanMessage(content="How did crypto do last year?"),
            AIMessage(
                content="Summarize Cryptocurrency Market Dynamics from last year"
            ),
            HumanMessage(content="What are my health plans?"),
            AIMessage(content="Show available health plans"),
        ]
        for human, ai in history[-self.n_last_interactions :]:
            messages.append(HumanMessage(content=human))
            messages.append(AIMessage(content=ai))

        messages.append(HumanMessage(content=f"Generate search query for: {question}"))

        resp = self.llm(messages).text
        if resp == "0":
            return Document(content="")

        if resp == "1":
            return Document(content=question)

        return Document(content=resp)


class FullQAPipeline(BaseReasoning):
    """Question answering pipeline. Handle from question to answer"""

    class Config:
        allow_extra = True

    # configuration parameters
    trigger_context: int = 150
    use_rewrite: bool = False

    retrievers: list[BaseComponent]

    evidence_pipeline: PrepareEvidencePipeline = PrepareEvidencePipeline.withx()
    answering_pipeline: AnswerWithContextPipeline
    output_reserve: int = 2048
    format_reserve: int = 256
    rewrite_pipeline: RewriteQuestionPipeline | None = None
    create_citation_viz_pipeline: CreateCitationVizPipeline = Node(
        default_callback=lambda _: CreateCitationVizPipeline(
            embedding=embeddings.get_default()
        )
    )
    add_query_context: AddQueryContextPipeline = AddQueryContextPipeline.withx()

    def retrieve(
        self,
        message: str,
        history: list,
        trace=None,
        trace_context: dict | None = None,
    ) -> tuple[list[RetrievedDocument], list[Document]]:
        """Retrieve the documents based on the message"""
        # if len(message) < self.trigger_context:
        #     # prefer adding context for short user questions, avoid adding context for
        #     # long questions, as they are likely to contain enough information
        #     # plus, avoid the situation where the original message is already too long
        #     # for the model to handle
        #     query = self.add_query_context(message, history).content
        # else:
        #     query = message
        # print(f"Rewritten query: {query}")
        query = None
        if not query:
            # TODO: previously return [], [] because we think this message as something
            # like "Hello", "I need help"...
            query = message

        query_context = dict(trace_context or {})
        trace_event(
            trace,
            "qa_query",
            original_query=message,
            **query_context,
        )

        docs, doc_ids = [], []
        plot_docs = []

        for idx, retriever in enumerate(self.retrievers):
            retriever_node = self._prepare_child(retriever, f"retriever_{idx}")
            retriever_name = type(retriever).__name__
            retriever_trace = trace_scoped(
                trace,
                retriever_index=idx,
                retriever_name=retriever_name,
                **query_context,
            )
            retriever_kwargs = {"text": query}
            if getattr(retriever, "v3_enabled", False) and getattr(
                retriever, "query_enrichment", False
            ):
                counter_factory = getattr(self.evidence_pipeline, "_counter", None)
                count_tokens = (
                    counter_factory()
                    if callable(counter_factory)
                    else lambda text: len(text.encode("utf-8"))
                )
                retriever_kwargs["user_history"] = user_turns_from_history(
                    history,
                    max_turns=DEFAULT_MAX_TURNS,
                    token_limit=DEFAULT_HISTORY_TOKEN_LIMIT,
                    count_tokens=count_tokens,
                )
            if trace is not None:
                retriever_kwargs["trace"] = retriever_trace
            retriever_docs = retriever_node(**retriever_kwargs)
            trace_event(
                trace,
                "qa_retriever",
                retriever_index=idx,
                retriever_name=retriever_name,
                ids=[doc.doc_id for doc in retriever_docs],
                **query_context,
            )

            retriever_docs_text = []
            retriever_docs_plot = []

            for doc in retriever_docs:
                if doc.metadata.get("type", "") == "plot":
                    retriever_docs_plot.append(doc)
                else:
                    retriever_docs_text.append(doc)

            for doc in retriever_docs_text:
                if doc.doc_id not in doc_ids:
                    docs.append(doc)
                    doc_ids.append(doc.doc_id)

            plot_docs.extend(retriever_docs_plot)

        info = [
            Document(
                channel="info",
                content=Render.collapsible_with_header(doc, open_collapsible=True),
            )
            for doc in docs
        ] + [
            Document(
                channel="plot",
                content=doc.metadata.get("data", ""),
            )
            for doc in plot_docs
        ]

        return docs, info

    def _pack_authorized_v3_evidence(self, docs, trace, *, question, history):
        """Pack expansion-enabled product evidence before answer generation."""
        seeds = tuple(
            document
            for document in docs
            if (document.metadata or {}).get("knowledge_evidence_role") != "expansion"
        )
        expansions = tuple(
            document
            for document in docs
            if (document.metadata or {}).get("knowledge_evidence_role") == "expansion"
        )
        budget = GenerationBudget(
            model_context=self.evidence_pipeline._budget(),
            output_reserve=self.output_reserve,
            format_reserve=self.format_reserve,
        )

        def render_request(documents):
            evidence_mode, evidence, images = self.evidence_pipeline(
                list(documents)
            ).content
            messages, _prompt, _evidence = (
                self.answering_pipeline.prepare_generation_messages(
                    question,
                    evidence,
                    evidence_mode,
                    images=images,
                    history=history,
                )
            )
            return serialize_chat_messages(
                [message.to_openai_format() for message in messages]
            )

        packed = pack_evidence(
            EvidenceBundle(seeds=seeds, expansions=expansions, decisions=()),
            budget=budget,
            count_tokens=self.evidence_pipeline._counter(),
            base_prompt="",
            render_context=render_request,
            render_budgeted_request=lambda serialized_messages: serialized_messages,
        )
        trace_event(
            trace,
            "product_context_packing",
            status=packed.status,
            chunk_ids=[document.doc_id for document in packed.documents],
            token_budget=packed.available_tokens,
            tokens_used=packed.token_count,
            omitted_ids=list(packed.omitted_ids),
        )
        return list(packed.documents), packed

    def prepare_mindmap(self, answer) -> Document | None:
        mindmap = answer.metadata["mindmap"]
        if mindmap:
            mindmap_text = mindmap.text
            mindmap_svg = dedent(
                """
                <div class="markmap">
                <script type="text/template">
                ---
                markmap:
                    colorFreezeLevel: 2
                    activeNode:
                        placement: center
                    initialExpandLevel: 4
                    maxWidth: 200
                ---
                {}
                </script>
                </div>
                """
            ).format(mindmap_text)

            mindmap_content = Document(
                channel="info",
                content=Render.collapsible(
                    header="""
                    <i>Mindmap</i>
                    <a href="#" id='mindmap-toggle'>
                        [Expand]</a>
                    <a href="#" id='mindmap-export'>
                        [Export]</a>""",
                    content=mindmap_svg,
                    open=True,
                ),
            )
        else:
            mindmap_content = None

        return mindmap_content

    def prepare_citation_viz(self, answer, question, docs) -> Document | None:
        doc_texts = [doc.text for doc in docs]
        citation_plot = None
        plot_content = None

        if answer.metadata["citation_viz"] and len(docs) > 1:
            try:
                citation_plot = self.create_citation_viz_pipeline(doc_texts, question)
            except Exception as e:
                print("Failed to create citation plot:", e)

            if citation_plot:
                plot = to_json(citation_plot)
                plot_content = Document(channel="plot", content=plot)

        return plot_content

    def show_citations_and_addons(self, answer, docs, question):
        # show the evidence
        with_citation, without_citation = self.answering_pipeline.prepare_citations(
            answer, docs
        )
        mindmap_output = self.prepare_mindmap(answer)
        citation_plot_output = self.prepare_citation_viz(answer, question, docs)

        if not with_citation and not without_citation:
            yield Document(channel="info", content="<h5><b>No evidence found.</b></h5>")
        else:
            # clear the Info panel
            max_llm_rerank_score = max(
                doc.metadata.get("llm_trulens_score", 0.0) for doc in docs
            )
            has_llm_score = any("llm_trulens_score" in doc.metadata for doc in docs)
            # clear previous info
            yield Document(channel="info", content=None)

            # yield mindmap output
            if mindmap_output:
                yield mindmap_output

            # yield citation plot output
            if citation_plot_output:
                yield citation_plot_output

            # yield warning message
            if has_llm_score and max_llm_rerank_score < CONTEXT_RELEVANT_WARNING_SCORE:
                yield Document(
                    channel="info",
                    content=(
                        "<h5>WARNING! Context relevance score is low. "
                        "Double check the model answer for correctness.</h5>"
                    ),
                )

            # show QA score
            qa_score = (
                round(answer.metadata["qa_score"], 2)
                if answer.metadata.get("qa_score")
                else None
            )
            if qa_score:
                yield Document(
                    channel="info",
                    content=f"<h5>Answer confidence: {qa_score}</h5>",
                )

            yield from with_citation
            if without_citation:
                yield from without_citation

    async def ainvoke(  # type: ignore
        self, message: str, conv_id: str, history: list, **kwargs  # type: ignore
    ) -> Document:  # type: ignore
        raise NotImplementedError

    def stream(  # type: ignore
        self, message: str, conv_id: str, history: list, **kwargs  # type: ignore
    ) -> Generator[Document, None, Document]:
        if self.use_rewrite and self.rewrite_pipeline:
            print("Chosen rewrite pipeline", self.rewrite_pipeline)
            message = self.rewrite_pipeline(question=message).text
            print("Rewrite result", message)

        print(f"Retrievers {self.retrievers}")
        # should populate the context
        trace = kwargs.get("trace")
        docs, infos = self.retrieve(
            message,
            history,
            trace=trace,
            trace_context={"query_kind": "main"},
        )
        expansion_enabled = any(
            getattr(retriever, "v3_enabled", False)
            and getattr(retriever, "evidence_expansion", False)
            for retriever in self.retrievers
        )
        packed_status = None
        if expansion_enabled:
            docs, packed_context = self._pack_authorized_v3_evidence(
                docs, trace, question=message, history=history
            )
            packed_status = packed_context.status
            infos = [
                Document(
                    channel="info",
                    content=Render.collapsible_with_header(doc, open_collapsible=True),
                )
                for doc in docs
                if (doc.metadata or {}).get("type", "") != "plot"
            ]
        print(f"Got {len(docs)} retrieved documents")
        yield from infos

        if packed_status == "insufficient_evidence":
            message = "Insufficient evidence fits within the configured context budget."
            trace_event(
                trace,
                "generation_skipped",
                reason="insufficient_evidence",
            )
            answer = Document(channel="chat", content=message)
            yield answer
            return answer

        evidence_trace = trace_scoped(trace, query_kind="main")
        evidence_kwargs = {"trace": evidence_trace} if trace is not None else {}
        if expansion_enabled:
            context_trace = {}
            evidence_mode, evidence, images = self.evidence_pipeline(
                docs, trace=context_trace
            ).content
            context_ids = context_trace.get("context_chunk_ids", [])
            included_ids = set(context_ids)
            docs = [document for document in docs if document.doc_id in included_ids]
            trace_event(
                trace,
                "context",
                chunk_ids=context_ids,
                token_budget=context_trace.get("context_token_budget"),
                tokens_used=context_trace.get("context_tokens"),
            )
        else:
            evidence_mode, evidence, images = self.evidence_pipeline(
                docs, **evidence_kwargs
            ).content

        def generate_relevant_scores():
            nonlocal docs
            docs = self.retrievers[0].generate_relevant_scores(message, docs)

        # generate relevant score using
        if evidence and self.retrievers:
            scoring_thread = threading.Thread(target=generate_relevant_scores)
            scoring_thread.start()
        else:
            scoring_thread = None

        answer = yield from self.answering_pipeline.stream(
            question=message,
            history=history,
            evidence=evidence,
            evidence_mode=evidence_mode,
            images=images,
            conv_id=conv_id,
            **kwargs,
        )

        # check <think> tag from reasoning models
        processed_answer = replace_think_tag_with_details(answer.text)
        if processed_answer != answer.text:
            # clear the chat message and render again
            yield Document(channel="chat", content=None)
            yield Document(channel="chat", content=processed_answer)

        # show the evidence
        if scoring_thread:
            scoring_thread.join()

        yield from self.show_citations_and_addons(answer, docs, message)

        return answer

    @classmethod
    def prepare_pipeline_instance(cls, settings, retrievers):
        return cls(
            retrievers=retrievers,
            rewrite_pipeline=None,
        )

    @classmethod
    def get_pipeline(cls, settings, states, retrievers):
        """Get the reasoning pipeline

        Args:
            settings: the settings for the pipeline
            retrievers: the retrievers to use
        """
        max_context_length_setting = settings.get("reasoning.max_context_length", 32000)

        pipeline = cls.prepare_pipeline_instance(settings, retrievers)

        prefix = f"reasoning.options.{cls.get_info()['id']}"
        llm_name = settings.get(f"{prefix}.llm", None)
        llm = llms.get(llm_name, llms.get_default())

        # prepare evidence pipeline configuration
        evidence_pipeline = pipeline.evidence_pipeline
        evidence_pipeline.max_context_length = max_context_length_setting

        # answering pipeline configuration
        use_inline_citation = settings[f"{prefix}.highlight_citation"] == "inline"

        if use_inline_citation:
            answer_pipeline = pipeline.answering_pipeline = AnswerWithInlineCitation()
        else:
            answer_pipeline = pipeline.answering_pipeline = AnswerWithContextPipeline()

        answer_pipeline.llm = llm
        answer_pipeline.citation_pipeline.llm = llm
        answer_pipeline.n_last_interactions = settings[f"{prefix}.n_last_interactions"]
        answer_pipeline.enable_citation = (
            settings[f"{prefix}.highlight_citation"] != "off"
        )
        answer_pipeline.enable_mindmap = settings[f"{prefix}.create_mindmap"]
        answer_pipeline.enable_citation_viz = settings[f"{prefix}.create_citation_viz"]
        answer_pipeline.use_multimodal = settings[f"{prefix}.use_multimodal"]
        answer_pipeline.system_prompt = settings[f"{prefix}.system_prompt"]
        answer_pipeline.qa_template = settings[f"{prefix}.qa_prompt"]
        answer_pipeline.lang = SUPPORTED_LANGUAGE_MAP.get(
            settings["reasoning.lang"], "English"
        )

        pipeline.add_query_context.llm = llm
        pipeline.add_query_context.n_last_interactions = settings[
            f"{prefix}.n_last_interactions"
        ]

        pipeline.trigger_context = settings[f"{prefix}.trigger_context"]
        pipeline.use_rewrite = states.get("app", {}).get("regen", False)
        if pipeline.rewrite_pipeline:
            pipeline.rewrite_pipeline.llm = llm
            pipeline.rewrite_pipeline.lang = SUPPORTED_LANGUAGE_MAP.get(
                settings["reasoning.lang"], "English"
            )
        return pipeline

    @classmethod
    def get_user_settings(cls) -> dict:
        from ktem.llms.manager import llms

        llm = ""
        choices = [("(default)", "")]
        try:
            choices += [(_, _) for _ in llms.options().keys()]
        except Exception as e:
            logger.exception(f"Failed to get LLM options: {e}")

        return {
            "llm": {
                "name": "Language model",
                "value": llm,
                "component": "dropdown",
                "choices": choices,
                "special_type": "llm",
                "info": (
                    "The language model to use for generating the answer. If None, "
                    "the application default language model will be used."
                ),
            },
            "highlight_citation": {
                "name": "Citation style",
                "value": (
                    "highlight"
                    if not config("USE_LOW_LLM_REQUESTS", default=False, cast=bool)
                    else "off"
                ),
                "component": "radio",
                "choices": [
                    ("citation: highlight", "highlight"),
                    ("citation: inline", "inline"),
                    ("no citation", "off"),
                ],
            },
            "create_mindmap": {
                "name": "Create Mindmap",
                "value": False,
                "component": "checkbox",
            },
            "create_citation_viz": {
                "name": "Create Embeddings Visualization",
                "value": False,
                "component": "checkbox",
            },
            "use_multimodal": {
                "name": "Use Multimodal Input",
                "value": False,
                "component": "checkbox",
            },
            "system_prompt": {
                "name": "System Prompt",
                "value": ("This is a question answering system."),
            },
            "qa_prompt": {
                "name": "QA Prompt (contains {context}, {question}, {lang})",
                "value": DEFAULT_QA_TEXT_PROMPT,
            },
            "n_last_interactions": {
                "name": "Number of interactions to include",
                "value": 5,
                "component": "number",
                "info": "The maximum number of chat interactions to include in the LLM",
            },
            "trigger_context": {
                "name": "Maximum message length for context rewriting",
                "value": 150,
                "component": "number",
                "info": (
                    "The maximum length of the message to trigger context addition. "
                    "Exceeding this length, the message will be used as is."
                ),
            },
        }

    @classmethod
    def get_info(cls) -> dict:
        return {
            "id": "simple",
            "name": "Simple QA",
            "description": (
                "Simple RAG-based question answering pipeline. This pipeline can "
                "perform both keyword search and similarity search to retrieve the "
                "context. After that it includes that context to generate the answer."
            ),
        }


class FullDecomposeQAPipeline(FullQAPipeline):
    def answer_sub_questions(
        self, messages: list, conv_id: str, history: list, **kwargs
    ):
        output_str = ""
        for idx, message in enumerate(messages):
            yield Document(
                channel="chat",
                content=f"<br><b>Sub-question {idx + 1}</b>"
                f"<br>{message}<br><b>Answer</b><br>",
            )
            # should populate the context
            trace = kwargs.get("trace")
            docs, infos = self.retrieve(
                message,
                history,
                trace=trace,
                trace_context={"query_kind": "subquestion", "subquestion_index": idx},
            )
            print(f"Got {len(docs)} retrieved documents")

            yield from infos

            evidence_trace = trace_scoped(
                trace, query_kind="subquestion", subquestion_index=idx
            )
            evidence_kwargs = {"trace": evidence_trace} if trace is not None else {}
            evidence_mode, evidence, images = self.evidence_pipeline(
                docs, **evidence_kwargs
            ).content
            answer = yield from self.answering_pipeline.stream(
                question=message,
                history=history,
                evidence=evidence,
                evidence_mode=evidence_mode,
                images=images,
                conv_id=conv_id,
                **kwargs,
            )

            output_str += (
                f"Sub-question {idx + 1}-th: '{message}'\nAnswer: '{answer.text}'\n\n"
            )

        return output_str

    def stream(  # type: ignore
        self, message: str, conv_id: str, history: list, **kwargs  # type: ignore
    ) -> Generator[Document, None, Document]:
        sub_question_answer_output = ""
        if self.rewrite_pipeline:
            print("Chosen rewrite pipeline", self.rewrite_pipeline)
            result = self.rewrite_pipeline(question=message)
            print("Rewrite result", result)
            if isinstance(result, Document):
                message = result.text
            elif (
                isinstance(result, list)
                and len(result) > 0
                and isinstance(result[0], Document)
            ):
                yield Document(
                    channel="chat",
                    content="<h4>Sub questions and their answers</h4>",
                )
                sub_question_answer_output = yield from self.answer_sub_questions(
                    [r.text for r in result], conv_id, history, **kwargs
                )

        yield Document(
            channel="chat",
            content=f"<h4>Main question</h4>{message}<br><b>Answer</b><br>",
        )

        # should populate the context
        trace = kwargs.get("trace")
        docs, infos = self.retrieve(
            message,
            history,
            trace=trace,
            trace_context={"query_kind": "main"},
        )
        print(f"Got {len(docs)} retrieved documents")
        yield from infos

        evidence_trace = trace_scoped(trace, query_kind="main")
        evidence_kwargs = {"trace": evidence_trace} if trace is not None else {}
        evidence_mode, evidence, images = self.evidence_pipeline(
            docs, **evidence_kwargs
        ).content
        answer = yield from self.answering_pipeline.stream(
            question=message,
            history=history,
            evidence=evidence + "\n" + sub_question_answer_output,
            evidence_mode=evidence_mode,
            images=images,
            conv_id=conv_id,
            **kwargs,
        )

        # show the evidence
        with_citation, without_citation = self.answering_pipeline.prepare_citations(
            answer, docs
        )
        if not with_citation and not without_citation:
            yield Document(channel="info", content="<h5><b>No evidence found.</b></h5>")
        else:
            yield Document(channel="info", content=None)
            yield from with_citation
            yield from without_citation

        return answer

    @classmethod
    def get_user_settings(cls) -> dict:
        user_settings = super().get_user_settings()
        user_settings["decompose_prompt"] = {
            "name": "Decompose Prompt",
            "value": DecomposeQuestionPipeline.DECOMPOSE_SYSTEM_PROMPT_TEMPLATE,
        }
        return user_settings

    @classmethod
    def prepare_pipeline_instance(cls, settings, retrievers):
        prefix = f"reasoning.options.{cls.get_info()['id']}"
        pipeline = cls(
            retrievers=retrievers,
            rewrite_pipeline=DecomposeQuestionPipeline(
                prompt_template=settings.get(f"{prefix}.decompose_prompt")
            ),
        )
        return pipeline

    @classmethod
    def get_info(cls) -> dict:
        return {
            "id": "complex",
            "name": "Complex QA",
            "description": (
                "Use multi-step reasoning to decompose a complex question into "
                "multiple sub-questions. This pipeline can "
                "perform both keyword search and similarity search to retrieve the "
                "context. After that it includes that context to generate the answer."
            ),
        }
