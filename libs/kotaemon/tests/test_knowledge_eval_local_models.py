"""Synthetic tests for local BGE adapters; no model weights or corpus files."""

from __future__ import annotations

import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

from kotaemon.base import Document, DocumentWithEmbedding

_LOCAL_MODELS_MODULE = "kotaemon.indices.knowledge.evaluation.local_models"
if importlib.util.find_spec(_LOCAL_MODELS_MODULE) is None:
    local_models = None
    BgeM3Embeddings = None
    BgeM3Reranking = None
    LocalModelPaths = None
else:
    from kotaemon.indices.knowledge.evaluation import local_models
    from kotaemon.indices.knowledge.evaluation.local_models import (
        BgeM3Embeddings,
        BgeM3Reranking,
        LocalModelPaths,
    )


def test_local_model_adapters_are_implemented():
    assert local_models is not None


@pytest.fixture(autouse=True)
def _skip_adapter_behavior_until_implemented(request):
    if local_models is None and request.node.name != "test_local_model_adapters_are_implemented":
        pytest.skip("behavior tests run once local BGE adapters exist")


class FakeFlagEmbedding:
    def __init__(self):
        self.query_calls = []
        self.corpus_calls = []
        self.score_calls = []
        self.query_result = None
        self.corpus_result = None
        self.score_result = None

    @staticmethod
    def _vectors(texts):
        return [[float(len(text)), float(len(text) + 1)] for text in texts]

    def encode_queries(self, queries, **kwargs):
        self.query_calls.append((list(queries), kwargs))
        if self.query_result is not None:
            return self.query_result
        return {"dense_vecs": self._vectors(queries)}

    def encode_corpus(self, corpus, **kwargs):
        self.corpus_calls.append((list(corpus), kwargs))
        if self.corpus_result is not None:
            return self.corpus_result
        return {"dense_vecs": self._vectors(corpus)}

    def compute_score(self, sentence_pairs, **kwargs):
        self.score_calls.append((list(sentence_pairs), kwargs))
        if self.score_result is not None:
            return self.score_result
        scores = {
            "low": 0.1,
            "tie-a": 0.5,
            "tie-b": 0.5,
            "high": 0.9,
        }
        values = [scores[passage] for _, passage in sentence_pairs]
        return values[0] if len(values) == 1 else values


@pytest.fixture
def fake_flag_embedding():
    return FakeFlagEmbedding()


def _complete_synthetic_model_dir(root: Path) -> Path:
    root.mkdir()
    (root / "config.json").write_text(json.dumps({"synthetic": True}), encoding="utf-8")
    (root / "tokenizer.json").write_text("{}", encoding="utf-8")
    (root / "model.safetensors").write_bytes(b"synthetic weights")
    return root


def test_preimported_online_hub_runtime_fails_before_backend_constructor():
    probe = textwrap.dedent(
        """
        import json
        import os
        import sys
        import types
        from pathlib import Path

        from huggingface_hub import constants, get_session
        from transformers.utils import hub as transformers_hub

        session = get_session()
        initial_state = {
            "hub_offline": constants.HF_HUB_OFFLINE,
            "transformers_offline": transformers_hub.is_offline_mode(),
            "adapters": sorted({type(adapter).__name__ for adapter in session.adapters.values()}),
        }
        constructor_calls = []

        def constructor(*args, **kwargs):
            constructor_calls.append((args, kwargs))
            return object()

        flag_embedding = types.ModuleType("FlagEmbedding")
        flag_embedding.BGEM3FlagModel = constructor
        flag_embedding.FlagReranker = constructor
        sys.modules["FlagEmbedding"] = flag_embedding

        from kotaemon.indices.knowledge.evaluation.local_models import (
            _load_local_flag_backend,
        )

        try:
            _load_local_flag_backend(
                Path("synthetic-model"),
                "embedding",
                device="cpu",
                query_max_length=8,
                passage_max_length=8,
            )
        except Exception as error:
            error_type = type(error).__name__
            error_message = str(error)
        else:
            error_type = None
            error_message = None

        final_state = {
            "hub_offline": constants.HF_HUB_OFFLINE,
            "transformers_offline": transformers_hub.is_offline_mode(),
            "hub_env": os.environ.get("HF_HUB_OFFLINE"),
            "transformers_env": os.environ.get("TRANSFORMERS_OFFLINE"),
            "adapters": sorted({type(adapter).__name__ for adapter in get_session().adapters.values()}),
        }
        print(json.dumps({
            "initial_state": initial_state,
            "final_state": final_state,
            "constructor_calls": len(constructor_calls),
            "error_type": error_type,
            "error_message": error_message,
        }))
        """
    )
    env = os.environ.copy()
    env.pop("HF_HUB_OFFLINE", None)
    env.pop("TRANSFORMERS_OFFLINE", None)

    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        check=True,
        env=env,
        text=True,
    )
    observed = json.loads(result.stdout)

    assert observed["initial_state"]["hub_offline"] is False
    assert observed["initial_state"]["transformers_offline"] is False
    assert "UniqueRequestIdAdapter" in observed["initial_state"]["adapters"]
    assert observed["final_state"] == {
        "hub_offline": False,
        "transformers_offline": False,
        "hub_env": None,
        "transformers_env": None,
        "adapters": observed["initial_state"]["adapters"],
    }
    assert observed["error_type"] == "RuntimeError"
    assert "fresh offline inference process" in observed["error_message"]
    assert observed["constructor_calls"] == 0


def test_fresh_offline_subprocess_checks_cached_hub_session_before_loading():
    probe = textwrap.dedent(
        """
        import json
        import sys
        import types
        from pathlib import Path

        import huggingface_hub
        from huggingface_hub import constants, get_session
        from huggingface_hub.utils import _http as hub_http
        from transformers.utils import hub as transformers_hub

        session = get_session()
        initial_state = {
            "hub_offline": constants.HF_HUB_OFFLINE,
            "transformers_offline": transformers_hub.is_offline_mode(),
            "adapters": sorted({type(adapter).__name__ for adapter in session.adapters.values()}),
        }
        session_checks = []
        original_get_session = get_session

        def checked_get_session():
            session_checks.append(True)
            return original_get_session()

        huggingface_hub.get_session = checked_get_session
        hub_http.get_session = checked_get_session
        constructor_calls = []

        def constructor(*args, **kwargs):
            constructor_calls.append((args, kwargs))
            return object()

        flag_embedding = types.ModuleType("FlagEmbedding")
        flag_embedding.BGEM3FlagModel = constructor
        flag_embedding.FlagReranker = constructor
        sys.modules["FlagEmbedding"] = flag_embedding

        from kotaemon.indices.knowledge.evaluation.local_models import (
            _load_local_flag_backend,
        )

        try:
            _load_local_flag_backend(
                Path("synthetic-model"),
                "embedding",
                device="cpu",
                query_max_length=8,
                passage_max_length=8,
            )
        except Exception as error:
            error_type = type(error).__name__
            error_message = str(error)
        else:
            error_type = None
            error_message = None

        print(json.dumps({
            "initial_state": initial_state,
            "session_checks": len(session_checks),
            "constructor_calls": len(constructor_calls),
            "error_type": error_type,
            "error_message": error_message,
        }))
        """
    )
    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"

    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        check=True,
        env=env,
        text=True,
    )
    observed = json.loads(result.stdout)

    assert observed["initial_state"]["hub_offline"] is True
    assert observed["initial_state"]["transformers_offline"] is True
    assert set(observed["initial_state"]["adapters"]) == {"OfflineAdapter"}
    assert observed["session_checks"] >= 1
    assert observed["error_type"] is None
    assert observed["constructor_calls"] == 1


def test_corrupt_local_snapshot_load_error_identifies_model_and_path(tmp_path):
    model_dir = _complete_synthetic_model_dir(tmp_path / "corrupt-snapshot")
    probe = textwrap.dedent(
        """
        import json
        import sys
        import types
        from pathlib import Path

        flag_embedding = types.ModuleType("FlagEmbedding")
        constructor_calls = []

        def corrupt_model_constructor(*args, **kwargs):
            constructor_calls.append((args, kwargs))
            raise ValueError("synthetic corrupt tensor payload")

        flag_embedding.BGEM3FlagModel = corrupt_model_constructor
        flag_embedding.FlagReranker = corrupt_model_constructor
        sys.modules["FlagEmbedding"] = flag_embedding

        from kotaemon.indices.knowledge.evaluation.local_models import (
            BgeM3Embeddings,
        )

        try:
            BgeM3Embeddings(model_path=Path(sys.argv[1]))
        except Exception as error:
            cause = error.__cause__
            observed = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "cause_type": type(cause).__name__ if cause is not None else None,
                "cause_message": str(cause) if cause is not None else None,
                "constructor_calls": len(constructor_calls),
            }
        else:
            observed = {
                "error_type": None,
                "error_message": None,
                "cause_type": None,
                "cause_message": None,
                "constructor_calls": len(constructor_calls),
            }

        print(json.dumps(observed))
        """
    )
    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"

    result = subprocess.run(
        [sys.executable, "-c", probe, str(model_dir)],
        capture_output=True,
        check=True,
        env=env,
        text=True,
    )
    observed = json.loads(result.stdout)

    assert observed["error_type"] == "RuntimeError"
    assert "BAAI/bge-m3" in observed["error_message"]
    assert str(model_dir) in observed["error_message"]
    assert "repair" in observed["error_message"].lower()
    assert observed["cause_type"] == "ValueError"
    assert observed["cause_message"] == "synthetic corrupt tensor payload"
    assert observed["constructor_calls"] == 1


def test_scalar_document_is_encoded_as_query_and_keeps_document_fields(
    fake_flag_embedding,
):
    source = Document(
        text="synthetic query",
        doc_id="query-id",
        metadata={"source": "generated"},
    )
    original_metadata = copy.deepcopy(source.metadata)
    embeddings = BgeM3Embeddings(model_path="local-model", backend=fake_flag_embedding)

    (result,) = embeddings.run(source)

    assert isinstance(result, DocumentWithEmbedding)
    assert fake_flag_embedding.query_calls[0][0] == ["synthetic query"]
    assert fake_flag_embedding.corpus_calls == []
    assert result.text == source.text
    assert result.doc_id == source.doc_id
    assert result.metadata == original_metadata
    assert source.metadata == original_metadata


def test_string_list_is_encoded_as_corpus_even_for_one_passage(fake_flag_embedding):
    embeddings = BgeM3Embeddings(model_path="local-model", backend=fake_flag_embedding)

    result = embeddings.run(["synthetic passage"])

    assert len(result) == 1
    assert fake_flag_embedding.query_calls == []
    assert fake_flag_embedding.corpus_calls[0][0] == ["synthetic passage"]
    assert result[0].text == "synthetic passage"


def test_document_list_is_encoded_as_corpus_and_preserves_order_and_fields(
    fake_flag_embedding,
):
    docs = [
        Document(text="first passage", doc_id="first", metadata={"rank": 1}),
        Document(text="second passage", doc_id="second", metadata={"rank": 2}),
    ]
    original_metadata = [copy.deepcopy(doc.metadata) for doc in docs]
    embeddings = BgeM3Embeddings(model_path="local-model", backend=fake_flag_embedding)

    results = embeddings.run(docs)

    assert fake_flag_embedding.corpus_calls[0][0] == [
        "first passage",
        "second passage",
    ]
    assert [item.doc_id for item in results] == ["first", "second"]
    assert [item.metadata for item in results] == original_metadata
    assert [doc.metadata for doc in docs] == original_metadata
    assert all(isinstance(item, DocumentWithEmbedding) for item in results)


def test_empty_embedding_corpus_skips_backend(fake_flag_embedding):
    embeddings = BgeM3Embeddings(model_path="local-model", backend=fake_flag_embedding)

    assert embeddings.run([]) == []
    assert fake_flag_embedding.query_calls == []
    assert fake_flag_embedding.corpus_calls == []


def test_embedding_backend_cardinality_must_match_inputs(fake_flag_embedding):
    fake_flag_embedding.corpus_result = {"dense_vecs": [[1.0, 2.0], [3.0, 4.0]]}
    embeddings = BgeM3Embeddings(model_path="local-model", backend=fake_flag_embedding)

    with pytest.raises(ValueError, match="one embedding per input"):
        embeddings.run(["only one passage"])


@pytest.mark.parametrize(
    ("vectors", "message"),
    [
        ([[1.0, 2.0], [3.0]], "consistent dimensions"),
        ([[[1.0, 2.0]]], "one-dimensional"),
        ([[1.0, math.inf]], "finite"),
        ([[1.0, "2.0"]], "numeric"),
    ],
)
def test_embedding_vectors_must_be_finite_numeric_dense_vectors(
    fake_flag_embedding, vectors, message
):
    fake_flag_embedding.corpus_result = {"dense_vecs": vectors}
    embeddings = BgeM3Embeddings(model_path="local-model", backend=fake_flag_embedding)

    with pytest.raises(ValueError, match=message):
        embeddings.run(["first", "second"] if len(vectors) == 2 else ["only"])


def test_embedding_dimension_stays_consistent_across_query_and_corpus_calls(
    fake_flag_embedding,
):
    embeddings = BgeM3Embeddings(model_path="local-model", backend=fake_flag_embedding)
    fake_flag_embedding.query_result = {"dense_vecs": [[1.0, 2.0]]}
    embeddings.run("synthetic query")
    fake_flag_embedding.corpus_result = {"dense_vecs": [[1.0, 2.0, 3.0]]}

    with pytest.raises(ValueError, match="consistent dimensions"):
        embeddings.run(["synthetic passage"])


def test_empty_rerank_skips_backend(fake_flag_embedding):
    reranker = BgeM3Reranking(model_path="local-model", backend=fake_flag_embedding)

    assert reranker.run([], query="synthetic query") == []
    assert fake_flag_embedding.score_calls == []


def test_bge_reranker_preserves_document_identity_and_stable_ties(
    fake_flag_embedding,
):
    docs = [
        Document(text="low", doc_id="low", metadata={"keep": True}),
        Document(text="tie-a", doc_id="tie-a"),
        Document(text="tie-b", doc_id="tie-b"),
        Document(text="high", doc_id="high"),
    ]
    original_metadata = [copy.deepcopy(doc.metadata) for doc in docs]
    reranker = BgeM3Reranking(model_path="local-model", backend=fake_flag_embedding)

    result = reranker.run(docs, query="synthetic query")

    assert [doc.doc_id for doc in result] == ["high", "tie-a", "tie-b", "low"]
    assert {id(doc) for doc in result} == {id(doc) for doc in docs}
    assert fake_flag_embedding.score_calls[0][0] == [
        ("synthetic query", "low"),
        ("synthetic query", "tie-a"),
        ("synthetic query", "tie-b"),
        ("synthetic query", "high"),
    ]
    assert [doc.metadata for doc in docs] == original_metadata


def test_bge_reranker_accepts_scalar_score_for_one_pair(fake_flag_embedding):
    fake_flag_embedding.score_result = 0.75
    doc = Document(text="only passage", doc_id="only")
    reranker = BgeM3Reranking(model_path="local-model", backend=fake_flag_embedding)

    (result,) = reranker.run([doc], query="synthetic query")

    assert result is doc


@pytest.mark.parametrize(
    ("scores", "message"),
    [([0.5], "one score per document"), ([0.5, math.nan], "finite")],
)
def test_reranker_validates_score_cardinality_and_finiteness(
    fake_flag_embedding, scores, message
):
    fake_flag_embedding.score_result = scores
    docs = [Document(text="first"), Document(text="second")]
    reranker = BgeM3Reranking(model_path="local-model", backend=fake_flag_embedding)

    with pytest.raises(ValueError, match=message):
        reranker.run(docs, query="synthetic query")


def test_local_model_paths_normalize_to_path_values(tmp_path):
    paths = LocalModelPaths(
        embedding_model_dir=str(tmp_path / "embedder"),
        reranker_model_dir=tmp_path / "reranker",
    )

    assert paths.embedding_model_dir == tmp_path / "embedder"
    assert paths.reranker_model_dir == tmp_path / "reranker"
    assert isinstance(paths.embedding_model_dir, Path)
    assert isinstance(paths.reranker_model_dir, Path)


def test_missing_local_weights_fail_before_backend_loading(tmp_path, monkeypatch):
    missing = tmp_path / "missing-model"
    loader_called = False

    def forbidden_loader(*args, **kwargs):
        nonlocal loader_called
        loader_called = True
        raise AssertionError("model loader must not run without local files")

    monkeypatch.setattr(local_models, "_load_local_flag_backend", forbidden_loader)

    with pytest.raises(FileNotFoundError, match="local model directory"):
        BgeM3Embeddings(model_path=missing)
    assert not loader_called


def test_incomplete_local_weights_fail_fast(tmp_path, monkeypatch):
    incomplete = tmp_path / "incomplete"
    incomplete.mkdir()
    (incomplete / "config.json").write_text("{}", encoding="utf-8")
    (incomplete / "tokenizer.json").write_text("{}", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="model weight files"):
        BgeM3Embeddings(model_path=incomplete, backend=None)


def test_missing_unindexed_weight_shard_fails_fast(tmp_path):
    incomplete = tmp_path / "partial-shards"
    incomplete.mkdir()
    (incomplete / "config.json").write_text("{}", encoding="utf-8")
    (incomplete / "tokenizer.json").write_text("{}", encoding="utf-8")
    (incomplete / "model-00001-of-00002.safetensors").write_bytes(b"shard one")

    with pytest.raises(FileNotFoundError, match="missing weight shard"):
        BgeM3Embeddings(model_path=incomplete)


def test_missing_flagembedding_has_actionable_optional_extra_error(tmp_path, monkeypatch):
    model_dir = _complete_synthetic_model_dir(tmp_path / "model")

    def missing_package(*args, **kwargs):
        raise ImportError("Install the optional `local-eval` extra")

    monkeypatch.setattr(local_models, "_load_local_flag_backend", missing_package)

    with pytest.raises(ImportError, match="local-eval"):
        BgeM3Embeddings(model_path=model_dir)
