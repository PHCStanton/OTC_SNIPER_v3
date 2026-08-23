from __future__ import annotations

import time
import pytest
from app.backend.services.htf_directional_bias import HTFDirectionalBiasEngine, HTFCandle
from app.backend.services.market_context import Candle
from app.backend.services.auto_ghost import AutoGhostConfig
from app.backend.services.extensions.bayesian_signal_filter import BayesianSignalFilter


def create_synthetic_1m_candles(count: int = 30, trend: str = "BULLISH", base_price: float = 1.0500) -> list[Candle]:
    candles = []
    base_ts = 1700000100  # Multiple of 300 (5m boundary)
    price = base_price

    for i in range(count):
        step = 0.0005 if trend == "BULLISH" else (-0.0005 if trend == "BEARISH" else 0.0)
        c_open = price
        c_close = price + step
        c_high = max(c_open, c_close) + 0.0002
        c_low = min(c_open, c_close) - 0.0002
        price = c_close

        candles.append(
            Candle(
                start_ts=base_ts + i * 60,
                open=c_open,
                high=c_high,
                low=c_low,
                close=c_close,
            )
        )
    return candles


def test_resample_1m_candles_to_5m():
    engine = HTFDirectionalBiasEngine.get_instance()
    candles_1m = create_synthetic_1m_candles(count=20, trend="BULLISH", base_price=1.1000)
    
    candles_5m = engine.resample_1m_candles(candles_1m, timeframe_minutes=5)
    assert len(candles_5m) == 4
    for c in candles_5m:
        assert isinstance(c, HTFCandle)
        assert c.volume == 5
        assert c.high >= c.low
        assert c.close > c.open  # Bullish upward trend


def test_compute_htf_trend_bullish_and_bearish():
    engine = HTFDirectionalBiasEngine.get_instance()
    
    # Bullish series
    bullish_1m = create_synthetic_1m_candles(count=30, trend="BULLISH")
    bull_res = engine.compute_htf_trend(bullish_1m)
    assert "BULLISH" in bull_res["htf_trend"]
    assert bull_res["trend_5m"] == "BULLISH"
    assert bull_res["trend_strength"] >= 60.0

    # Bearish series
    bearish_1m = create_synthetic_1m_candles(count=30, trend="BEARISH")
    bear_res = engine.compute_htf_trend(bearish_1m)
    assert "BEARISH" in bear_res["htf_trend"]
    assert bear_res["trend_5m"] == "BEARISH"


def test_compute_tick_flow_ratio():
    engine = HTFDirectionalBiasEngine.get_instance()
    now = 1000.0

    # 8 up ticks, 2 down ticks within 60s
    ticks = [
        {"t": now - 50, "p": 1.0000},
        {"t": now - 45, "p": 1.0002},  # UP
        {"t": now - 40, "p": 1.0004},  # UP
        {"t": now - 35, "p": 1.0003},  # DOWN
        {"t": now - 30, "p": 1.0005},  # UP
        {"t": now - 25, "p": 1.0007},  # UP
        {"t": now - 20, "p": 1.0006},  # DOWN
        {"t": now - 15, "p": 1.0008},  # UP
        {"t": now - 10, "p": 1.0010},  # UP
        {"t": now - 5,  "p": 1.0012},  # UP
    ]
    flow = engine.compute_tick_flow_ratio(ticks, window_seconds=60.0, current_ts=now)
    # Total transitions = 9 (7 up, 2 down) -> 7/9 = 77.8%
    assert flow >= 70.0


def test_evaluate_directional_confluence_strong_alignment():
    engine = HTFDirectionalBiasEngine.get_instance()
    bullish_1m = create_synthetic_1m_candles(count=30, trend="BULLISH")
    now = 1000.0
    ticks = [
        {"t": now - 40, "p": 1.0000},
        {"t": now - 30, "p": 1.0005},
        {"t": now - 20, "p": 1.0010},
        {"t": now - 10, "p": 1.0015},
    ]

    res = engine.evaluate_directional_confluence(
        asset="EURUSD_otc",
        direction="CALL",
        candles_1m=bullish_1m,
        recent_ticks=ticks,
        current_ts=now,
    )
    assert res["confluence_status"] == "STRONG_ALIGNMENT"
    assert res["confluence_score"] > 35.0
    assert res["calibrated_bayesian_floor"] == 0.520
    assert res["veto"] is False


def test_evaluate_directional_confluence_divergent_veto():
    engine = HTFDirectionalBiasEngine.get_instance()
    bearish_1m = create_synthetic_1m_candles(count=30, trend="BEARISH")
    now = 1000.0
    # Downward collapsing ticks (0% up ticks)
    ticks = [
        {"t": now - 40, "p": 1.0020},
        {"t": now - 30, "p": 1.0015},
        {"t": now - 20, "p": 1.0010},
        {"t": now - 10, "p": 1.0005},
    ]

    # Proposing a CALL directly into collapsing bearish HTF + zero up tick flow
    res = engine.evaluate_directional_confluence(
        asset="EURUSD_otc",
        direction="CALL",
        candles_1m=bearish_1m,
        recent_ticks=ticks,
        current_ts=now,
    )
    assert res["confluence_status"] == "DIVERGENT"
    assert res["veto"] is True
    assert "Adverse micro tick flow" in res["veto_reason"]


def test_bayesian_floor_defaults():
    config = AutoGhostConfig()
    assert config.bayesian_min_probability == 0.535  # Calibrated within 51%-56%

    bsf = BayesianSignalFilter({})
    assert bsf.min_win_probability == 0.535


def test_ai_pulse_text_regex_asset_extraction():
    import re

    def extract_pulse_signal(text: str, allowed_assets: list[str]) -> dict | None:
        def _normalize(raw: str) -> str | None:
            if not raw:
                return None
            cleaned = raw.strip().rstrip(":,|").strip()
            upper_c = cleaned.upper()
            if upper_c in ("CALL", "PUT", "BUY", "SELL", "CALL_OTC", "PUT_OTC", "TARGET", "WAIT", "FOCUS", "AVOID"):
                return None
            if upper_c.endswith(".OTC"):
                cleaned = cleaned[:-4] + "_otc"
            elif not cleaned.lower().endswith("_otc"):
                cleaned = f"{cleaned}_otc"
            for a in allowed_assets:
                if a.lower() == cleaned.lower():
                    return a
            return cleaned

        call_match = re.search(r'(?:🟢\s*(?:CALL|BUY)?[:\s]+|(?<!\w)CALL[:\s]+)\s*([A-Za-z0-9_]+(?:\.otc|_otc)?)(?:.*?Target:\s*([\d.]+))?(?:.*?Wait:\s*(\d+)m?)?', text, re.IGNORECASE)
        put_match = re.search(r'(?:🔴\s*(?:PUT|SELL)?[:\s]+|(?<!\w)PUT[:\s]+)\s*([A-Za-z0-9_]+(?:\.otc|_otc)?)(?:.*?Target:\s*([\d.]+))?', text, re.IGNORECASE)

        if call_match:
            cand = _normalize(call_match.group(1))
            if cand:
                t_price = float(call_match.group(2)) if call_match.group(2) else None
                w_mins = int(call_match.group(3)) if call_match.group(3) else 1
                return {"asset": cand, "direction": "CALL", "target_price": t_price, "wait_minutes": w_mins}
        if put_match:
            cand = _normalize(put_match.group(1))
            if cand:
                t_price = float(put_match.group(2)) if put_match.group(2) else None
                w_match = re.search(r'Wait:\s*(\d+)m?', text, re.IGNORECASE)
                w_mins = int(w_match.group(1)) if w_match else 1
                return {"asset": cand, "direction": "PUT", "target_price": t_price, "wait_minutes": w_mins}
        return None

    allowed = ["EURUSD_otc", "CADCHF_otc", "GBPJPY_otc", "USDCAD_otc"]

    # Case 1: Standard AI message with emoji, target, and 2m wait
    text1 = "🟢 CALL: USDCAD_otc | Target: 1.3998 | Wait: 2m\n🔴 PUT: CADCHF_otc | Target: 0.8970 | Wait: 1m"
    sig1 = extract_pulse_signal(text1, allowed)
    assert sig1 is not None
    assert sig1["asset"] == "USDCAD_otc"
    assert sig1["direction"] == "CALL"
    assert sig1["target_price"] == 1.3998
    assert sig1["wait_minutes"] == 2

    # Case 2: PUT with 3m wait
    text2 = "🔴 PUT: CADCHF | Target: 0.8970 | Wait: 3m"
    sig2 = extract_pulse_signal(text2, allowed)
    assert sig2 is not None
    assert sig2["asset"] == "CADCHF_otc"
    assert sig2["direction"] == "PUT"
    assert sig2["target_price"] == 0.8970
    assert sig2["wait_minutes"] == 3

    # Case 3: Text with no trade setup
    text3 = "Waiting for more trade results to calibrate Ghost Controller gates. No clear setups."
    sig3 = extract_pulse_signal(text3, allowed)
    assert sig3 is None


def test_compute_tick_flow_ratio_flat_and_empty():
    engine = HTFDirectionalBiasEngine.get_instance()
    now = 5000.0

    # Case 1: Empty or single tick -> 50.0%
    assert engine.compute_tick_flow_ratio([], current_ts=now) == 50.0
    assert engine.compute_tick_flow_ratio([{"t": now, "p": 1.0500}], current_ts=now) == 50.0

    # Case 2: All prices identical (zero directional changes) -> 50.0%
    flat_ticks = [{"t": now - (i * 5), "p": 1.0500} for i in range(10)]
    assert engine.compute_tick_flow_ratio(flat_ticks, current_ts=now) == 50.0


def test_midnight_utc_rollover_resampling():
    engine = HTFDirectionalBiasEngine.get_instance()
    # Timestamps spanning across midnight UTC aligned to 5m boundary
    base_ts = (1700000000 + 86100) // 300 * 300
    candles_1m = []
    for i in range(15):
        candles_1m.append(
            Candle(
                start_ts=base_ts + (i * 60),
                open=1.1000 + (i * 0.0001),
                high=1.1005 + (i * 0.0001),
                low=1.0995 + (i * 0.0001),
                close=1.1002 + (i * 0.0001),
            )
        )

    resampled_5m = engine.resample_1m_candles(candles_1m, timeframe_minutes=5)
    assert len(resampled_5m) == 3
    for c in resampled_5m:
        assert c.volume == 5
        assert c.start_ts % 300 == 0


def test_normalize_otc_asset_symbol_module_utility():
    from app.backend.services.streaming import normalize_otc_asset_symbol

    allowed = {"EURUSD_otc", "GBPUSD_otc", "AUDCAD_otc"}

    # Standard casing & format
    assert normalize_otc_asset_symbol("eurusd_otc", allowed) == "EURUSD_otc"
    assert normalize_otc_asset_symbol("EURUSD.OTC", allowed) == "EURUSD_otc"
    assert normalize_otc_asset_symbol("EURUSD", allowed) == "EURUSD_otc"
    assert normalize_otc_asset_symbol("  AUDCAD_otc:  ", allowed) == "AUDCAD_otc"

    # Reserved tokens rejected
    assert normalize_otc_asset_symbol("CALL") is None
    assert normalize_otc_asset_symbol("PUT") is None
    assert normalize_otc_asset_symbol("BUY") is None
    assert normalize_otc_asset_symbol("SELL") is None
    assert normalize_otc_asset_symbol("CALL_OTC") is None
    assert normalize_otc_asset_symbol("TARGET") is None
    assert normalize_otc_asset_symbol("WAIT") is None
    assert normalize_otc_asset_symbol("FOCUS") is None
    assert normalize_otc_asset_symbol("AVOID") is None
    assert normalize_otc_asset_symbol("") is None
    assert normalize_otc_asset_symbol(None) is None

    # Unlisted assets correctly format with _otc
    assert normalize_otc_asset_symbol("NZDUSD") == "NZDUSD_otc"

