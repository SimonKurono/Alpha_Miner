"""I/O helpers for ingestion artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def ensure_parent_dir(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def write_json(path: str | Path, payload: dict) -> str:
    target = ensure_parent_dir(path)
    with target.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    return str(target)


def write_jsonl(path: str | Path, rows: Iterable[dict]) -> str:
    target = ensure_parent_dir(path)
    with target.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")
    return str(target)


def read_jsonl(path: str | Path) -> list[dict]:
    target = Path(path)
    if not target.exists():
        return []
    rows: list[dict] = []
    with target.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_table_prefer_parquet(path_without_suffix: str | Path, rows: list[dict]) -> str:
    """Write parquet when pandas+pyarrow are available, otherwise write jsonl.

    Returns the final file path.
    """

    base = Path(path_without_suffix)
    base.parent.mkdir(parents=True, exist_ok=True)

    try:
        import pandas as pd  # type: ignore

        df = pd.DataFrame(rows)
        parquet_path = base.with_suffix(".parquet")
        df.to_parquet(parquet_path, index=False)
        return str(parquet_path)
    except Exception:
        jsonl_path = base.with_suffix(".jsonl")
        return write_jsonl(jsonl_path, rows)
