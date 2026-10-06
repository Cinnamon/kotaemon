"""Generated inputs shared by knowledge evaluation tests."""

from __future__ import annotations

from pathlib import Path

from kotaemon.base import Document


def document(doc_id: str, text: str) -> Document:
    """Build a document with a caller-selected stable test ID."""
    return Document(text=text, doc_id=doc_id)


def make_generated_corpus(root: Path) -> Path:
    """Write a small synthetic corpus for evaluation tests and return its root."""
    root = Path(root)
    generated_documents = {
        "zhang/internship.md": (
            "# Zhang San\n\n"
            "During the internship, Zhang San built a retrieval augmented "
            "generation API.\n"
        ),
        "li/frontend.md": (
            "# Li Si\n\n"
            "Li Si implemented the frontend and connected it to the API.\n"
        ),
        "wang/automation.md": (
            "# Wang Wu\n\n" "Wang Wu automated nightly evaluation and reporting.\n"
        ),
        "legacy/notes.md": (
            "# Legacy Notes\n\n"
            "The older project used a separate retrieval service.\n"
        ),
    }

    for relative_path, text in generated_documents.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    return root
