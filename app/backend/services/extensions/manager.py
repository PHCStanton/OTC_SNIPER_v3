from __future__ import annotations

import os
import logging
import importlib
from pathlib import Path
from typing import Any, Dict, List, Tuple
from .base import BaseExtension

logger = logging.getLogger(__name__)

class ExtensionManager:
    def __init__(self):
        self._extensions: List[BaseExtension] = []
        self.discover_extensions()

    def discover_extensions(self) -> None:
        """Dynamically discover and instantiate active plugins in the extensions directory."""
        self._extensions.clear()
        
        ext_dir = Path(__file__).resolve().parent
        if not ext_dir.exists():
            return

        for entry in os.listdir(ext_dir):
            if entry.endswith(".py") and entry not in ("base.py", "manager.py", "__init__.py"):
                module_name = entry[:-3]
                try:
                    # Import the plugin module dynamically
                    module = importlib.import_module(f".{module_name}", package="app.backend.services.extensions")
                    
                    # Find all classes that subclass BaseExtension
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BaseExtension)
                            and attr is not BaseExtension
                        ):
                            # Instantiate with default settings
                            instance = attr(settings={})
                            self._extensions.append(instance)
                            logger.info("Successfully registered extension: %s", attr.__name__)
                except Exception as e:
                    logger.error("Failed to load extension module %s: %s", module_name, e, exc_info=True)

    def get_active_extensions(self) -> List[BaseExtension]:
        """Return all registered plugins."""
        return self._extensions
