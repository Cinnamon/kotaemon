import json
import uuid
from pathlib import Path

from ktem.components import get_docstore, get_vectorstore
from ktem.llms.manager import llms
from ktem.reasoning.prompt_optimization.rewrite_question import (
    DEFAULT_REWRITE_PROMPT,
    RewriteQuestionPipeline,
)
from theflow.settings import settings as flowsettings

from kotaemon.base import AIMessage, Document, HumanMessage, Node, SystemMessage
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.llms import ChatLLM
from kotaemon.storages import BaseDocumentStore, BaseVectorStore


class FewshotRewriteQuestionPipeline(RewriteQuestionPipeline):
    """Rewrite user question

    Args:
        llm: the language model to rewrite question
        rewrite_template: the prompt template for llm to paraphrase a text input
        lang: the language of the answer. Currently support English and Japanese
        embedding: the embedding model to encode the question
        vector_store: the vector store to store the encoded question
        doc_store: the document store to store the original question
        k: the number of examples to retrieve for rewriting
    """

    llm: ChatLLM = Node(default_callback=lambda _: llms.get_default())
    rewrite_template: str = DEFAULT_REWRITE_PROMPT
    lang: str = "English"
    embedding: BaseEmbeddings
    vector_store: BaseVectorStore
    doc_store: BaseDocumentStore
    k: int = getattr(flowsettings, "N_PROMPT_OPT_EXAMPLES", 3)

    def add_documents(self, examples, batch_size: int = 50):
        print("Adding fewshot examples for rewriting")
        documents = []
        for example in examples:
            doc = Document(
                text=example["input"], id_=str(uuid.uuid4()), metadata=example
            )
            documents.append(doc)

        for i in range(0, len(documents), batch_size):
            embeddings = self.embedding(documents[i : i + batch_size])
            ids = [t.doc_id for t in documents[i : i + batch_size]]
            self.vector_store.add(
                embeddings=embeddings,
                ids=ids,
            )
            self.doc_store.add(documents[i : i + batch_size])

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
            embedding=embedding, vector_store=vector_store, doc_store=doc_store
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

        result = self.llm(messages)
        return result
