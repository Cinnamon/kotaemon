"""Trace handoff tests across the file service, evidence, and simple QA paths."""

from __future__ import annotations

import json
from types import SimpleNamespace

from ktem.index.file.pipelines import DocumentRetrievalPipeline
from ktem.reasoning.simple import FullDecomposeQAPipeline, FullQAPipeline

from kotaemon.base import (
    BaseComponent,
    Document,
    DocumentWithEmbedding,
    RetrievedDocument,
)
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices import VectorRetrieval
from kotaemon.indices.knowledge.planning.query_planner import KnowledgeSource
from kotaemon.indices.knowledge.planning.retrieval_plan import RetrievalPlan
from kotaemon.indices.knowledge.retrieval.knowledge_service import KnowledgeService
from kotaemon.indices.knowledge.retrieval.trace import RetrievalTrace
from kotaemon.indices.qa.citation_qa import AnswerWithContextPipeline
from kotaemon.indices.qa.citation_qa_inline import AnswerWithInlineCitation
from kotaemon.indices.qa.format_context import PrepareEvidencePipeline
from kotaemon.indices.rankings import BaseReranking
from kotaemon.storages.docstores.base import BaseDocumentStore
from kotaemon.storages.vectorstores.base import BaseVectorStore


class FakeCatalog:
    def __init__(self):
        self.sources = [
            KnowledgeSource(
                source_id="source-a",
                source_type="markdown",
                virtual_path="/team/guide.md",
                document_name="guide.md",
                entity={"team": "rag"},
            )
        ]

    def list_sources(self, allowed_source_ids=None):
        if allowed_source_ids is None:
            return list(self.sources)
        allowed = set(allowed_source_ids)
        return [source for source in self.sources if source.source_id in allowed]

    def chunk_ids(self, source_ids, relation_type="document"):
        return {"source-a": ["chunk-a"]}

    def source_ids_for_chunk_ids(self, chunk_ids, allowed_source_ids=None):
        return {"chunk-a": ["source-a"]}


class FakePlanner:
    def plan(
        self, query, catalog, source_types=None, filters=None, allowed_source_ids=None
    ):
        return RetrievalPlan(
            query=query,
            semantic_query="semantic query",
            source_types=("markdown",),
            virtual_paths=("/team/guide.md",),
            metadata_filters={"team": "rag"},
            confidence=0.95,
            reason="exact entity",
            source_ids=("source-a",),
        )


class FakeRetriever:
    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return [RetrievedDocument(id_="chunk-a", text="A source passage", metadata={})]


def test_service_trace_records_original_query_plan_filters_and_authorized_scopes():
    from kotaemon.indices.knowledge.retrieval.knowledge_service import KnowledgeService

    retriever = FakeRetriever()
    service = KnowledgeService(
        planner=FakePlanner(), catalog=FakeCatalog(), retriever=retriever, docstore=None
    )
    trace = RetrievalTrace()

    result = service.search(
        "where did Zhang intern?",
        path="/team",
        source_types=["markdown"],
        filters={"team": "rag"},
        allowed_source_ids=["source-a"],
        trace=trace,
    )
    snapshot = trace.to_dict()

    assert [doc.doc_id for doc in result] == ["chunk-a"]
    assert snapshot["original_query"] == "where did Zhang intern?"
    assert snapshot["plan"]["semantic_query"] == "semantic query"
    assert snapshot["explicit_filters"] == {
        "path": "/team",
        "source_types": ["markdown"],
        "metadata_filters": {"team": "rag"},
    }
    assert snapshot["source_scope"]["visible_ids"] == ["source-a"]
    assert snapshot["source_scope"]["planned_ids"] == ["source-a"]
    assert snapshot["chunk_scope"]["visible_ids"] == ["chunk-a"]
    assert retriever.calls[0]["text"] == "semantic query"
    assert retriever.calls[0]["trace"] is not None


def test_empty_visibility_is_traced_without_calling_retriever():
    from kotaemon.indices.knowledge.retrieval.knowledge_service import KnowledgeService

    retriever = FakeRetriever()
    service = KnowledgeService(
        planner=FakePlanner(), catalog=FakeCatalog(), retriever=retriever, docstore=None
    )
    trace = RetrievalTrace()

    assert service.search("question", allowed_source_ids=[], trace=trace) == []
    assert retriever.calls == []
    assert trace.to_dict()["source_scope"]["visible_ids"] == []
    assert any(event["stage"] == "no_search" for event in trace.to_dict()["events"])


def test_context_trace_has_complete_ids_and_actual_token_use():
    doc = RetrievedDocument(
        id_="evidence-chunk",
        text="A complete cited passage.",
        metadata={"file_name": "guide.md"},
    )
    trace = RetrievalTrace()
    pipeline = PrepareEvidencePipeline(max_context_length=200, token_counter=len)

    result = pipeline.run([doc], trace=trace)

    snapshot = trace.to_dict()
    assert result.content[1].endswith("A complete cited passage. \n<br>")
    assert snapshot["context"]["chunk_ids"] == ["evidence-chunk"]
    assert snapshot["context"]["tokens_used"] == len(result.content[1])
    assert snapshot["context"]["token_budget"] == 200


def test_simple_qa_trace_is_only_injected_when_supplied_and_labels_retrievers():
    class LegacyRetriever:
        def __init__(self):
            self.calls = []

        def __call__(self, **kwargs):
            self.calls.append(kwargs)
            return [
                RetrievedDocument(id_="legacy", text="citation source", metadata={})
            ]

    retriever = LegacyRetriever()
    pipeline = FullQAPipeline(
        retrievers=[retriever],
        evidence_pipeline=PrepareEvidencePipeline(
            max_context_length=200, token_counter=len
        ),
    )
    pipeline._prepare_child = lambda child, name: child
    docs_without_trace, _ = pipeline.retrieve("question", [])
    trace = RetrievalTrace()
    docs_with_trace, _ = pipeline.retrieve("question", [], trace=trace)

    assert retriever.calls[0] == {"text": "question"}
    assert retriever.calls[1]["trace"] is not None
    assert docs_without_trace == docs_with_trace
    assert any(event["stage"] == "qa_retriever" for event in trace.to_dict()["events"])


class FakeAnsweringPipeline(BaseComponent):
    def run(self, **kwargs):
        return Document(
            text="answer",
            metadata={"mindmap": None, "citation_viz": None, "qa_score": None},
        )

    def stream(self, **kwargs):
        yield Document(channel="chat", content="answer")
        return self.run(**kwargs)

    def prepare_citations(self, answer, docs):
        return [], []


def test_v3_packer_counts_product_prompt_history_and_reserves():
    docs = [
        RetrievedDocument(
            id_=f"budget-seed-{index}",
            text=f"evidence segment {index} " + ("x" * 40),
            metadata={
                "knowledge_evidence_role": "seed",
                "file_name": f"guide-{index}.md",
            },
        )
        for index in range(2)
    ]
    question = 'What is the result for "the example"?'
    history = [
        ("older question", "older answer"),
        ("recent question", "recent answer"),
    ]
    output_reserve = 17
    format_reserve = 9

    for answering_pipeline in (
        AnswerWithContextPipeline(
            system_prompt="System instructions",
            qa_template=(
                "Question={question}\nContext={context}\nLanguage={lang}\nAnswer="
            ),
            n_last_interactions=1,
        ),
        AnswerWithInlineCitation(
            system_prompt="System instructions",
            qa_citation_template="Citation format. Question={question}\nContext={context}",
            n_last_interactions=1,
        ),
    ):
        evidence_pipeline = PrepareEvidencePipeline(
            max_context_length=4096, token_counter=len
        )
        evidence_mode, evidence, _images = evidence_pipeline(docs).content
        prompt, _ = answering_pipeline.get_prompt(question, evidence, evidence_mode)
        all_messages = [
            {"role": "system", "content": answering_pipeline.system_prompt},
            {"role": "user", "content": history[-1][0]},
            {"role": "assistant", "content": history[-1][1]},
            {"role": "user", "content": prompt},
        ]
        full_message_tokens = len(
            json.dumps(
                all_messages,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        )
        model_context = full_message_tokens + output_reserve + format_reserve - 1
        pipeline = FullQAPipeline(
            retrievers=[],
            evidence_pipeline=PrepareEvidencePipeline(
                max_context_length=model_context, token_counter=len
            ),
            answering_pipeline=answering_pipeline,
            output_reserve=output_reserve,
            format_reserve=format_reserve,
        )

        packed_docs, packed = pipeline._pack_authorized_v3_evidence(
            docs,
            None,
            question=question,
            history=history,
        )
        evidence_mode, evidence, _images = pipeline.evidence_pipeline(
            packed_docs
        ).content
        prompt, _ = answering_pipeline.get_prompt(question, evidence, evidence_mode)
        expected_messages = [
            {"role": "system", "content": answering_pipeline.system_prompt},
            {"role": "user", "content": history[-1][0]},
            {"role": "assistant", "content": history[-1][1]},
            {"role": "user", "content": prompt},
        ]
        expected_tokens = len(
            json.dumps(
                expected_messages,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        )

        assert packed.request_token_count == expected_tokens
        assert packed.request_tokens_available == (
            model_context - output_reserve - format_reserve
        )
        assert expected_tokens + output_reserve + format_reserve <= model_context
        assert len(packed_docs) < len(docs)


def _drain(generator):
    outputs = []
    while True:
        try:
            outputs.append(next(generator))
        except StopIteration as stopped:
            return outputs, stopped.value


class BrokenScopedTrace:
    def __init__(self):
        self.events = []
        self.scope_calls = []

    def scoped(self, **context):
        self.scope_calls.append(context)
        raise RuntimeError("trace scope unavailable")

    def update(self, mapping=None, **fields):
        if mapping is not None:
            fields = {**mapping, **fields}
        self.events.append(("update", fields))

    def record(self, stage, **fields):
        self.events.append((stage, fields))


def test_normal_qa_stream_hands_same_trace_through_retrieval_and_evidence():
    class Retriever:
        def __init__(self):
            self.calls = []

        def __call__(self, **kwargs):
            self.calls.append(kwargs)
            kwargs["trace"].record("synthetic_retriever", ids=["stream-chunk"])
            return [
                RetrievedDocument(
                    id_="stream-chunk",
                    text="A full cited source passage.",
                    metadata={"file_name": "guide.md"},
                )
            ]

        def generate_relevant_scores(self, query, documents):
            return documents

    retriever = Retriever()
    pipeline = FullQAPipeline(
        retrievers=[retriever],
        evidence_pipeline=PrepareEvidencePipeline(
            max_context_length=300, token_counter=len
        ),
        answering_pipeline=FakeAnsweringPipeline(),
    )
    pipeline._prepare_child = lambda child, name: child
    trace = RetrievalTrace()

    outputs, answer = _drain(
        pipeline.stream("question", "conversation", [], trace=trace)
    )
    snapshot = trace.to_dict()

    assert isinstance(answer, Document)
    assert outputs and all(isinstance(item, Document) for item in outputs)
    assert retriever.calls[0]["trace"] is not None
    assert snapshot["context"]["chunk_ids"] == ["stream-chunk"]
    assert [
        event["stage"]
        for event in snapshot["events"]
        if event["stage"] in {"qa_query", "synthetic_retriever", "context"}
    ] == ["qa_query", "synthetic_retriever", "context"]


def test_decomposed_stream_labels_subquestions_and_main_question_on_one_trace():
    class Retriever:
        def __init__(self):
            self.calls = []

        def __call__(self, **kwargs):
            self.calls.append(kwargs)
            return [
                RetrievedDocument(id_="same-chunk", text="source passage", metadata={})
            ]

        def generate_relevant_scores(self, query, documents):
            return documents

    class Decomposer:
        def __call__(self, question):
            return [
                Document(text="first subquestion"),
                Document(text="second subquestion"),
            ]

    retriever = Retriever()
    pipeline = FullDecomposeQAPipeline(
        retrievers=[retriever],
        evidence_pipeline=PrepareEvidencePipeline(
            max_context_length=300, token_counter=len
        ),
        answering_pipeline=FakeAnsweringPipeline(),
    )
    pipeline._prepare_child = lambda child, name: child
    pipeline.rewrite_pipeline = Decomposer()
    trace = RetrievalTrace()

    outputs, answer = _drain(
        pipeline.stream("main question", "conversation", [], trace=trace)
    )

    events = trace.to_dict()["events"]
    query_events = [event for event in events if event["stage"] == "qa_query"]
    labels = [
        (event["query_kind"], event.get("subquestion_index")) for event in query_events
    ]
    assert labels == [("subquestion", 0), ("subquestion", 1), ("main", None)]
    context_events = [event for event in events if event["stage"] == "context"]
    context_labels = [
        (event.get("query_kind"), event.get("subquestion_index"))
        for event in context_events
    ]
    assert context_labels == labels
    assert len(retriever.calls) == 3
    assert all(call["trace"] is not None for call in retriever.calls)
    assert isinstance(answer, Document)
    assert outputs and all(isinstance(item, Document) for item in outputs)


def test_extra_table_trace_reports_the_final_authorized_ui_ids(monkeypatch):
    selected = RetrievedDocument(
        id_="selected-text",
        text="Table 4 summarizes the selected source.",
        metadata={"file_id": "source-a", "file_name": "guide.md", "page_label": "4"},
    )
    selected_table = RetrievedDocument(
        id_="selected-table",
        text="Selected table contents.",
        metadata={"file_id": "source-a", "type": "table", "page_label": "4"},
    )

    def search_main(self, query, **kwargs):
        trace = kwargs["trace"]
        trace.record("merged", ids=["selected-text"])
        trace.record("reranker", name="main-reranker", candidates=["selected-text"])
        trace.record("diversity", selected_ids=["selected-text"])
        trace.record("final", ids=["selected-text"])
        return [selected]

    service = type(
        "Service",
        (),
        {
            "search": search_main,
            "chunk_ids_for_sources": lambda self, ids: [
                "selected-text",
                "selected-table",
            ],
        },
    )()

    class ExtraRetriever:
        def __call__(self, **kwargs):
            trace = kwargs["trace"]
            trace.record("merged", ids=["selected-table"])
            trace.record(
                "reranker", name="table-reranker", candidates=["selected-table"]
            )
            trace.record("diversity", selected_ids=["selected-table"])
            trace.record("final", ids=["selected-table"])
            return [selected_table]

    monkeypatch.setattr(
        "ktem.index.file.pipelines.create_file_knowledge_service",
        lambda **kwargs: service,
        raising=False,
    )
    monkeypatch.setattr(
        "ktem.index.file.pipelines.VectorRetrieval",
        lambda **kwargs: ExtraRetriever(),
    )
    pipeline = DocumentRetrievalPipeline(
        embedding=None,
        Source=object(),
        Index=object(),
        VS=object(),
        DS=object(),
        get_extra_table=True,
    )
    trace = RetrievalTrace()

    result = pipeline.run(text="question", doc_ids=["source-a"], trace=trace)

    snapshot = trace.to_dict()
    assert [doc.doc_id for doc in result] == ["selected-text", "selected-table"]
    assert snapshot["merged_ids"] == ["selected-text"]
    assert snapshot["diversity_selected_ids"] == ["selected-text"]
    assert snapshot["final_chunk_ids"] == ["selected-text"]
    assert snapshot["final_ui_chunk_ids"] == ["selected-text", "selected-table"]
    auxiliary = snapshot["auxiliary_retrievals"]["extra_table"]
    assert auxiliary["merged_ids"] == ["selected-table"]
    assert auxiliary["diversity_selected_ids"] == ["selected-table"]
    assert auxiliary["final_chunk_ids"] == ["selected-table"]
    assert "unselected" not in str(snapshot["final_ui_chunk_ids"])


def test_extra_table_trace_never_records_foreign_candidates_after_zero_scope_hits(
    monkeypatch,
):
    selected = RetrievedDocument(
        id_="selected-text",
        text="Table 4 summarizes the selected source.",
        metadata={"file_id": "source-a", "file_name": "guide.md", "page_label": "4"},
    )
    foreign_table = Document(
        id_="foreign-table",
        text="A table from a different source.",
        metadata={
            "file_id": "source-b",
            "file_name": "guide.md",
            "page_label": "4",
            "type": "table",
        },
    )
    service = type(
        "Service",
        (),
        {
            "search": lambda self, query, **kwargs: [selected],
            "chunk_ids_for_sources": lambda self, ids: [
                "selected-text",
                "selected-table",
            ],
        },
    )()

    class Embedding(BaseEmbeddings):
        def run(self, text, *args, **kwargs):
            return [DocumentWithEmbedding(embedding=[1.0, 0.0])]

    class VectorStore(BaseVectorStore):
        def __init__(self):
            self.query_scopes = []

        def add(self, embeddings, metadatas=None, ids=None):
            return ids or []

        def delete(self, ids, **kwargs):
            return None

        def query(self, embedding, top_k=1, ids=None, **kwargs):
            self.query_scopes.append(ids)
            if ids is None:
                return [], [0.9], ["foreign-table"]
            return [], [], []

        def drop(self):
            return None

    class DocumentStore(BaseDocumentStore):
        supports_lexical_search = False

        def __init__(self):
            self.docs = {"foreign-table": foreign_table}

        def add(self, docs, ids=None, **kwargs):
            return None

        def get(self, ids):
            requested = [ids] if isinstance(ids, str) else list(ids)
            return [self.docs[doc_id] for doc_id in requested if doc_id in self.docs]

        def get_all(self):
            return list(self.docs.values())

        def count(self):
            return len(self.docs)

        def query(self, query, top_k=10, doc_ids=None):
            return []

        def delete(self, ids):
            return None

        def drop(self):
            return None

    vector_store = VectorStore()
    extra_retrieval = VectorRetrieval(
        vector_store=vector_store,
        doc_store=DocumentStore(),
        embedding=Embedding(),
        retrieval_mode="vector",
    )
    monkeypatch.setattr(
        "ktem.index.file.pipelines.create_file_knowledge_service",
        lambda **kwargs: service,
        raising=False,
    )
    monkeypatch.setattr(
        "ktem.index.file.pipelines.VectorRetrieval",
        lambda **kwargs: extra_retrieval,
    )
    pipeline = DocumentRetrievalPipeline(
        embedding=Embedding(),
        Source=object(),
        Index=object(),
        VS=vector_store,
        DS=DocumentStore(),
        get_extra_table=True,
    )
    trace = RetrievalTrace()

    result = pipeline.run(text="question", doc_ids=["source-a"], trace=trace)

    snapshot = trace.to_dict()
    recall_events = [
        event for event in snapshot["events"] if event["stage"] == "recall_attempt"
    ]
    traced_candidate_ids = [
        candidate["id"]
        for event in recall_events
        for branch in ("vector_candidates", "lexical_candidates")
        for candidate in event.get(branch, [])
    ]
    final_ui_events = [
        event for event in snapshot["events"] if event["stage"] == "final_ui"
    ]
    assert [doc.doc_id for doc in result] == ["selected-text"]
    assert "foreign-table" not in traced_candidate_ids
    assert all(
        doc_id in {"selected-text", "selected-table"} for doc_id in traced_candidate_ids
    )
    assert vector_store.query_scopes == [["selected-text", "selected-table"]]
    assert final_ui_events[-1]["ids"] == ["selected-text"]
    assert snapshot["final_ui_chunk_ids"] == ["selected-text"]


def test_broken_scoped_trace_does_not_interrupt_qa_stream_or_evidence_handoff():
    class Retriever:
        def __call__(self, **kwargs):
            kwargs["trace"].record("retriever_used", ids=["usable"])
            return [
                RetrievedDocument(id_="usable", text="usable evidence", metadata={})
            ]

        def generate_relevant_scores(self, query, documents):
            return documents

    trace = BrokenScopedTrace()
    pipeline = FullQAPipeline(
        retrievers=[Retriever()],
        evidence_pipeline=PrepareEvidencePipeline(
            max_context_length=200, token_counter=len
        ),
        answering_pipeline=FakeAnsweringPipeline(),
    )
    pipeline._prepare_child = lambda child, name: child

    outputs, answer = _drain(
        pipeline.stream("question", "conversation", [], trace=trace)
    )

    assert answer.text == "answer"
    assert outputs and all(isinstance(item, Document) for item in outputs)
    assert "retriever_used" in [stage for stage, _ in trace.events]
    assert "context" in [stage for stage, _ in trace.events]
    assert trace.scope_calls == [
        {"retriever_index": 0, "retriever_name": "Retriever", "query_kind": "main"},
        {"query_kind": "main"},
    ]


def test_broken_scoped_trace_does_not_skip_extra_table_retrieval(monkeypatch):
    selected = RetrievedDocument(
        id_="selected-text",
        text="Table 4 summarizes the selected source.",
        metadata={"file_id": "source-a", "file_name": "guide.md", "page_label": "4"},
    )
    selected_table = RetrievedDocument(
        id_="selected-table",
        text="Selected table contents.",
        metadata={"file_id": "source-a", "type": "table", "page_label": "4"},
    )
    service = type(
        "Service",
        (),
        {
            "search": lambda self, query, **kwargs: [selected],
            "chunk_ids_for_sources": lambda self, ids: [
                "selected-text",
                "selected-table",
            ],
        },
    )()

    class ExtraRetriever:
        def __init__(self):
            self.calls = []

        def __call__(self, **kwargs):
            self.calls.append(kwargs)
            return [selected_table]

    extra_retriever = ExtraRetriever()
    monkeypatch.setattr(
        "ktem.index.file.pipelines.create_file_knowledge_service",
        lambda **kwargs: service,
        raising=False,
    )
    monkeypatch.setattr(
        "ktem.index.file.pipelines.VectorRetrieval",
        lambda **kwargs: extra_retriever,
    )
    pipeline = DocumentRetrievalPipeline(
        embedding=None,
        Source=object(),
        Index=object(),
        VS=object(),
        DS=object(),
        get_extra_table=True,
    )
    trace = BrokenScopedTrace()

    result = pipeline.run(text="question", doc_ids=["source-a"], trace=trace)

    assert [doc.doc_id for doc in result] == ["selected-text", "selected-table"]
    assert len(extra_retriever.calls) == 1
    assert extra_retriever.calls[0]["trace"] is trace
    assert trace.scope_calls == [{"query_kind": "extra_table"}]


def test_broken_trace_does_not_interrupt_context_or_qa_retrieval():
    class BrokenTrace:
        def update(self, *args, **kwargs):
            raise RuntimeError("trace broken")

        def record(self, *args, **kwargs):
            raise RuntimeError("trace broken")

    class LegacyRetriever:
        def __call__(self, **kwargs):
            return [
                RetrievedDocument(id_="usable", text="usable evidence", metadata={})
            ]

        def generate_relevant_scores(self, query, documents):
            return documents

    trace = BrokenTrace()
    evidence = PrepareEvidencePipeline(max_context_length=200, token_counter=len)
    evidence_result = evidence.run(
        [RetrievedDocument(id_="usable", text="usable evidence", metadata={})],
        trace=trace,
    )
    pipeline = FullQAPipeline(
        retrievers=[LegacyRetriever()],
        evidence_pipeline=evidence,
        answering_pipeline=FakeAnsweringPipeline(),
    )
    pipeline._prepare_child = lambda child, name: child

    docs, _ = pipeline.retrieve("question", [], trace=trace)
    outputs, answer = _drain(
        pipeline.stream("question", "conversation", [], trace=trace)
    )

    assert "usable evidence" in evidence_result.content[1]
    assert [doc.doc_id for doc in docs] == ["usable"]
    assert answer.text == "answer"
    assert outputs and all(isinstance(item, Document) for item in outputs)


def test_complete_service_retrieval_context_trace_round_trips_and_maps_citation():
    first_text = (
        "Vector retrieval assembled this full evidence passage for citation mapping."
    )
    second_text = "A related but lower-ranked passage from the same parent section."
    documents = {
        "chunk-a": Document(
            id_="chunk-a",
            text=first_text,
            metadata={
                "file_id": "source-a",
                "document_id": "source-a",
                "parent_id": "p",
            },
        ),
        "chunk-b": Document(
            id_="chunk-b",
            text=second_text,
            metadata={
                "file_id": "source-a",
                "document_id": "source-a",
                "parent_id": "p",
            },
        ),
    }

    class TwoChunkCatalog(FakeCatalog):
        def chunk_ids(self, source_ids, relation_type="document"):
            return {"source-a": ["chunk-a", "chunk-b"]}

    class Embedding(BaseEmbeddings):
        def run(self, text, *args, **kwargs):
            return [DocumentWithEmbedding(embedding=[0.1, 0.2])]

    class VectorStore(BaseVectorStore):
        def __init__(self):
            pass

        def add(self, embeddings, metadatas=None, ids=None):
            return ids or []

        def delete(self, ids, **kwargs):
            return None

        def query(self, embedding, top_k=1, ids=None, **kwargs):
            return [], [0.88, 0.72], ["chunk-a", "chunk-b"]

        def drop(self):
            return None

    class DocumentStore(BaseDocumentStore):
        supports_lexical_search = True

        def __init__(self):
            self.docs = documents

        def add(self, docs, ids=None, **kwargs):
            return None

        def get(self, ids):
            requested = [ids] if isinstance(ids, str) else list(ids)
            return [
                self.docs[doc_id]
                for doc_id in reversed(requested)
                if doc_id in self.docs
            ]

        def get_all(self):
            return list(self.docs.values())

        def count(self):
            return len(self.docs)

        def query(self, query, top_k=10, doc_ids=None):
            results = [self.docs["chunk-b"], self.docs["chunk-a"]]
            if doc_ids is not None:
                results = [doc for doc in results if doc.doc_id in doc_ids]
            return results[:top_k]

        def delete(self, ids):
            return None

        def drop(self):
            return None

    class ScoredReranker(BaseReranking):
        def run(self, documents, query):
            scores = {"chunk-a": 0.97, "chunk-b": 0.84}
            ordered = sorted(documents, key=lambda document: document.doc_id)
            return [
                RetrievedDocument(
                    **{**document.to_dict(), "score": scores[document.doc_id]}
                )
                for document in ordered
            ]

    retriever = VectorRetrieval(
        vector_store=VectorStore(),
        doc_store=DocumentStore(),
        embedding=Embedding(),
        retrieval_mode="hybrid",
        rerankers=[ScoredReranker()],
        max_per_parent_or_section=1,
    )
    service = KnowledgeService(
        planner=FakePlanner(),
        catalog=TwoChunkCatalog(),
        retriever=retriever,
        docstore=None,
    )
    trace = RetrievalTrace()

    result = service.search(
        "original retrieval question",
        top_k=1,
        allowed_source_ids=["source-a"],
        trace=trace,
    )
    _, evidence, _ = (
        PrepareEvidencePipeline(max_context_length=500, token_counter=len)
        .run(result, trace=trace)
        .content
    )
    answer = SimpleNamespace(
        metadata={
            "citation": SimpleNamespace(
                evidences=["assembled this full evidence passage"]
            )
        }
    )
    citation_spans = AnswerWithContextPipeline.match_evidence_with_context(
        None, answer, result
    )
    snapshot = json.loads(trace.to_json())
    stages = [event["stage"] for event in snapshot["events"]]
    attempt = snapshot["attempts"][0]

    assert [document.doc_id for document in result] == ["chunk-a"]
    assert snapshot["original_query"] == "original retrieval question"
    assert snapshot["plan"]["semantic_query"] == "semantic query"
    assert snapshot["source_scope"]["visible_ids"] == ["source-a"]
    assert snapshot["chunk_scope"]["planned_ids"] == ["chunk-a", "chunk-b"]
    assert attempt["vector_status"] == attempt["lexical_status"] == "available"
    assert [(item["id"], item["score"]) for item in attempt["vector_candidates"]] == [
        ("chunk-a", 0.88),
        ("chunk-b", 0.72),
    ]
    assert [item["id"] for item in attempt["lexical_candidates"]] == [
        "chunk-b",
        "chunk-a",
    ]
    assert all(item["score"] is None for item in attempt["lexical_candidates"])
    assert snapshot["merged_ids"] == ["chunk-b", "chunk-a"]
    assert [item["id"] for item in snapshot["rerankers"][0]["candidates"]] == [
        "chunk-a",
        "chunk-b",
    ]
    assert snapshot["diversity"]["excluded"] == [
        {"id": "chunk-b", "reason": "group_cap"}
    ]
    assert (
        snapshot["final_chunk_ids"] == snapshot["context"]["chunk_ids"] == ["chunk-a"]
    )
    assert snapshot["context"]["tokens_used"] == len(evidence)
    assert "assembled this full evidence passage" in evidence
    assert citation_spans["chunk-a"]
    span = citation_spans["chunk-a"][0]
    assert (
        result[0].text[span["start"] : span["end"]]
        == "assembled this full evidence passage"
    )
    assert [
        stages.index(stage)
        for stage in (
            "request",
            "plan",
            "recall_attempt",
            "merged",
            "reranker",
            "diversity",
            "final",
            "context",
        )
    ] == sorted(
        stages.index(stage)
        for stage in (
            "request",
            "plan",
            "recall_attempt",
            "merged",
            "reranker",
            "diversity",
            "final",
            "context",
        )
    )
