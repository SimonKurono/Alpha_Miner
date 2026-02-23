from __future__ import annotations

from alpha_miner.tools.interfaces import derive_market_features


def test_derive_market_features_returns_and_market_cap():
    rows = [
        {"symbol": "AAPL", "date": "2024-01-01", "close": 100.0, "volume": 1000},
        {"symbol": "AAPL", "date": "2024-01-02", "close": 110.0, "volume": 1200},
        {"symbol": "AAPL", "date": "2024-01-03", "close": 121.0, "volume": 1300},
        {"symbol": "AAPL", "date": "2024-01-04", "close": 133.1, "volume": 1400},
        {"symbol": "AAPL", "date": "2024-01-05", "close": 146.41, "volume": 1500},
        {"symbol": "AAPL", "date": "2024-01-06", "close": 161.051, "volume": 1600},
    ]

    shares = {"AAPL": 10.0}
    out = derive_market_features(rows, shares)

    assert len(out) == 6
    assert out[0]["returns_1d"] is None
    assert round(out[1]["returns_1d"], 6) == 0.1
    assert round(out[5]["returns_5d"], 6) == round((161.051 / 100.0) - 1.0, 6)
    assert out[2]["market_cap"] == 1210.0
