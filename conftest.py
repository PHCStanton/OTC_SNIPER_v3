"""
Pytest configuration and module path aliasing for OTC_SNIPER workspace.
"""

import sys
import importlib.util
from pathlib import Path

root_dir = Path(__file__).parent.resolve()
data_agent_dir = root_dir / "data-agent"

# Add repository root and data-agent directory to sys.path
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

if str(data_agent_dir) not in sys.path:
    sys.path.insert(0, str(data_agent_dir))

# Handle module alias for hypenated folder data-agent -> data_agent
if "data_agent" not in sys.modules:
    init_file = data_agent_dir / "__init__.py"
    if init_file.exists():
        spec = importlib.util.spec_from_file_location("data_agent", str(init_file))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules["data_agent"] = mod
            spec.loader.exec_module(mod)
