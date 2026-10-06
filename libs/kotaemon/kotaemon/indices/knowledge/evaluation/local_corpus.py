"""Deterministic inventory of generated or explicitly selected local sources."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_SUPPORTED_SUFFIXES = frozenset({".pdf", ".docx", ".md", ".xlsx"})
_HASH_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class SourceFile:
    """One supported source path and its exact-byte identity."""

    source_id: str
    relative_path: str
    sha256: str
    suffix: str
    byte_size: int
    duplicate_of: str | None


def scan_sources(root: Path) -> tuple[SourceFile, ...]:
    """Inventory supported regular files under ``root`` without changing them.

    Paths are relative to ``root`` and use POSIX separators. Byte-identical
    files keep separate rows, while the first path in sorted order is canonical.
    """
    root = Path(root)
    candidates: list[tuple[str, str, str, int]] = []

    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        if path.name == ".DS_Store" or path.name.startswith("~$"):
            continue

        suffix = path.suffix.lower()
        if suffix not in _SUPPORTED_SUFFIXES:
            continue

        relative_path = path.relative_to(root).as_posix()
        digest = hashlib.sha256()
        byte_size = 0
        with path.open("rb") as source:
            while chunk := source.read(_HASH_CHUNK_SIZE):
                digest.update(chunk)
                byte_size += len(chunk)

        candidates.append((relative_path, digest.hexdigest(), suffix, byte_size))

    candidates.sort(key=lambda row: row[0])

    canonical_paths: dict[str, str] = {}
    sources: list[SourceFile] = []
    for relative_path, sha256, suffix, byte_size in candidates:
        duplicate_of = canonical_paths.get(sha256)
        if duplicate_of is None:
            canonical_paths[sha256] = relative_path

        sources.append(
            SourceFile(
                source_id=sha256,
                relative_path=relative_path,
                sha256=sha256,
                suffix=suffix,
                byte_size=byte_size,
                duplicate_of=duplicate_of,
            )
        )

    return tuple(sources)


def canonical_sources(sources: Iterable[SourceFile]) -> tuple[SourceFile, ...]:
    """Return one indexable inventory row for each exact-byte identity."""
    return tuple(source for source in sources if source.duplicate_of is None)


def unsupported_paths(root: Path) -> tuple[str, ...]:
    """List unsupported regular-file paths without reading or hashing contents."""
    root = Path(root)
    paths = []
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        if path.name == ".DS_Store" or path.name.startswith("~$"):
            continue
        if path.suffix.lower() in _SUPPORTED_SUFFIXES:
            continue
        paths.append(path.relative_to(root).as_posix())
    return tuple(sorted(paths))
