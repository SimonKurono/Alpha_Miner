from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def test_streamlit_app_module_loads_without_exceptions():
    pytest.importorskip("streamlit")

    root = Path(__file__).resolve().parents[2]
    app_path = root / "ui" / "streamlit_app.py"
    spec = importlib.util.spec_from_file_location("alpha_miner_streamlit_app", app_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "main")

