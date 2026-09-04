from __future__ import annotations

import threading
import time
import types
from concurrent.futures import ThreadPoolExecutor

import pytest

from server import funasr_runtime


def test_funasr_import_uses_direct_package_scan_and_restores_pkgutil(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auto_model = object()
    recursive_calls: list[str] = []

    def original_walk_packages(
        _path=None,
        prefix: str = "",
        _onerror=None,
    ):
        recursive_calls.append(prefix)
        return iter([("recursive", prefix)])

    def direct_modules(_path=None, prefix: str = ""):
        return iter([("direct", prefix)])

    def import_module(name: str):
        assert name == "funasr"
        assert list(funasr_runtime.pkgutil.walk_packages([], "funasr.")) == [
            ("direct", "funasr.")
        ]
        assert list(funasr_runtime.pkgutil.walk_packages([], "other.")) == [
            ("recursive", "other.")
        ]
        return types.SimpleNamespace(AutoModel=auto_model)

    monkeypatch.setattr(
        funasr_runtime.pkgutil,
        "walk_packages",
        original_walk_packages,
    )
    monkeypatch.setattr(funasr_runtime.pkgutil, "iter_modules", direct_modules)
    monkeypatch.setattr(funasr_runtime.importlib, "import_module", import_module)

    assert funasr_runtime.load_funasr_auto_model() is auto_model
    assert funasr_runtime.pkgutil.walk_packages is original_walk_packages
    assert recursive_calls == ["other."]


def test_funasr_import_restores_pkgutil_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_walk_packages = funasr_runtime.pkgutil.walk_packages

    def fail_import(_name: str):
        assert funasr_runtime.pkgutil.walk_packages is not original_walk_packages
        raise OSError("blocked optional native dependency")

    monkeypatch.setattr(funasr_runtime.importlib, "import_module", fail_import)

    with pytest.raises(OSError, match="blocked optional native dependency"):
        funasr_runtime.load_funasr_auto_model()

    assert funasr_runtime.pkgutil.walk_packages is original_walk_packages


def test_funasr_import_serializes_global_pkgutil_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_walk_packages = funasr_runtime.pkgutil.walk_packages
    state_lock = threading.Lock()
    active_imports = 0
    maximum_active_imports = 0

    def import_module(name: str):
        nonlocal active_imports, maximum_active_imports
        assert name == "funasr"
        with state_lock:
            active_imports += 1
            maximum_active_imports = max(maximum_active_imports, active_imports)
        try:
            assert funasr_runtime.pkgutil.walk_packages is not original_walk_packages
            time.sleep(0.01)
            return types.SimpleNamespace(AutoModel=object())
        finally:
            with state_lock:
                active_imports -= 1

    monkeypatch.setattr(funasr_runtime.importlib, "import_module", import_module)

    with ThreadPoolExecutor(max_workers=4) as executor:
        models = list(
            executor.map(
                lambda _index: funasr_runtime.load_funasr_auto_model(),
                range(8),
            )
        )

    assert len(models) == 8
    assert maximum_active_imports == 1
    assert funasr_runtime.pkgutil.walk_packages is original_walk_packages
