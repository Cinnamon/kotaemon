from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .base import ChunkRelationStore, FileSourceStore, RelationType


@dataclass
class FileSourceRecord:
    """Serialized source file metadata."""

    id: str
    name: str
    path: str
    size: int
    user: str
    note: dict = field(default_factory=dict)


@dataclass
class ChunkRelationRecord:
    """Serialized source-to-chunk link."""

    source_id: str
    target_id: str
    relation_type: str


def _read_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return data


def _write_json_list(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    tmp.replace(path)


@dataclass(kw_only=True)
class FileLevelSourceStore(FileSourceStore):
    """JSON file-backed :class:`FileSourceStore` for standalone kotaemon use.

    Persists rows to ``{storage_dir}/sources.json``. Suitable for
    single-process indexing without SQLAlchemy.
    """

    storage_dir: Path
    private: bool = False

    @property
    def _sources_path(self) -> Path:
        return self.storage_dir / "sources.json"

    def _load(self) -> list[FileSourceRecord]:
        return [FileSourceRecord(**row) for row in _read_json_list(self._sources_path)]

    def _save(self, rows: list[FileSourceRecord]) -> None:
        _write_json_list(self._sources_path, [asdict(r) for r in rows])

    def find_id_by_name(self, name: str, *, user_id: int) -> str | None:
        user = str(user_id)
        for row in self._load():
            if row.name != name:
                continue
            if self.private and row.user != user:
                continue
            return row.id
        return None

    def create_from_url(self, url: str, path_hash: str, *, user_id: int) -> str:
        rows = self._load()
        record = FileSourceRecord(
            id=str(uuid.uuid4()),
            name=url,
            path=path_hash,
            size=0,
            user=str(user_id),
        )
        rows.append(record)
        self._save(rows)
        return record.id

    def create_from_file(
        self, name: str, path_hash: str, size: int, *, user_id: int
    ) -> str:
        rows = self._load()
        record = FileSourceRecord(
            id=str(uuid.uuid4()),
            name=name,
            path=path_hash,
            size=size,
            user=str(user_id),
        )
        rows.append(record)
        self._save(rows)
        return record.id

    def update_note(self, file_id: str, *, tokens: int | None, loader: str) -> None:
        rows = self._load()
        for row in rows:
            if row.id != file_id:
                continue
            if tokens is not None:
                row.note["tokens"] = tokens
            row.note["loader"] = loader
            self._save(rows)
            return

    def delete_source(self, file_id: str) -> None:
        rows = [r for r in self._load() if r.id != file_id]
        self._save(rows)


@dataclass(kw_only=True)
class FileLevelChunkRelationStore(ChunkRelationStore):
    """JSON file-backed :class:`ChunkRelationStore` for standalone kotaemon use.

    Persists rows to ``{storage_dir}/relations.json``.
    """

    storage_dir: Path

    @property
    def _relations_path(self) -> Path:
        return self.storage_dir / "relations.json"

    def _load(self) -> list[ChunkRelationRecord]:
        return [
            ChunkRelationRecord(**row) for row in _read_json_list(self._relations_path)
        ]

    def _save(self, rows: list[ChunkRelationRecord]) -> None:
        _write_json_list(self._relations_path, [asdict(r) for r in rows])

    def add_relations(
        self,
        source_id: str,
        target_ids: list[str],
        relation_type: RelationType,
    ) -> None:
        if not target_ids:
            return
        rows = self._load()
        rows.extend(
            ChunkRelationRecord(
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
            )
            for target_id in target_ids
        )
        self._save(rows)

    def list_target_ids(self, source_id: str, relation_type: RelationType) -> list[str]:
        return [
            row.target_id
            for row in self._load()
            if row.source_id == source_id and row.relation_type == relation_type
        ]

    def list_target_ids_for_sources(
        self, source_ids: list[str], relation_type: RelationType
    ) -> list[str]:
        if not source_ids:
            return []
        allowed = set(source_ids)
        return [
            row.target_id
            for row in self._load()
            if row.source_id in allowed and row.relation_type == relation_type
        ]

    def delete_by_source(self, source_id: str) -> tuple[list[str], list[str]]:
        vs_ids: list[str] = []
        ds_ids: list[str] = []
        kept: list[ChunkRelationRecord] = []
        for row in self._load():
            if row.source_id != source_id:
                kept.append(row)
                continue
            if row.relation_type == "vector":
                vs_ids.append(row.target_id)
            elif row.relation_type == "document":
                ds_ids.append(row.target_id)
        self._save(kept)
        return vs_ids, ds_ids


def make_file_level_stores(
    storage_dir: str | Path,
    *,
    private: bool = False,
) -> tuple[FileLevelSourceStore, FileLevelChunkRelationStore]:
    """Build a matched pair of file-level stores under *storage_dir*.

    Example (standalone kotaemon indexing)::

        from pathlib import Path
        from kotaemon.indices.stores import make_file_level_stores

        file_source, chunk_relations = make_file_level_stores(
            Path("./index_data/default")
        )
    """
    root = Path(storage_dir)
    return (
        FileLevelSourceStore(storage_dir=root, private=private),
        FileLevelChunkRelationStore(storage_dir=root),
    )
