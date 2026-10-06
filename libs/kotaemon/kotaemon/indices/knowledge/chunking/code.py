"""Python semantic units using the standard library AST parser."""

import ast
import io
import textwrap
import tokenize
from pathlib import PurePosixPath

from kotaemon.base import Document
from kotaemon.indices.splitters import BaseSplitter

from .base import semantic_unit
from .token import TokenChunkStrategy

_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


class PythonCodeChunkStrategy:
    def __init__(self, token_splitter: BaseSplitter):
        self.fallback = TokenChunkStrategy(token_splitter)

    def split(self, document: Document) -> list[Document]:
        metadata = document.metadata
        language = metadata.get("language")
        name = (
            metadata.get("file_name")
            or metadata.get("document_name")
            or metadata.get("file_path", "")
        )
        if (language and str(language).lower() not in {"python", "py"}) or (
            not language and PurePosixPath(str(name)).suffix.lower() != ".py"
        ):
            return self.fallback.split(document)
        try:
            tree = ast.parse(document.text)
        except (SyntaxError, ValueError, RecursionError):
            return self.fallback.split(document)
        if not any(isinstance(node, (ast.ClassDef, *_FUNCTIONS)) for node in tree.body):
            return self.fallback.split(document)
        chunks = []
        module_lines = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                chunks.extend(self._class(document, node))
            elif isinstance(node, _FUNCTIONS):
                chunks.extend(self._function(document, node))
            else:
                module_lines.append(self._text(document.text, node))
        # AST spans omit leading/trailing comments and comments between class
        # members. Keep any comments absent from the emitted units retrievable.
        emitted_text = "\n".join([*(chunk.text for chunk in chunks), *module_lines])
        for token in tokenize.generate_tokens(io.StringIO(document.text).readline):
            if token.type == tokenize.COMMENT and token.string not in emitted_text:
                module_lines.append(token.string)
        if module_lines:
            unit = semantic_unit(document, "\n\n".join(module_lines), ["module"])
            unit.metadata["language"] = "python"
            chunks.extend(self.fallback.split(unit))
        return chunks

    @staticmethod
    def _text(source: str, node: ast.AST) -> str:
        text = ast.get_source_segment(source, node) or ""
        decorators = getattr(node, "decorator_list", [])
        if decorators:
            lines = source.splitlines()
            prefix = "\n".join(lines[decorators[0].lineno - 1 : node.lineno - 1])
            text = prefix + "\n" + text
        return text

    def _class(self, document: Document, node: ast.ClassDef) -> list[Document]:
        lines = document.text.splitlines()
        start = node.decorator_list[0].lineno if node.decorator_list else node.lineno
        # Keep declaration, docstring and class-level data without duplicating
        # method bodies inside the class retrieval unit.
        first = node.body[0]
        decorators = getattr(first, "decorator_list", [])
        first_line = decorators[0].lineno if decorators else first.lineno
        first_column = decorators[0].col_offset - 1 if decorators else first.col_offset
        # AST columns count UTF-8 bytes, including for an inline class body.
        last_header_line = (
            lines[first_line - 1].encode("utf-8")[:first_column].decode("utf-8")
        )
        header = "\n".join(
            [*lines[start - 1 : first_line - 1], last_header_line]
        ).rstrip()
        body = [
            self._text(document.text, child)
            for child in node.body
            if not isinstance(child, (ast.ClassDef, *_FUNCTIONS))
        ]
        if not body:
            body = ["pass"]
        unit = semantic_unit(
            document,
            "\n".join([header, *[textwrap.indent(text, "    ") for text in body]]),
            [node.name],
        )
        unit.metadata.update(class_name=node.name, language="python")
        chunks = self.fallback.split(unit)
        parent_id = chunks[0].doc_id if chunks else unit.doc_id
        for child in node.body:
            if isinstance(child, _FUNCTIONS):
                chunks.extend(self._function(document, child, node.name, parent_id))
            elif isinstance(child, ast.ClassDef):
                chunks.extend(self._class(document, child))
        return chunks

    def _function(self, document, node, class_name=None, parent_id=None):
        path = [class_name, node.name] if class_name else [node.name]
        unit = semantic_unit(document, self._text(document.text, node), path)
        unit.metadata.update(function_name=node.name, language="python")
        if class_name:
            unit.metadata.update(class_name=class_name, parent_id=parent_id)
        return self.fallback.split(unit)
