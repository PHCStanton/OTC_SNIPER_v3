"""Phase 3 autonomy enforcement tests."""
from __future__ import annotations

import unittest

from app.backend.services.auto_ghost import CALIBRATION_TIER_A_FIELDS
from app.backend.services.calibration_autonomy import (
    enforce_milestone,
    guardian_prior_transfer,
    guardian_proposals,
    is_catastrophic,
    parse_autonomy_payload,
)
from app.backend.services.calibration_service import CALIBRATION_LOCKED_FIELDS


class TestCatastrophic(unittest.TestCase):
    def test_twelve_two_wins_is_catastrophic(self):
        self.assertTrue(is_catastrophic(12, 2, 10))
        self.assertTrue(is_catastrophic(12, 0, 12))

    def test_thin_or_healthy_is_not(self):
        self.assertFalse(is_catastrophic(11, 0, 11))
        self.assertFalse(is_catastrophic(12, 3, 9))


class TestParse(unittest.TestCase):
    def test_fenced_json(self):
        text = 'note\n```json\n{"tier_a_changes":[{"field":"bayesian_min_probability","new":0.6,"rationale":"x","evidence_n":12}]}\n```'
        parsed = parse_autonomy_payload(text)
        self.assertEqual(parsed["tier_a_changes"][0]["field"], "bayesian_min_probability")
        self.assertEqual(parsed["tier_a_changes"][0]["new"], 0.6)

    def test_empty_is_safe(self):
        parsed = parse_autonomy_payload("")
        self.assertEqual(parsed["tier_a_changes"], [])


class TestEnforce(unittest.TestCase):
    def _current(self):
        return {
            "bayesian_min_probability": 0.50,
            "manipulation_severity_threshold": 0.35,
            "min_zscore": -2.5,
        }

    def test_locked_fields_rejected(self):
        # R2-4 (M-4): `amount`/`expiration_seconds` are now propose-only via the
        # tier-B re-route — use a genuinely locked internal (mode) here.
        payload = {"tier_a_changes": [{"field": "mode", "new": "calibration", "evidence_n": 12}]}
        verdict = enforce_milestone(
            payload, current=self._current(), locked_fields=set(CALIBRATION_LOCKED_FIELDS),
            settled_wins=0, settled_losses=12, apply_tier_a=True,
        )
        self.assertEqual(verdict["applied"], [])
        self.assertTrue(any(r["reason"] == "locked" for r in verdict["rejected"]))

    def test_tier_b_amount_routed_to_proposals(self):
        """R2-4 (M-4): amount via tier_a_changes is PROPOSE-ONLY (requires_confirm)
        — never auto-applied by Tier A, never rejected as locked."""
        payload = {"tier_a_changes": [{"field": "amount", "new": 5.0, "evidence_n": 12}]}
        verdict = enforce_milestone(
            payload, current=self._current(), locked_fields=set(CALIBRATION_LOCKED_FIELDS),
            settled_wins=0, settled_losses=12, apply_tier_a=True,
        )
        self.assertEqual(verdict["applied"], [])
        self.assertEqual(verdict["rejected"], [])
        self.assertEqual(len(verdict["proposals"]), 1)
        self.assertEqual(verdict["proposals"][0]["field"], "amount")
        self.assertTrue(verdict["proposals"][0]["requires_confirm"])
        self.assertEqual(verdict["proposals"][0]["reason"], "tier_b_route")

    def test_non_catastrophic_demoted_to_proposals(self):
        payload = {"tier_a_changes": [{
            "field": "bayesian_min_probability", "new": 0.60, "rationale": "nudge", "evidence_n": 12,
        }]}
        verdict = enforce_milestone(
            payload, current=self._current(), locked_fields=set(CALIBRATION_LOCKED_FIELDS),
            settled_wins=6, settled_losses=6, apply_tier_a=True,
        )
        self.assertEqual(verdict["applied"], [])
        self.assertEqual(verdict["proposals"][0]["field"], "bayesian_min_probability")
        self.assertFalse(verdict["catastrophic"])

    def test_catastrophic_applies_one_family(self):
        payload = {"tier_a_changes": [
            {"field": "bayesian_min_probability", "new": 0.60, "evidence_n": 12},
            {"field": "min_zscore", "new": -1.0, "evidence_n": 12},
        ]}
        verdict = enforce_milestone(
            payload, current=self._current(), locked_fields=set(CALIBRATION_LOCKED_FIELDS),
            settled_wins=1, settled_losses=11, apply_tier_a=True,
        )
        self.assertTrue(verdict["catastrophic"])
        self.assertEqual(len(verdict["applied"]), 1)
        self.assertEqual(verdict["applied"][0]["field"], "bayesian_min_probability")
        self.assertTrue(any(p.get("demoted") == "one_family_per_milestone" for p in verdict["proposals"]))

    def test_manipulation_raise_only(self):
        payload = {"tier_a_changes": [{
            "field": "manipulation_severity_threshold", "new": 0.20, "evidence_n": 12,
        }]}
        verdict = enforce_milestone(
            payload, current=self._current(), locked_fields=set(CALIBRATION_LOCKED_FIELDS),
            settled_wins=0, settled_losses=12, apply_tier_a=True,
        )
        self.assertTrue(any(r["reason"] == "manipulation_raise_only" for r in verdict["rejected"]))

    def test_regime_blocked_on_first_milestone(self):
        payload = {"tier_a_changes": [{
            "field": "regime_gate_enabled", "new": True, "evidence_n": 12,
        }]}
        verdict = enforce_milestone(
            payload, current=self._current(), locked_fields=set(CALIBRATION_LOCKED_FIELDS),
            settled_wins=0, settled_losses=12, is_first_milestone=True, apply_tier_a=True,
        )
        self.assertTrue(any(r["reason"] == "regime_not_on_first_milestone" for r in verdict["rejected"]))

    def test_tier_b_stays_proposals(self):
        payload = {"tier_b_proposals": [{
            "field": "max_concurrent_trades", "new": 1, "evidence_n": 12,
        }]}
        verdict = enforce_milestone(
            payload, current=self._current(), locked_fields=set(CALIBRATION_LOCKED_FIELDS),
            settled_wins=0, settled_losses=12, apply_tier_a=True,
        )
        self.assertEqual(verdict["applied"], [])
        self.assertEqual(verdict["proposals"][0]["field"], "max_concurrent_trades")

    def test_bayesian_percent_form_clamped(self):
        payload = {"tier_a_changes": [{
            "field": "bayesian_min_probability", "new": 53.5, "evidence_n": 12,
        }]}
        verdict = enforce_milestone(
            payload, current=self._current(), locked_fields=set(CALIBRATION_LOCKED_FIELDS),
            settled_wins=0, settled_losses=12, apply_tier_a=True,
        )
        self.assertEqual(verdict["applied"][0]["new"], 0.90)


class TestGuardian(unittest.TestCase):
    def test_emits_one_family_at_n20_poor_wr(self):
        trades = [{"outcome": "loss", "entry_context": {"regime_label": "CHOPPY"}} for _ in range(18)]
        trades += [{"outcome": "win", "entry_context": {"regime_label": "CHOPPY"}} for _ in range(2)]
        # R2-3 (M-3): a healthy second regime must remain after the drop — an
        # empty whitelist (allow-all) is never proposed.
        trades += [{"outcome": "win", "entry_context": {"regime_label": "TRENDING"}} for _ in range(5)]
        out = guardian_proposals(trades, already_emitted=set())
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["field"], "allowed_regimes")
        self.assertEqual(out[0]["new"], ["TRENDING"])

    def test_skips_already_emitted_and_healthy(self):
        trades = [{"outcome": "win", "entry_context": {"regime_label": "RANGE_BOUND"}} for _ in range(20)]
        self.assertEqual(guardian_proposals(trades, already_emitted=set()), [])

    def test_guardian_never_proposes_allow_all(self):
        """R2-3 (M-3): with ALL settled trades in ONE poorly-performing regime, a
        drop proposal would produce an EMPTY allowed_regimes (= allow-all in
        AutoGhost) — must be skipped entirely."""
        trades = [
            {"outcome": "loss", "entry_context": {"regime_label": "RANGE_BOUND"}}
            for _ in range(25)
        ]
        props = guardian_proposals(trades, already_emitted=set(), min_n=20)
        self.assertEqual(props, [])

    def test_prior_transfer_flags_material_divergence(self):
        trades = [{"outcome": "loss"} for _ in range(8)] + [{"outcome": "win"} for _ in range(2)]
        flags = guardian_prior_transfer(
            trades,
            {"expected_wr": 55.0},
            already_emitted=set(),
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["bucket"], "warm_start:overall")
        self.assertEqual(flags[0]["kind"], "prior_transfer_failure")

    def test_prior_transfer_skips_thin_sample_and_close_wr(self):
        thin = [{"outcome": "loss"} for _ in range(5)]
        self.assertEqual(
            guardian_prior_transfer(thin, {"expected_wr": 55.0}, already_emitted=set()),
            [],
        )
        close = [{"outcome": "win"} for _ in range(11)] + [{"outcome": "loss"} for _ in range(9)]
        self.assertEqual(
            guardian_prior_transfer(close, {"expected_wr": 52.0}, already_emitted=set()),
            [],
        )


class TestTierTablesExist(unittest.TestCase):
    def test_tables_are_non_empty(self):
        self.assertIn("bayesian_min_probability", CALIBRATION_TIER_A_FIELDS)
        self.assertIn("amount", CALIBRATION_LOCKED_FIELDS)


if __name__ == "__main__":
    unittest.main()
