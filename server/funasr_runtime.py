from __future__ import annotations

import importlib
import pkgutil
import threading
from typing import Any


_IMPORT_LOCK = threading.Lock()


def load_funasr_auto_model() -> Any:
    """Import FunASR without recursively loading unrelated optional models."""
    with _IMPORT_LOCK:
        original_walk_packages = pkgutil.walk_packages

        def walk_packages(
            path: Any = None,
            prefix: str = "",
            onerror: Any = None,
        ) -> Any:
            if prefix.startswith("funasr."):
                return pkgutil.iter_modules(path, prefix)
            return original_walk_packages(path, prefix, onerror)

        pkgutil.walk_packages = walk_packages
        try:
            module = importlib.import_module("funasr")
            return getattr(module, "AutoModel")
        finally:
            pkgutil.walk_packages = original_walk_packages
