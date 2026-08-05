"""Isolated multiprocess worker for prior-store stress tests (Windows spawn-safe)."""

from __future__ import annotations


def mp_prior_store_worker(payload: tuple) -> int:
    path_str, n, won = payload
    from shared.bayesian_prior_store import BayesianPriorStore

    store = BayesianPriorStore(path_str, lock_timeout_sec=60.0)
    for _ in range(n):
        store.update_from_trades(
            [{"won": bool(won), "features": [f"mp={'w' if won else 'l'}"]}]
        )
    return n
