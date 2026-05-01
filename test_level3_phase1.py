import unittest

from app.backend.services.market_context import Level2Config, MarketContextEngine
from app.backend.services.regime_classifier import RegimeClassifier
from app.backend.services.streaming import StreamingService


class _AutoGhostStub:
    def update_config(self, **kwargs):
        return {}


def _build_context(**overrides):
    context = {
        "candle_count": 20,
        "adx": 45.0,
        "adx_slope": 0.4,
        "plus_di": 32.0,
        "minus_di": 8.0,
        "cci": 120.0,
        "cci_state": "overbought",
        "atr": 1.0,
        "nearest_structure_atr": 0.2,
        "micro_support": 99.0,
        "micro_resistance": 101.0,
        "reversal_friendly": False,
    }
    context.update(overrides)
    return context


class Level3Phase1Tests(unittest.TestCase):
    def test_market_context_exposes_candle_closed_transition(self) -> None:
        engine = MarketContextEngine(config=Level2Config(candle_seconds=60))

        first = engine.update_tick(1.0000, timestamp=0.0)
        same_candle = engine.update_tick(1.0005, timestamp=30.0)
        next_candle = engine.update_tick(1.0010, timestamp=60.0)
        followup = engine.update_tick(1.0015, timestamp=61.0)

        self.assertFalse(first["candle_closed"])
        self.assertFalse(same_candle["candle_closed"])
        self.assertTrue(next_candle["candle_closed"])
        self.assertFalse(followup["candle_closed"])

    def test_regime_classifier_persistence_reaches_stable_state(self) -> None:
        classifier = RegimeClassifier()
        context = _build_context()

        first = classifier.classify(context)
        second = classifier.classify(context)
        third = classifier.classify(context)

        self.assertEqual(first["regime_label"], "STRONG_MOMENTUM")
        self.assertFalse(first["regime_stable"])
        self.assertEqual(second["regime_persistence"], 2)
        self.assertTrue(third["regime_stable"])
        self.assertEqual(third["regime_persistence"], 3)

    def test_regime_classifier_transitions_with_market_conditions(self) -> None:
        classifier = RegimeClassifier()

        choppy = classifier.classify(_build_context(
            adx=15.0,
            adx_slope=0.0,
            plus_di=16.0,
            minus_di=14.0,
            cci=10.0,
            cci_state="neutral",
            nearest_structure_atr=0.8,
        ))
        pullback = classifier.classify(_build_context(
            adx=25.0,
            adx_slope=0.2,
            plus_di=21.0,
            minus_di=13.0,
            cci=35.0,
            cci_state="neutral",
            nearest_structure_atr=0.2,
        ))
        momentum = classifier.classify(_build_context(
            adx=45.0,
            adx_slope=0.6,
            plus_di=34.0,
            minus_di=9.0,
            cci=120.0,
            cci_state="overbought",
            nearest_structure_atr=0.2,
        ))

        self.assertEqual(choppy["regime_label"], "CHOPPY")
        self.assertEqual(choppy["regime_prior"], "INSUFFICIENT_DATA")
        self.assertEqual(pullback["regime_label"], "TREND_PULLBACK")
        self.assertEqual(pullback["regime_prior"], "CHOPPY")
        self.assertEqual(momentum["regime_label"], "STRONG_MOMENTUM")
        self.assertEqual(momentum["regime_prior"], "TREND_PULLBACK")
        self.assertFalse(momentum["regime_stable"])

    def test_runtime_toggle_clears_level3_cached_state(self) -> None:
        service = object.__new__(StreamingService)
        service.level2_enabled = True
        service.level3_enabled = True
        service._last_regime = {"AUDCAD_otc": {"regime_label": "STRONG_MOMENTUM"}}
        service._regime_classifiers = {"AUDCAD_otc": object()}
        service.auto_ghost = _AutoGhostStub()

        service.update_runtime_settings(level3_enabled=False)
        self.assertEqual(service._last_regime, {})
        self.assertEqual(set(service._regime_classifiers.keys()), {"AUDCAD_otc"})

        service.level3_enabled = False
        service._last_regime = {"AUDCAD_otc": {"regime_label": "RANGE_BOUND"}}
        service._regime_classifiers = {"AUDCAD_otc": object()}

        service.update_runtime_settings(level3_enabled=True)
        self.assertEqual(service._last_regime, {})
        self.assertEqual(service._regime_classifiers, {})

    def test_get_or_create_engines_rebuilds_missing_classifier_for_active_asset(self) -> None:
        service = object.__new__(StreamingService)
        service._oteo_engines = {"AUDCAD_otc": object()}
        service._market_context_engines = {"AUDCAD_otc": object()}
        service._manip_engines = {"AUDCAD_otc": object()}
        service._regime_classifiers = {}

        service._get_or_create_engines("AUDCAD_otc")

        self.assertIn("AUDCAD_otc", service._regime_classifiers)
        self.assertIsInstance(service._regime_classifiers["AUDCAD_otc"], RegimeClassifier)


if __name__ == "__main__":
    unittest.main()
