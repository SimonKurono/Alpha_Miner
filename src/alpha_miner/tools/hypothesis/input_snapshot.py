"""Load Feature 1 artifacts and build a compact hypothesis input snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from alpha_miner.tools.io_utils import read_jsonl


def _read_json(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Missing JSON artifact: {target}")
    with target.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_table(path: str | Path) -> list[dict[str, Any]]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Missing table artifact: {target}")

    if target.suffix == ".jsonl":
        return read_jsonl(target)

    if target.suffix == ".parquet":
        try:
            import pandas as pd  # type: ignore

            return pd.read_parquet(target).to_dict(orient="records")
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Could not read parquet artifact: {target}") from exc

    raise ValueError(f"Unsupported artifact extension: {target.suffix}")


def load_ingestion_manifest(ingestion_run_id: str) -> dict[str, Any]:
    return _read_json(Path(f"artifacts/{ingestion_run_id}/ingestion_manifest.json"))


def load_ingestion_quality(ingestion_run_id: str) -> dict[str, Any]:
    return _read_json(Path(f"artifacts/{ingestion_run_id}/ingestion_quality.json"))


def _cap_rows_per_symbol(rows: list[dict[str, Any]], max_rows_per_symbol: int) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).upper()
        grouped.setdefault(symbol, []).append(row)

    out: list[dict[str, Any]] = []
    for symbol in sorted(grouped):
        chunk = grouped[symbol]
        chunk.sort(key=lambda r: str(r.get("date", "")))
        out.extend(chunk[-max_rows_per_symbol:])

    return out


def load_hypothesis_input_snapshot(manifest_path: str, max_rows_per_symbol: int = 200) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    market_rows = _read_table(manifest["market_path"])
    text_rows = _read_table(manifest["text_path"])

    market_rows = _cap_rows_per_symbol(market_rows, max_rows_per_symbol=max_rows_per_symbol)
    text_rows = _cap_rows_per_symbol(text_rows, max_rows_per_symbol=max_rows_per_symbol)

    symbols = sorted({str(r.get("symbol", "")).upper() for r in market_rows if r.get("symbol")})

    return {
        "symbols": symbols,
        "market_rows": market_rows,
        "text_rows": text_rows,
        "stats": {
            "market_rows": len(market_rows),
            "text_rows": len(text_rows),
            "symbols": len(symbols),
        },
    }
