"""Presentation reader using existing Unstructured slide metadata."""

from pathlib import Path

from llama_index.core.readers.base import BaseReader

from kotaemon.base import Document

from .unstructured_loader import UnstructuredReader


def _joined_document(documents, metadata):
    first = documents[0]
    return Document(
        text="\n\n".join(document.text for document in documents if document.text),
        metadata=metadata,
        source=first.source,
        channel=first.channel,
        excluded_embed_metadata_keys=list(first.excluded_embed_metadata_keys),
        excluded_llm_metadata_keys=list(first.excluded_llm_metadata_keys),
    )


def group_slide_documents(documents: list[Document]) -> list[Document]:
    """Group elements only when every element has a reliable slide boundary."""
    if not documents:
        return []
    boundaries = [
        doc.metadata.get("slide_number") or doc.metadata.get("page_number")
        for doc in documents
    ]
    if any(
        not isinstance(value, (int, str)) or not str(value).strip()
        for value in boundaries
    ):
        metadata = dict(documents[0].metadata)
        for key in ("slide_number", "slide_title", "page_number", "page_label", "page"):
            metadata.pop(key, None)
        return [_joined_document(documents, metadata)]
    groups = {}
    for boundary, document in zip(boundaries, documents):
        groups.setdefault(boundary, []).append(document)
    slides = []
    for number, elements in groups.items():
        first = elements[0]
        title = first.metadata.get("slide_title") or (
            first.text.splitlines()[0] if first.text else f"Slide {number}"
        )
        metadata = {
            **first.metadata,
            "slide_number": number,
            "page_label": first.metadata.get("page_label", number),
            "slide_title": title,
        }
        slides.append(_joined_document(elements, metadata))
    return slides


class PptxReader(BaseReader):
    def __init__(self, reader=None, **kwargs):
        super().__init__()
        self._reader = reader or UnstructuredReader(**kwargs)

    def load_data(self, file: Path, extra_info=None, **kwargs):
        file = Path(file)
        metadata = {
            "file_name": file.name,
            "file_path": str(file.resolve()),
            "source_type": "ppt",
            "presentation": file.name,
            **(extra_info or {}),
        }
        kwargs.pop("split_documents", None)
        documents = self._reader.load_data(
            file, extra_info=metadata, split_documents=True, **kwargs
        )
        # Adapters may return documents without forwarding extra_info.
        for document in documents:
            document.metadata = {**metadata, **document.metadata}
        return group_slide_documents(documents)
