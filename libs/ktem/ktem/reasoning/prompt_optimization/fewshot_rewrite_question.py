import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ktem.components import get_docstore, get_vectorstore
from ktem.llms.manager import llms
from ktem.reasoning.prompt_optimization.rewrite_question import (
    DEFAULT_REWRITE_PROMPT,
    RewriteQuestionPipeline,
)
from ktem.settings_config import app_settings as flowsettings

from kotaemon.base import AIMessage, Document, HumanMessage, SystemMessage
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.llms import ChatLLM
from kotaemon.storages import BaseDocumentStore, BaseVectorStore


@dataclass(kw_only=True)
class FewshotRewriteQuestionPipeline(RewriteQuestionPipeline):
    llm: ChatLLM = field(default_factory=lambda: llms.get_default())
    rewrite_template: str = DEFAULT_REWRITE_PROMPT
    lang: str = "English"
    embedding: BaseEmbeddings = field(repr=False)
    vector_store: BaseVectorStore = field(repr=False)
    doc_store: BaseDocumentStore = field(repr=False)
    k: int = field(default_factory=lambda: flowsettings.N_PROMPT_OPT_EXAMPLES)

    def add_documents(self, examples, batch_size: int = 50):
        documents = [
            Document(text=ex["input"], id_=str(uuid.uuid4()), metadata=ex)
            for ex in examples
        ]
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            embeddings = self.embedding(batch)
            ids = [t.doc_id for t in batch]
            self.vector_store.add(embeddings=embeddings, ids=ids)
            self.doc_store.add(batch)

    @classmethod
    def get_pipeline(
        cls,
        embedding,
        example_path=Path(__file__).parent / "rephrase_question_train.json",
        collection_name: str = "fewshot_rewrite_examples",
    ):
        vector_store = get_vectorstore(collection_name)
        doc_store = get_docstore(collection_name)
        pipeline = cls(
            embedding=embedding,
            vector_store=vector_store,
            doc_store=doc_store,
        )
        if doc_store.count():
            return pipeline
        examples = json.load(open(example_path, "r"))
        pipeline.add_documents(examples)
        return pipeline

    def run(self, question: str) -> Document:  # type: ignore
        emb = self.embedding(question)[0].embedding
        _, _, ids = self.vector_store.query(embedding=emb, top_k=self.k)
        examples = self.doc_store.get(ids)
        messages = [SystemMessage(content="You are a helpful assistant")]
        for example in examples:
            messages.append(
                HumanMessage(
                    content=self.rewrite_template.format(
                        question=example.metadata["input"], lang=self.lang
                    )
                )
            )
            messages.append(AIMessage(content=example.metadata["output"]))
        messages.append(
            HumanMessage(
                content=self.rewrite_template.format(question=question, lang=self.lang)
            )
        )
        return self.llm(messages)
