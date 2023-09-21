from haystack.schema import Document as HaystackDocument
from llama_index.bridge.pydantic import Field
from llama_index.schema import Document as BaseDocument

SAMPLE_TEXT = "A sample Document from kotaemon"


class Document(BaseDocument):
    """Base document class, mostly inherited from Document class from llama-index"""

    @classmethod
    def example(cls) -> "Document":
        document = Document(
            text=SAMPLE_TEXT,
            metadata={"filename": "README.md", "category": "codebase"},
        )
        return document

    def to_haystack_format(self) -> "HaystackDocument":
        """Convert struct to Haystack document format."""
        metadata = self.metadata or {}
        text = self.text
        return HaystackDocument(content=text, meta=metadata)


class RetrievedDocument(Document):
    """Subclass of Document with retrieval-related information

    Attributes:
        score (float): score of the document (from 0.0 to 1.0)
        retrieval_metadata (dict): metadata from the retrieval process, can be used
            by different components in a retrieved pipeline to communicate with each
            other
    """

    score: float = Field(default=0.0)
    retrieval_metadata: dict = Field(default={})
