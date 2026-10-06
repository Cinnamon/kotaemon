"""Ephemeral document storage with an optional SQLite FTS5 lexical index."""

from __future__ import annotations

import json
import sqlite3
import threading
import unicodedata
from collections.abc import Callable
from typing import Optional, Union

from kotaemon.base import Document

from .base import BaseDocumentStore

_CJK_RANGES = (
    (0x3400, 0x4DBF),  # CJK Extension A
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
    (0x20000, 0x2FA1F),  # CJK Extensions B-F
    (0x2EBF0, 0x2EE5D),  # CJK Extension I
    (0x30000, 0x323AF),  # CJK Extensions G and H
    (0x3040, 0x30FF),  # Hiragana and Katakana
    (0x31F0, 0x31FF),  # Katakana Phonetic Extensions
    (0x1B000, 0x1B16F),  # Kana supplements and extensions
    (0x3100, 0x312F),  # Bopomofo
    (0x31A0, 0x31BF),  # Bopomofo Extended
    (0x1100, 0x11FF),  # Hangul Jamo
    (0x3130, 0x318F),  # Hangul Compatibility Jamo
    (0xA960, 0xA97F),  # Hangul Jamo Extended-A
    (0xAC00, 0xD7AF),  # Hangul syllables
    (0xD7B0, 0xD7FF),  # Hangul Jamo Extended-B
)


def _is_cjk(character: str) -> bool:
    codepoint = ord(character)
    return any(start <= codepoint <= end for start, end in _CJK_RANGES)


def lexical_tokens(text: str) -> tuple[str, ...]:
    """Return normalized Latin/code terms and overlapping CJK bigrams.

    The preprocessing is intentionally small and versioned as ``cjk_bigram_v1``.
    It is not a Chinese word segmenter and makes no stemming or synonym claim.
    """
    normalized = unicodedata.normalize("NFKC", text).casefold()
    tokens: list[str] = []
    index = 0

    while index < len(normalized):
        character = normalized[index]
        if _is_cjk(character):
            end = index + 1
            while end < len(normalized) and _is_cjk(normalized[end]):
                end += 1

            run = normalized[index:end]
            if len(run) == 1:
                previous_is_delimiter = index == 0 or not (
                    normalized[index - 1].isalnum() or normalized[index - 1] == "_"
                )
                next_is_delimiter = end == len(normalized) or not (
                    normalized[end].isalnum() or normalized[end] == "_"
                )
                if previous_is_delimiter and next_is_delimiter:
                    tokens.append(run)
            else:
                tokens.extend(
                    run[offset : offset + 2] for offset in range(len(run) - 1)
                )
            index = end
            continue

        if character.isalnum() or character == "_":
            end = index + 1
            while end < len(normalized) and (
                not _is_cjk(normalized[end])
                and (normalized[end].isalnum() or normalized[end] == "_")
            ):
                end += 1
            tokens.append(normalized[index:end])
            index = end
            continue

        index += 1

    # Preserve source order while making repeated terms a single MATCH alternative.
    return tuple(dict.fromkeys(tokens))


class SQLiteFTSDocumentStore(BaseDocumentStore):
    """In-memory document store whose optional FTS5 index searches document text."""

    def __init__(
        self,
        *,
        connection_factory: Callable[[str], sqlite3.Connection] | None = None,
    ):
        self._connection = (
            sqlite3.connect(":memory:", check_same_thread=False)
            if connection_factory is None
            else connection_factory(":memory:")
        )
        self._lock = threading.RLock()
        self._connection.execute(
            "CREATE TABLE documents ("
            "id TEXT PRIMARY KEY, text TEXT NOT NULL, metadata TEXT NOT NULL)"
        )
        self.configuration = {
            "tokenizer": "unicode61",
            "preprocessing": "cjk_bigram_v1",
        }
        self.capability_reason: str | None = None
        self.supports_lexical_search = True
        try:
            self._connection.execute(
                "CREATE VIRTUAL TABLE documents_fts USING "
                "fts5(id UNINDEXED, tokens, tokenize='unicode61')"
            )
        except sqlite3.OperationalError as error:
            self.supports_lexical_search = False
            self.capability_reason = str(error)

    def add(
        self,
        docs: Union[Document, list[Document]],
        ids: Optional[Union[list[str], str]] = None,
        **kwargs,
    ):
        exist_ok: bool = kwargs.pop("exist_ok", False)
        if ids and not isinstance(ids, list):
            ids = [ids]
        if not isinstance(docs, list):
            docs = [docs]
        doc_ids = ids if ids else [doc.doc_id for doc in docs]

        with self._lock:
            for doc_id, document in zip(doc_ids, docs):
                existing = self._connection.execute(
                    "SELECT 1 FROM documents WHERE id = ?", (doc_id,)
                ).fetchone()
                if existing is not None and not exist_ok:
                    raise ValueError(f"Document with id {doc_id} already exist")

                text = document.text or ""
                metadata = json.dumps(document.metadata, ensure_ascii=False)
                self._connection.execute(
                    "INSERT OR REPLACE INTO documents (id, text, metadata) VALUES (?, ?, ?)",
                    (doc_id, text, metadata),
                )
                if self.supports_lexical_search:
                    self._connection.execute(
                        "DELETE FROM documents_fts WHERE id = ?", (doc_id,)
                    )
                    self._connection.execute(
                        "INSERT INTO documents_fts (id, tokens) VALUES (?, ?)",
                        (doc_id, " ".join(lexical_tokens(text))),
                    )

    def get(self, ids: Union[list[str], str]) -> list[Document]:
        if not isinstance(ids, list):
            ids = [ids]
        documents: list[Document] = []
        with self._lock:
            for doc_id in ids:
                row = self._connection.execute(
                    "SELECT id, text, metadata FROM documents WHERE id = ?", (doc_id,)
                ).fetchone()
                if row is None:
                    raise KeyError(doc_id)
                documents.append(self._document_from_row(row))
        return documents

    def get_all(self) -> list[Document]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT id, text, metadata FROM documents ORDER BY rowid"
            ).fetchall()
        return [self._document_from_row(row) for row in rows]

    def count(self) -> int:
        with self._lock:
            row = self._connection.execute("SELECT COUNT(*) FROM documents").fetchone()
        return int(row[0])

    def query(
        self, query: str, top_k: int = 10, doc_ids: Optional[list[str]] = None
    ) -> list[Document]:
        if not self.supports_lexical_search:
            reason = self.capability_reason or "FTS5 is not available"
            raise RuntimeError(f"SQLite FTS5 lexical search is unavailable: {reason}")
        if top_k <= 0:
            return []
        tokens = lexical_tokens(query)
        if not tokens:
            return []
        if doc_ids is not None and not doc_ids:
            return []

        match_expression = " OR ".join(
            '"' + token.replace('"', '""') + '"' for token in tokens
        )
        parameters: list[object] = [match_expression]
        allowlist_sql = ""
        if doc_ids is not None:
            placeholders = ", ".join("?" for _ in doc_ids)
            allowlist_sql = f" AND documents.id IN ({placeholders})"
            parameters.extend(doc_ids)
        parameters.append(top_k)

        with self._lock:
            rows = self._connection.execute(
                "SELECT documents.id, documents.text, documents.metadata "
                "FROM documents_fts JOIN documents ON documents.id = documents_fts.id "
                "WHERE documents_fts MATCH ?"
                + allowlist_sql
                + " ORDER BY bm25(documents_fts) ASC, documents.id ASC LIMIT ?",
                parameters,
            ).fetchall()
        return [self._document_from_row(row) for row in rows]

    def delete(self, ids: Union[list[str], str]):
        if not isinstance(ids, list):
            ids = [ids]
        with self._lock:
            for doc_id in ids:
                exists = self._connection.execute(
                    "SELECT 1 FROM documents WHERE id = ?", (doc_id,)
                ).fetchone()
                if exists is None:
                    raise KeyError(doc_id)
                if self.supports_lexical_search:
                    self._connection.execute(
                        "DELETE FROM documents_fts WHERE id = ?", (doc_id,)
                    )
                self._connection.execute(
                    "DELETE FROM documents WHERE id = ?", (doc_id,)
                )

    def drop(self):
        with self._lock:
            if self.supports_lexical_search:
                self._connection.execute("DELETE FROM documents_fts")
            self._connection.execute("DELETE FROM documents")

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    @staticmethod
    def _document_from_row(row) -> Document:
        return Document(id_=row[0], text=row[1], metadata=json.loads(row[2]))

    def __persist_flow__(self):
        return {}


__all__ = ["SQLiteFTSDocumentStore", "lexical_tokens"]
