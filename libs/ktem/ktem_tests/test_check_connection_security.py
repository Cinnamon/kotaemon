from __future__ import annotations

import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest


class _FakeVendor:
    __module__ = "kotaemon.llms.chats.openai"
    __qualname__ = "ChatOpenAI"

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self, prompt: str) -> str:
        return f"echo:{prompt}:{self.kwargs.get('model', 'default')}"


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch):
    fake_gradio = ModuleType("gradio")
    fake_gradio.Info = MagicMock()
    fake_gradio.Error = Exception
    fake_gradio.SelectData = object
    fake_gradio.update = lambda **kwargs: kwargs

    fake_app = ModuleType("ktem.app")
    fake_app.BasePage = type("BasePage", (), {})

    fake_kotaemon_base = ModuleType("kotaemon.base")
    fake_kotaemon_base.Document = lambda content="": SimpleNamespace(content=content)

    fake_pandas = ModuleType("pandas")

    fake_llms_manager = ModuleType("ktem.llms.manager")
    fake_llms_manager.llms = SimpleNamespace()
    fake_emb_manager = ModuleType("ktem.embeddings.manager")
    fake_emb_manager.embedding_models_manager = SimpleNamespace()
    fake_rerank_manager = ModuleType("ktem.rerankings.manager")
    fake_rerank_manager.reranking_models_manager = SimpleNamespace()

    monkeypatch.setitem(sys.modules, "gradio", fake_gradio)
    monkeypatch.setitem(sys.modules, "pandas", fake_pandas)
    monkeypatch.setitem(sys.modules, "ktem.app", fake_app)
    monkeypatch.setitem(sys.modules, "kotaemon.base", fake_kotaemon_base)
    monkeypatch.setitem(sys.modules, "ktem.llms.manager", fake_llms_manager)
    monkeypatch.setitem(sys.modules, "ktem.embeddings.manager", fake_emb_manager)
    monkeypatch.setitem(sys.modules, "ktem.rerankings.manager", fake_rerank_manager)
    return fake_gradio


def _build_rce_payload() -> str:
    return json.dumps(
        {
            "__type__": "unittest.mock.Mock",
            "return_value": {
                "__type__": "subprocess.check_output",
                "args": ["sh", "-c", "echo PWNED"],
                "text": True,
            },
        }
    )


def test_llm_check_connection_blocks_arbitrary_deserialization(
    isolated_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ktem.llms.ui as llm_ui
    from theflow.utils.modules import deserialize

    fake_manager = SimpleNamespace(
        info=lambda: {
            "my_llm": {
                "name": "my_llm",
                "spec": {
                    "__type__": "kotaemon.llms.ChatOpenAI",
                    "model": "gpt-4o-mini",
                },
                "default": True,
            }
        },
        deserialize=lambda spec: deserialize(
            spec,
            safe=True,
            allowed_modules={
                "kotaemon.llms.ChatOpenAI": _FakeVendor,
                "kotaemon.llms.chats.openai.ChatOpenAI": _FakeVendor,
            },
        ),
    )
    monkeypatch.setattr(llm_ui, "llms", fake_manager)

    page = object.__new__(llm_ui.LLMManagement)
    outputs = list(page.check_connection("my_llm", _build_rce_payload()))
    final_log = outputs[-1]

    assert "PWNED" not in final_log
    assert "Connection failed" in final_log


def test_llm_check_connection_preserves_registered_vendor_type(
    isolated_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ktem.llms.ui as llm_ui
    from theflow.utils.modules import deserialize

    fake_manager = SimpleNamespace(
        info=lambda: {
            "my_llm": {
                "name": "my_llm",
                "spec": {
                    "__type__": "kotaemon.llms.ChatOpenAI",
                    "model": "gpt-4o-mini",
                },
                "default": True,
            }
        },
        deserialize=lambda spec: deserialize(
            spec,
            safe=True,
            allowed_modules={
                "kotaemon.llms.ChatOpenAI": _FakeVendor,
                "kotaemon.llms.chats.openai.ChatOpenAI": _FakeVendor,
            },
        ),
    )
    monkeypatch.setattr(llm_ui, "llms", fake_manager)

    page = object.__new__(llm_ui.LLMManagement)
    outputs = list(page.check_connection("my_llm", "model: gpt-4o\n"))
    final_log = outputs[-1]

    assert "Connection success" in final_log
    assert "echo:Hi:gpt-4o" in final_log


def test_embedding_and_reranking_check_connection_block_arbitrary_deserialization(
    isolated_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ktem.embeddings.ui as emb_ui
    import ktem.rerankings.ui as rerank_ui
    from theflow.utils.modules import deserialize

    fake_emb_manager = SimpleNamespace(
        info=lambda: {
            "my_emb": {
                "name": "my_emb",
                "spec": {"__type__": "kotaemon.embeddings.OpenAIEmbeddings"},
                "default": True,
            }
        },
        deserialize=lambda spec: deserialize(
            spec,
            safe=True,
            allowed_modules={"kotaemon.embeddings.OpenAIEmbeddings": _FakeVendor},
        ),
    )
    fake_rerank_manager = SimpleNamespace(
        info=lambda: {
            "my_rerank": {
                "name": "my_rerank",
                "spec": {"__type__": "kotaemon.rerankings.CohereReranking"},
                "default": True,
            }
        },
        deserialize=lambda spec: deserialize(
            spec,
            safe=True,
            allowed_modules={"kotaemon.rerankings.CohereReranking": _FakeVendor},
        ),
    )
    monkeypatch.setattr(emb_ui, "embedding_models_manager", fake_emb_manager)
    monkeypatch.setattr(rerank_ui, "reranking_models_manager", fake_rerank_manager)

    emb_page = object.__new__(emb_ui.EmbeddingManagement)
    emb_outputs = list(emb_page.check_connection("my_emb", _build_rce_payload()))
    assert "PWNED" not in emb_outputs[-1]
    assert "Connection failed" in emb_outputs[-1]

    rerank_page = object.__new__(rerank_ui.RerankingManagement)
    rerank_outputs = list(
        rerank_page.check_connection("my_rerank", _build_rce_payload())
    )
    assert "PWNED" not in rerank_outputs[-1]
    assert "Connection failed" in rerank_outputs[-1]


def test_manager_allowed_modules_accepts_vendor_and_blocks_arbitrary_classes() -> None:
    from theflow.base import ParamAttr
    from theflow.utils.modules import deserialize

    allowed: dict[str, type] = {"theflow.base.ParamAttr": ParamAttr}
    for vendor in [_FakeVendor]:
        allowed[f"{vendor.__module__}.{vendor.__qualname__}"] = vendor
        top_pkg = ".".join(vendor.__module__.split(".")[:2])
        allowed[f"{top_pkg}.{vendor.__qualname__}"] = vendor

    valid_short = deserialize(
        {"__type__": "kotaemon.llms.ChatOpenAI", "model": "gpt-4o"},
        safe=True,
        allowed_modules=allowed,
    )
    assert isinstance(valid_short, _FakeVendor)
    assert valid_short.kwargs["model"] == "gpt-4o"

    valid_full = deserialize(
        {"__type__": "kotaemon.llms.chats.openai.ChatOpenAI", "model": "gpt-4o-mini"},
        safe=True,
        allowed_modules=allowed,
    )
    assert isinstance(valid_full, _FakeVendor)

    with pytest.raises(ValueError, match="is not allowed"):
        deserialize(
            {
                "__type__": "kotaemon.llms.ChatOpenAI",
                "return_value": {
                    "__type__": "subprocess.check_output",
                    "args": ["sh", "-c", "echo PWNED"],
                },
            },
            safe=True,
            allowed_modules=allowed,
        )
