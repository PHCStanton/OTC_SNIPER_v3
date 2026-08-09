"""
Entry point for the VPS Data Agent.

Run from anywhere:
    conda activate QuFLX-v2
    python data-agent/start.py

This file guarantees:
  - CWD is set to the monorepo root so all relative paths resolve correctly.
  - sys.path includes the root, data-agent/ and data-agent/src/.
  - vps_server.main() is the single composition root; nothing is duplicated here.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Resolve once — data-agent/ sits one level below the monorepo root.
_DATA_AGENT_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _DATA_AGENT_DIR.parent

# Set CWD to the monorepo root so relative paths in GCPTickSink / DataBridgeAPI
# (e.g. "data-agent/data/ticks_fallback.db") resolve correctly regardless of
# where this script was invoked from.
os.chdir(_ROOT_DIR)

# Ensure all internal imports resolve the same way vps_server.py resolves them.
for _p in [str(_ROOT_DIR), str(_DATA_AGENT_DIR), str(_DATA_AGENT_DIR / "src")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

if __name__ == "__main__":
    import vps_server  # resolves via data-agent/src on sys.path

    vps_server.main()
