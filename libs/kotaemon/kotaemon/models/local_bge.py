"""Local-only FlagEmbedding adapters for retrieval evaluation.

Production backends require a process started with Hugging Face Hub and
Transformers offline flags. Before importing FlagEmbedding, the adapters verify
those flags, the libraries' offline state, and the active Hub session adapters.
They do not change process state after imports, since cached library state and
sessions can remain online.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import numbers
import os
import re
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Sequence

from kotaemon.base import Document, DocumentWithEmbedding, RetrievedDocument
from kotaemon.embeddings.base import BaseEmbeddings
from kotaemon.rerankings.base import BaseReranking


EMBEDDING_MODEL_ID = "BAAI/bge-m3"
RERANKER_MODEL_ID = "BAAI/bge-reranker-v2-m3"
_WEIGHT_FILES = (
    "model.safetensors",
    "pytorch_model.bin",
    "model.safetensors.index.json",
    "pytorch_model.bin.index.json",
)
_TOKENIZER_FILES = (
    "tokenizer.json",
    "tokenizer.model",
    "sentencepiece.bpe.model",
    "spiece.model",
    "vocab.txt",
    "vocab.json",
)
_WEIGHT_SHARD_RE = re.compile(
    r"^(model|pytorch_model)-(\d+)-of-(\d+)\.(safetensors|bin)$"
)
_OFFLINE_PROCESS_ERROR = (
    "Local BGE inference requires HF_HUB_OFFLINE=1 and "
    "TRANSFORMERS_OFFLINE=1 before process startup, with Hugging Face Hub and "
    "Transformers already offline and the active Hub session using "
    "OfflineAdapter. Start a fresh offline inference process."
)


@dataclass(frozen=True)
class LocalModelPaths:
    """Local model assets plus verified identity and cache provenance."""

    embedding_model_dir: Path
    reranker_model_dir: Path
    embedding_revision: str | None = None
    embedding_weight_source: Literal["cached", "downloaded"] | None = None
    reranker_revision: str | None = None
    reranker_weight_source: Literal["cached", "downloaded"] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "embedding_model_dir", Path(self.embedding_model_dir))
        object.__setattr__(self, "reranker_model_dir", Path(self.reranker_model_dir))


@dataclass(frozen=True)
class LocalModelMetadata:
    """Read-only model identity and runtime facts for experiment reporting.

    ``revision`` and ``weight_source`` are only populated when an upstream
    model-management flow supplies them. The adapters do not infer download
    history from the shape or location of a directory.
    """

    model_id: str
    revision: str | None
    weights_sha256: tuple[tuple[str, str], ...]
    device: str
    flag_embedding_version: str | None
    query_max_length: int
    passage_max_length: int
    weight_source: Literal["cached", "downloaded"] | None


def _validate_model_settings(
    query_max_length: int,
    passage_max_length: int,
    weight_source: str | None,
) -> None:
    if query_max_length <= 0 or passage_max_length <= 0:
        raise ValueError("model truncation lengths must be positive")
    if weight_source not in (None, "cached", "downloaded"):
        raise ValueError("weight_source must be 'cached', 'downloaded', or None")


def _read_indexed_weight_files(model_dir: Path, index_path: Path) -> list[Path]:
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"invalid local model weight index: {index_path.name}"
        ) from exc

    weight_map = index.get("weight_map") if isinstance(index, dict) else None
    if not isinstance(weight_map, dict) or not weight_map:
        raise ValueError(
            f"local model weight index has no weight_map: {index_path.name}"
        )

    filenames = list(weight_map.values())
    if any(not isinstance(name, str) or Path(name).name != name for name in filenames):
        raise ValueError(
            f"local model weight index contains unsafe shard names: {index_path.name}"
        )
    filenames = sorted(set(filenames))
    shards = [model_dir / name for name in filenames]
    missing = [
        path.name for path in shards if not path.is_file() or path.stat().st_size == 0
    ]
    if missing:
        raise FileNotFoundError(
            "local model is missing weight shard files: " + ", ".join(missing)
        )
    return shards


def _local_weight_files(model_dir: Path) -> list[Path]:
    indexed = [
        model_dir / name for name in _WEIGHT_FILES[2:] if (model_dir / name).exists()
    ]
    if indexed:
        files = []
        for index_path in indexed:
            files.extend(_read_indexed_weight_files(model_dir, index_path))
        return sorted(set(files))

    direct = [
        model_dir / name for name in _WEIGHT_FILES[:2] if (model_dir / name).is_file()
    ]
    sharded = sorted(
        path
        for pattern in ("model-*.safetensors", "pytorch_model-*.bin")
        for path in model_dir.glob(pattern)
        if path.is_file()
    )
    files = sorted(set(direct + sharded))
    if not files:
        raise FileNotFoundError(
            f"local model directory has no model weight files: {model_dir}"
        )
    shard_groups: dict[tuple[str, str], tuple[int, set[int]]] = {}
    for path in sharded:
        match = _WEIGHT_SHARD_RE.fullmatch(path.name)
        if match is None:
            raise ValueError(f"unrecognized local model shard name: {path.name}")
        model_name, shard_number, shard_count, extension = match.groups()
        group = (model_name, extension)
        total = int(shard_count)
        previous_total, numbers_found = shard_groups.setdefault(group, (total, set()))
        if previous_total != total:
            raise ValueError(f"inconsistent local model shard count for {model_name}")
        numbers_found.add(int(shard_number))
    for (model_name, extension), (total, numbers_found) in shard_groups.items():
        expected_numbers = set(range(1, total + 1))
        if numbers_found != expected_numbers:
            missing = sorted(expected_numbers - numbers_found)
            missing_names = [
                f"{model_name}-{number:05d}-of-{total:05d}.{extension}"
                for number in missing
            ]
            raise FileNotFoundError(
                "local model is missing weight shard files: " + ", ".join(missing_names)
            )
    if any(path.stat().st_size == 0 for path in files):
        raise FileNotFoundError(
            "local model contains an empty model weight file: "
            + ", ".join(path.name for path in files if path.stat().st_size == 0)
        )
    return files


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        while chunk := model_file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_and_hash_model_dir(
    model_path: str | Path,
) -> tuple[Path, tuple[tuple[str, str], ...]]:
    model_dir = Path(model_path).expanduser()
    if not model_dir.is_dir():
        raise FileNotFoundError(
            "local model directory is unavailable: "
            f"{model_dir}. Provide a local model directory with the required "
            "asset files; automatic downloads are disabled."
        )
    config_path = model_dir / "config.json"
    if not config_path.is_file() or config_path.stat().st_size == 0:
        raise FileNotFoundError(
            f"local model directory is missing config.json: {model_dir}"
        )
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"local model config.json is invalid: {model_dir}") from exc
    if not isinstance(config, dict):
        raise ValueError(f"local model config.json must contain an object: {model_dir}")

    tokenizer_files = [
        model_dir / name
        for name in _TOKENIZER_FILES
        if (model_dir / name).is_file() and (model_dir / name).stat().st_size > 0
    ]
    if not tokenizer_files:
        raise FileNotFoundError(
            f"local model directory is missing tokenizer files: {model_dir}"
        )
    weight_files = _local_weight_files(model_dir)
    return model_dir.resolve(), tuple(
        (path.name, _hash_file(path)) for path in weight_files
    )


def _require_offline_inference_process() -> None:
    """Fail closed unless the current process and Hub session are offline."""
    if (
        os.environ.get("HF_HUB_OFFLINE") != "1"
        or os.environ.get("TRANSFORMERS_OFFLINE") != "1"
    ):
        raise RuntimeError(_OFFLINE_PROCESS_ERROR)

    try:
        from huggingface_hub import constants, get_session
        from huggingface_hub.utils._http import OfflineAdapter
        from transformers.utils.hub import is_offline_mode
    except ImportError as exc:
        raise ImportError(
            "Local BGE evaluation requires the optional dependency "
            "`kotaemon[local-eval]` (FlagEmbedding==1.4.2). Install it in the "
            "local evaluation environment; model downloads are disabled."
        ) from exc

    if not constants.HF_HUB_OFFLINE or not is_offline_mode():
        raise RuntimeError(_OFFLINE_PROCESS_ERROR)

    try:
        session = get_session()
        adapters = tuple(session.adapters.values())
        active_adapters = (
            session.get_adapter("http://huggingface.co"),
            session.get_adapter("https://huggingface.co"),
        )
    except Exception as exc:
        raise RuntimeError(_OFFLINE_PROCESS_ERROR) from exc

    if not adapters or any(type(adapter) is not OfflineAdapter for adapter in adapters):
        raise RuntimeError(_OFFLINE_PROCESS_ERROR)
    if any(type(adapter) is not OfflineAdapter for adapter in active_adapters):
        raise RuntimeError(_OFFLINE_PROCESS_ERROR)


def _load_local_flag_backend(
    model_path: Path,
    model_kind: Literal["embedding", "reranker"],
    *,
    device: str,
    query_max_length: int,
    passage_max_length: int,
) -> Any:
    """Load FlagEmbedding from a preflighted local path after offline checks."""
    _require_offline_inference_process()
    try:
        from FlagEmbedding import BGEM3FlagModel, FlagReranker
    except ImportError as exc:
        raise ImportError(
            "Local BGE evaluation requires the optional dependency "
            "`kotaemon[local-eval]` (FlagEmbedding==1.4.2). Install it in the "
            "local evaluation environment; model downloads are disabled."
        ) from exc

    # FlagEmbedding 1.4.2 delegates model loading to Transformers and does not
    # expose `local_files_only`; the checked process state and explicit local
    # path prevent fallback to the Hub.
    model_path_arg = str(model_path)
    model_id = EMBEDDING_MODEL_ID if model_kind == "embedding" else RERANKER_MODEL_ID
    try:
        if model_kind == "embedding":
            return BGEM3FlagModel(
                model_path_arg,
                use_fp16=False,
                devices=device,
                query_max_length=query_max_length,
                passage_max_length=passage_max_length,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
                trust_remote_code=False,
            )
        return FlagReranker(
            model_path_arg,
            use_fp16=False,
            devices=device,
            query_max_length=query_max_length,
            max_length=passage_max_length,
            trust_remote_code=False,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Could not load local model {model_id} from {model_path_arg}. "
            "The required asset files were found, but the local snapshot may "
            "be corrupt or incompatible; repair or re-download the snapshot "
            "and retry."
        ) from exc


def _flag_embedding_version() -> str | None:
    try:
        return importlib.metadata.version("FlagEmbedding")
    except importlib.metadata.PackageNotFoundError:
        return None


def _to_python(value: Any) -> Any:
    tolist = getattr(value, "tolist", None)
    return tolist() if callable(tolist) else value


def _dense_vectors(result: Any, expected_count: int) -> list[list[float]]:
    if not isinstance(result, dict) or "dense_vecs" not in result:
        raise ValueError("BGE-M3 backend must return a 'dense_vecs' mapping")
    rows = _to_python(result["dense_vecs"])
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ValueError("BGE-M3 dense_vecs must contain one embedding per input")

    # The upstream API removes the batch dimension for a scalar string. Accept
    # that representation for a one-item result while always sending lists.
    if (
        expected_count == 1
        and rows
        and all(
            isinstance(value, numbers.Real) and not isinstance(value, bool)
            for value in rows
        )
    ):
        rows = [rows]
    if len(rows) != expected_count:
        raise ValueError("BGE-M3 must return one embedding per input")

    vectors: list[list[float]] = []
    dimensions: set[int] = set()
    for row in rows:
        row = _to_python(row)
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
            raise ValueError("each dense embedding must be a one-dimensional vector")
        if any(
            isinstance(value, Sequence) and not isinstance(value, (str, bytes))
            for value in row
        ):
            raise ValueError("each dense embedding must be a one-dimensional vector")
        if not row:
            raise ValueError("dense embedding vectors must have a positive dimension")

        vector: list[float] = []
        for value in row:
            if not isinstance(value, numbers.Real) or isinstance(value, bool):
                raise ValueError("dense embedding vectors must contain numeric values")
            numeric_value = float(value)
            if not math.isfinite(numeric_value):
                raise ValueError("dense embedding vectors must contain finite values")
            vector.append(numeric_value)
        dimensions.add(len(vector))
        vectors.append(vector)

    if len(dimensions) != 1:
        raise ValueError("dense embedding vectors must have consistent dimensions")
    return vectors


def _reranker_scores(result: Any, expected_count: int) -> list[float]:
    scores = _to_python(result)
    if isinstance(scores, numbers.Real) and not isinstance(scores, bool):
        scores = [scores]
    if not isinstance(scores, Sequence) or isinstance(scores, (str, bytes)):
        raise ValueError("reranker must return one score per document")
    if len(scores) != expected_count:
        raise ValueError("reranker must return one score per document")

    normalized: list[float] = []
    for score in scores:
        score = _to_python(score)
        if not isinstance(score, numbers.Real) or isinstance(score, bool):
            raise ValueError("reranker scores must be numeric")
        value = float(score)
        if not math.isfinite(value):
            raise ValueError("reranker scores must be finite")
        normalized.append(value)
    return normalized


class BgeM3Embeddings(BaseEmbeddings):
    """Encode queries and passages with a local BGE-M3 model."""

    def __init__(
        self,
        model_path: str | Path,
        backend: Any | None = None,
        *,
        device: str = "cpu",
        batch_size: int = 32,
        query_max_length: int = 512,
        passage_max_length: int = 512,
        revision: str | None = None,
        weight_source: Literal["cached", "downloaded"] | None = None,
    ) -> None:
        super().__init__()
        _validate_model_settings(query_max_length, passage_max_length, weight_source)
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if not device:
            raise ValueError("device must be a non-empty local device name")

        self._model_path = Path(model_path).expanduser()
        self._device = device
        self._query_max_length = query_max_length
        self._passage_max_length = passage_max_length
        self._batch_size = batch_size
        self._embedding_dimension: int | None = None
        if backend is None:
            resolved_path, weight_hashes = _validate_and_hash_model_dir(
                self._model_path
            )
            self._model_path = resolved_path
            backend = self._load_model_backend(
                self._model_path,
                "embedding",
                device=device,
                query_max_length=query_max_length,
                passage_max_length=passage_max_length,
            )
            library_version = _flag_embedding_version()
        else:
            weight_hashes = ()
            library_version = None
        self._backend = backend
        self._metadata = LocalModelMetadata(
            model_id=EMBEDDING_MODEL_ID,
            revision=revision,
            weights_sha256=weight_hashes,
            device=device,
            flag_embedding_version=library_version,
            query_max_length=query_max_length,
            passage_max_length=passage_max_length,
            weight_source=weight_source,
        )

    @property
    def model_path(self) -> Path:
        return self._model_path

    @property
    def metadata(self) -> LocalModelMetadata:
        return self._metadata

    def _load_model_backend(self, model_path: Path, model_kind: str, **kwargs):
        return _load_local_flag_backend(model_path, model_kind, **kwargs)

    def invoke(
        self, text: str | Document | list[str] | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        if isinstance(text, (str, Document)):
            documents = [text if isinstance(text, Document) else Document(content=text)]
            is_query = True
        elif isinstance(text, list):
            documents = [
                item if isinstance(item, Document) else Document(content=item)
                for item in text
            ]
            if any(not isinstance(item, (str, Document)) for item in text):
                raise TypeError(
                    "embedding input lists must contain strings or Documents"
                )
            is_query = False
        else:
            raise TypeError("embedding input must be a string, Document, or list")

        if not documents:
            return []

        input_texts = [document.text for document in documents]
        options = {
            "batch_size": self._batch_size,
            "max_length": (
                self._query_max_length if is_query else self._passage_max_length
            ),
            "return_dense": True,
            "return_sparse": False,
            "return_colbert_vecs": False,
        }
        if is_query:
            raw_embeddings = self._backend.encode_queries(input_texts, **options)
        else:
            raw_embeddings = self._backend.encode_corpus(input_texts, **options)
        vectors = _dense_vectors(raw_embeddings, len(documents))
        dimension = len(vectors[0])
        if (
            self._embedding_dimension is not None
            and self._embedding_dimension != dimension
        ):
            raise ValueError("dense embedding vectors must have consistent dimensions")
        self._embedding_dimension = dimension

        return [
            DocumentWithEmbedding(content=document, embedding=vector)
            for document, vector in zip(documents, vectors)
        ]

    async def ainvoke(
        self, text: str | Document | list[str] | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        return self.invoke(text, *args, **kwargs)


class BgeM3Reranking(BaseReranking):
    """Score query/passage pairs with the local BGE reranker-v2-M3 model."""

    def __init__(
        self,
        model_path: str | Path,
        backend: Any | None = None,
        *,
        device: str = "cpu",
        batch_size: int = 32,
        query_max_length: int = 256,
        passage_max_length: int = 512,
        revision: str | None = None,
        weight_source: Literal["cached", "downloaded"] | None = None,
    ) -> None:
        super().__init__()
        _validate_model_settings(query_max_length, passage_max_length, weight_source)
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if not device:
            raise ValueError("device must be a non-empty local device name")

        self._model_path = Path(model_path).expanduser()
        self._device = device
        self._query_max_length = query_max_length
        self._passage_max_length = passage_max_length
        self._batch_size = batch_size
        if backend is None:
            resolved_path, weight_hashes = _validate_and_hash_model_dir(
                self._model_path
            )
            self._model_path = resolved_path
            backend = self._load_model_backend(
                self._model_path,
                "reranker",
                device=device,
                query_max_length=query_max_length,
                passage_max_length=passage_max_length,
            )
            library_version = _flag_embedding_version()
        else:
            weight_hashes = ()
            library_version = None
        self._backend = backend
        self._metadata = LocalModelMetadata(
            model_id=RERANKER_MODEL_ID,
            revision=revision,
            weights_sha256=weight_hashes,
            device=device,
            flag_embedding_version=library_version,
            query_max_length=query_max_length,
            passage_max_length=passage_max_length,
            weight_source=weight_source,
        )

    @property
    def model_path(self) -> Path:
        return self._model_path

    @property
    def metadata(self) -> LocalModelMetadata:
        return self._metadata

    def _load_model_backend(self, model_path: Path, model_kind: str, **kwargs):
        return _load_local_flag_backend(model_path, model_kind, **kwargs)

    def score_pairs(
        self, query: str, documents: Sequence[Document]
    ) -> tuple[float, ...]:
        """Return validated scores in the same order as the input documents."""
        if not documents:
            return ()
        if not isinstance(query, str):
            raise TypeError("reranker query must be a string")
        if any(not isinstance(document, Document) for document in documents):
            raise TypeError("reranker inputs must be Documents")

        sentence_pairs = [(query, document.text) for document in documents]
        scores = self._backend.compute_score(
            sentence_pairs,
            batch_size=self._batch_size,
            query_max_length=self._query_max_length,
            max_length=self._passage_max_length,
        )
        return tuple(_reranker_scores(scores, len(documents)))

    def run(self, documents: list[Document], query: str) -> list[Document]:
        if not documents:
            return []
        scores = self.score_pairs(query, documents)
        ranked = sorted(
            enumerate(zip(scores, documents)),
            key=lambda item: (-item[1][0], item[0]),
        )
        model_details = {
            "model_id": self._metadata.model_id,
            "revision": self._metadata.revision,
            "query_max_length": self._query_max_length,
            "passage_max_length": self._passage_max_length,
        }
        output = []
        for _input_order, (score, document) in ranked:
            payload = document.to_dict()
            payload["score"] = getattr(document, "score", 0.0)
            payload["retrieval_metadata"] = deepcopy(
                getattr(document, "retrieval_metadata", {}) or {}
            )
            clone = RetrievedDocument(**payload)
            retrieval_metadata = deepcopy(clone.retrieval_metadata or {})
            retrieval_metadata["rerank_score"] = score
            retrieval_metadata["reranker"] = deepcopy(model_details)
            clone.retrieval_metadata = retrieval_metadata
            output.append(clone)
        return output
