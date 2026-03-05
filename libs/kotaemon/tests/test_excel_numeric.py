import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.api.types import is_numeric_dtype

# Provide dummy modules for loader imports
sys.modules.setdefault("llama_index", types.ModuleType("llama_index"))
sys.modules.setdefault("llama_index.core", types.ModuleType("llama_index.core"))
sys.modules.setdefault(
    "llama_index.core.readers", types.ModuleType("llama_index.core.readers")
)
base_mod: Any = types.ModuleType("llama_index.core.readers.base")
base_mod.BaseReader = object
sys.modules.setdefault("llama_index.core.readers.base", base_mod)

theflow_mod: Any = types.ModuleType("theflow")
theflow_mod.Function = object
theflow_mod.Node = object
theflow_mod.Param = object
theflow_mod.lazy = lambda x: x
sys.modules.setdefault("theflow", theflow_mod)

base_pkg: Any = types.ModuleType("kotaemon.base")


class DummyDocument:
    def __init__(self, text: str, metadata=None, **kwargs):
        self.text = text
        self.metadata = metadata or {}


base_pkg.Document = DummyDocument
sys.modules.setdefault("kotaemon.base", base_pkg)


excel_loader_path = (
    Path(__file__).resolve().parents[2]
    / "kotaemon"
    / "kotaemon"
    / "loaders"
    / "excel_loader.py"
)
spec = importlib.util.spec_from_file_location("excel_loader", excel_loader_path)
assert spec is not None
excel_loader = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(excel_loader)

PandasExcelReader = excel_loader.PandasExcelReader
ExcelReader = excel_loader.ExcelReader


def test_pandas_excel_reader_numeric_columns(monkeypatch):
    df = pd.DataFrame({"num": [1, 2], "txt": ["a", "b"]})

    def fake_read_excel(*args, **kwargs):
        return {"Sheet1": df}

    monkeypatch.setattr(pd, "read_excel", fake_read_excel)

    dropna_calls = []
    orig_dropna = pd.DataFrame.dropna

    def dropna_wrapper(self, *args, **kwargs):
        result = orig_dropna(self, *args, **kwargs)
        dropna_calls.append(result)
        return result

    monkeypatch.setattr(pd.DataFrame, "dropna", dropna_wrapper)

    astype_calls = []
    orig_astype = pd.DataFrame.astype

    def astype_wrapper(self, dtype, *args, **kwargs):
        astype_calls.append(dtype)
        return orig_astype(self, dtype, *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "astype", astype_wrapper)

    reader = PandasExcelReader()
    docs = reader.load_data(Path("dummy.xlsx"))

    assert docs[0].text.strip() == "1 a\n2 b"
    assert not any(dt == str or dt == "str" or dt == "object" for dt in astype_calls)
    assert all(is_numeric_dtype(df_["num"]) for df_ in dropna_calls)


def test_excel_reader_numeric_columns(monkeypatch):
    df1 = pd.DataFrame({"num": [1, 2], "txt": ["a", "b"]})
    df2 = pd.DataFrame({"num": [3, 4], "txt": ["c", "d"]})

    def fake_read_excel(*args, **kwargs):
        return {"Sheet1": df1, "Sheet2": df2}

    monkeypatch.setattr(pd, "read_excel", fake_read_excel)

    dropna_calls = []
    orig_dropna = pd.DataFrame.dropna

    def dropna_wrapper(self, *args, **kwargs):
        result = orig_dropna(self, *args, **kwargs)
        dropna_calls.append(result)
        return result

    monkeypatch.setattr(pd.DataFrame, "dropna", dropna_wrapper)

    astype_calls = []
    orig_astype = pd.DataFrame.astype

    def astype_wrapper(self, dtype, *args, **kwargs):
        astype_calls.append(dtype)
        return orig_astype(self, dtype, *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "astype", astype_wrapper)

    reader = ExcelReader()
    docs = reader.load_data(Path("dummy.xlsx"))

    assert docs[0].text.startswith("(Sheet Sheet1")
    assert not any(dt == str or dt == "str" or dt == "object" for dt in astype_calls)
    assert all(is_numeric_dtype(df_["num"]) for df_ in dropna_calls)
