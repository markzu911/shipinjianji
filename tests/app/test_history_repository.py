from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import server.app as app_module
from server import history_repository


def test_history_repository_is_independent_and_uses_runtime_app_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    project_root = Path(__file__).resolve().parents[2]
    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "from server import history_repository; "
                "assert 'server.app' not in sys.modules"
            ),
        ],
        cwd=project_root,
        check=True,
        capture_output=True,
    )

    assert app_module.HistoryRepository is history_repository.HistoryRepository
    assert app_module.HISTORY_KINDS is history_repository.HISTORY_KINDS
    assert (
        app_module.HISTORY_LIBRARY_LOCK
        is history_repository.HISTORY_LIBRARY_LOCK
    )

    runtime_data_dir = tmp_path / "runtime-data"
    monkeypatch.setattr(app_module, "DATA_DIR", runtime_data_dir)
    monkeypatch.setattr(app_module, "HISTORY_MAX_STORED", 1)
    records = [
        {
            "id": f"history-{index:032x}",
            "kind": "edited",
            "videoFilename": "video.mp4",
            "createdAt": f"2026-08-{index + 1:02d}T00:00:00+00:00",
        }
        for index in range(2)
    ]

    app_module.save_history_versions_unlocked(records)
    retained, removed = app_module.enforce_history_limit_unlocked(records)

    assert app_module.history_library_directory() == runtime_data_dir / "history"
    assert app_module.history_manifest_path().is_file()
    assert [record["id"] for record in retained] == [records[1]["id"]]
    assert [record["id"] for record in removed] == [records[0]["id"]]
