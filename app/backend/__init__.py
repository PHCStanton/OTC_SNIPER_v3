"""OTC SNIPER v3 backend package."""

# Monorepo root on sys.path so the shared `shared.*` packages
# (utc_time_blocks, bayesian_prior_store, bayesian_protocol, ...) resolve
# regardless of the launch cwd. `python -m start` from `app/` puts only
# `app/` on sys.path, which broke module-level `from shared...` imports
# (session_tracker, ghost_protocol_profiles, kb_health, journal_stats_service).
# Precedent: extensions/bayesian_signal_filter.py:22-24.
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
