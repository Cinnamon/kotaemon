import os

from kotaemon.base import BaseComponent, Document, Node, RetrievedDocument
from kotaemon.llms import BaseLLM, LCAzureChatOpenAI, PromptTemplate

from .citation import CitationPipeline


class CitationQAPipeline(BaseComponent):
    """Answering question from a text corpus with citation"""

    qa_prompt_template: PromptTemplate = PromptTemplate(
        'Answer the following question: "{question}". '
        "The context is: \n{context}\nAnswer: "
    )
    llm: BaseLLM = LCAzureChatOpenAI.withx(
        azure_endpoint="https://bleh-dummy.openai.azure.com/",
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        openai_api_version="2023-07-01-preview",
        deployment_name="dummy-q2-16k",
        temperature=0,
        request_timeout=60,
    )
    citation_pipeline: CitationPipeline = Node(
        default_callback=lambda self: CitationPipeline(llm=self.llm)
    )

    def _format_doc_text(self, text: str) -> str:
        """Format the text of each document"""
        return text.replace("\n", " ")

    def _format_retrieved_context(self, documents: list[RetrievedDocument]) -> str:
        """Format the texts between all documents"""
        matched_texts: list[str] = [
            self._format_doc_text(doc.text) for doc in documents
        ]
        return "\n\n".join(matched_texts)

    def run(
        self,
        question: str,
        documents: list[RetrievedDocument],
        use_citation: bool = False,
        **kwargs
    ) -> Document:
        # retrieve relevant documents as context
        context = self._format_retrieved_context(documents)
        self.log_progress(".context", context=context)

        # generate the answer
        prompt = self.qa_prompt_template.populate(
            context=context,
            question=question,
        )
        self.log_progress(".prompt", prompt=prompt)
        answer_text = self.llm(prompt).text
        if use_citation:
            citation = self.citation_pipeline(context=context, question=question)
        else:
            citation = None

        answer = Document(text=answer_text, metadata={"citation": citation})
        return answer
