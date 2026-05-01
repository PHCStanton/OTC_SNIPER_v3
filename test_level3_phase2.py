import unittest

from app.backend.services.market_context import apply_level3_policy


def _oteo_result(**overrides):
    result = {
        "oteo_score": 60.0,
        "recommended": "CALL",
        "confidence": "MEDIUM",
        "actionable": True,
        "level2_suppressed_reason": None,
    }
    result.update(overrides)
    return result


def _market_context(**overrides):
    context = {
        "trend_direction": "up",
    }
    context.update(overrides)
    return context


def _regime(**overrides):
    regime = {
        "regime_label": "RANGE_BOUND",
        "regime_confidence": 80.0,
        "regime_stable": True,
    }
    regime.update(overrides)
    return regime


class Level3Phase2Tests(unittest.TestCase):
    def test_range_bound_boosts_reversal_signal(self) -> None:
        result = apply_level3_policy(_oteo_result(), _market_context(), _regime())

        self.assertGreater(result["oteo_score"], 60.0)
        self.assertEqual(result["level3_suppressed_reason"], None)
        self.assertEqual(result["regime_label"], "RANGE_BOUND")
        self.assertTrue(result["actionable"])

    def test_trend_pullback_suppresses_counter_trend_signal(self) -> None:
        result = apply_level3_policy(
            _oteo_result(recommended="CALL"),
            _market_context(trend_direction="down"),
            _regime(regime_label="TREND_PULLBACK"),
        )

        self.assertFalse(result["actionable"])
        self.assertEqual(result["confidence"], "LOW")
        self.assertIn("counter-trend in pullback regime", result["level3_suppressed_reason"])

    def test_choppy_regime_suppresses_signal(self) -> None:
        result = apply_level3_policy(
            _oteo_result(),
            _market_context(),
            _regime(regime_label="CHOPPY"),
        )

        self.assertFalse(result["actionable"])
        self.assertEqual(result["confidence"], "LOW")
        self.assertIn("choppy regime", result["level3_suppressed_reason"])

    def test_invalid_direction_fails_fast(self) -> None:
        with self.assertRaises(ValueError):
            apply_level3_policy(
                _oteo_result(recommended="SIDEWAYS"),
                _market_context(),
                _regime(),
            )

    def test_non_actionable_signal_keeps_zero_level3_adjustment(self) -> None:
        result = apply_level3_policy(
            _oteo_result(actionable=False),
            _market_context(),
            _regime(regime_label="BREAKOUT"),
        )

        self.assertEqual(result["level3_score_adjustment"], 0.0)
        self.assertIsNone(result["level3_suppressed_reason"])
        self.assertFalse(result["actionable"])


if __name__ == "__main__":
    unittest.main()
