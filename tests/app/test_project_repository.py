from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server.app as app_module
from server import project_repository


def make_repository(tmp_path: Path) -> project_repository.ProjectRepository:
    return project_repository.ProjectRepository(
        data_dir=tmp_path,
        allowed_extensions={".mp4", ".mov"},
        lock=threading.Lock(),
        utc_now=lambda: "2026-08-23T00:00:00+00:00",
    )


def make_project(
    tmp_path: Path,
    job_id: str = "11111111-1111-4111-8111-111111111111",
    *,
    status: str = "completed",
) -> tuple[dict[str, object], Path]:
    job_dir = tmp_path / "jobs" / job_id
    job_dir.mkdir(parents=True)
    source_path = job_dir / "source.mp4"
    source_path.write_bytes(b"source-media")
    job: dict[str, object] = {
        "id": job_id,
        "filename": "测试视频.mp4",
        "fileSize": source_path.stat().st_size,
        "duration": 1.0,
        "status": status,
        "stage": "已完成",
        "progress": 100,
        "result": {"text": "测试", "segments": []},
        "cutDraft": {"schemaVersion": 1, "revision": 7, "splitPoints": []},
        "edit": None,
        "art": None,
        "artSuggestion": None,
        "pictureInPictureImages": [],
        "pictureInPictureVideos": [],
        "pictureInPicture": None,
        "composition": None,
        "error": None,
    }
    return job, source_path


def test_repository_is_independent_atomic_and_uses_shared_app_identity(
    tmp_path: Path,
):
    project_root = Path(__file__).resolve().parents[2]
    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; from server import project_repository; "
                "assert 'server.app' not in sys.modules"
            ),
        ],
        cwd=project_root,
        check=True,
        capture_output=True,
    )
    assert app_module.ProjectRepository is project_repository.ProjectRepository
    assert (
        app_module.PROJECT_REPOSITORY_LOCK
        is project_repository.PROJECT_REPOSITORY_LOCK
    )

    repository = make_repository(tmp_path)
    job, source_path = make_project(tmp_path)
    payload = repository.save(str(job["id"]), source_path, job)
    restored = repository.load(str(job["id"]))

    assert payload["schemaVersion"] == 1
    assert payload["cutDraft"] == {"present": True, "revision": 7}
    assert "cutDraft" not in payload["job"]
    assert restored["job"]["result"]["text"] == "测试"
    assert restored["sourcePath"] == source_path
    assert not list(source_path.parent.glob(".project-state.json.*.tmp"))


def test_repository_snapshot_strips_internal_and_absolute_asset_paths(
    tmp_path: Path,
):
    repository = make_repository(tmp_path)
    job, source_path = make_project(tmp_path)
    job["pictureInPicture"] = {
        "status": "completed",
        "overlays": [
            {
                "assetId": "asset-1",
                "assetPath": str(source_path.parent / "private-asset.png"),
                "assetUrl": "/api/assets/asset-1",
                "cachePath": str(source_path.parent / "private-cache.bin"),
                "authorization": "Bearer must-not-persist",
                "accessToken": "must-not-persist",
                "password": "must-not-persist",
            }
        ],
        "recoveryWarnings": ["runtime-only"],
        "_processHandle": "must-not-persist",
    }

    payload = repository.save(str(job["id"]), source_path, job)

    overlay = payload["job"]["pictureInPicture"]["overlays"][0]
    assert "assetPath" not in overlay
    assert "cachePath" not in overlay
    assert "authorization" not in overlay
    assert "accessToken" not in overlay
    assert "password" not in overlay
    assert overlay["assetUrl"] == "/api/assets/asset-1"
    assert "recoveryWarnings" not in payload["job"]["pictureInPicture"]
    assert "_processHandle" not in payload["job"]["pictureInPicture"]


def test_corrupt_and_unsafe_snapshots_are_diagnostic_and_not_overwritten(
    tmp_path: Path,
):
    repository = make_repository(tmp_path)
    job, source_path = make_project(tmp_path)
    snapshot_path = repository.snapshot_path(str(job["id"]))
    snapshot_path.write_text("{broken", encoding="utf-8")
    original = snapshot_path.read_bytes()

    recovered, failures = repository.discover()

    assert recovered == []
    assert failures == [{"id": job["id"], "error": "任务快照无法读取。"}]
    assert snapshot_path.read_bytes() == original

    snapshot_path.unlink()
    repository.save(str(job["id"]), source_path, job)
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    payload["source"]["filename"] = "../source.mp4"
    snapshot_path.write_text(json.dumps(payload), encoding="utf-8")
    recovered, failures = repository.discover()
    assert recovered == []
    assert failures[0]["id"] == job["id"]
    assert "引用无效" in failures[0]["error"]


def test_snapshot_rejects_unknown_states_and_unsafe_asset_ids(tmp_path: Path):
    repository = make_repository(tmp_path)
    job, source_path = make_project(tmp_path)
    repository.save(str(job["id"]), source_path, job)
    snapshot_path = repository.snapshot_path(str(job["id"]))
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))

    payload["job"]["status"] = "mystery"
    snapshot_path.write_text(json.dumps(payload), encoding="utf-8")
    recovered, failures = repository.discover()
    assert recovered == []
    assert "主任务状态无效" in failures[0]["error"]

    payload["job"]["status"] = "completed"
    payload["job"]["pictureInPictureImages"] = [
        {"id": "../../../outside", "type": "image"}
    ]
    snapshot_path.write_text(json.dumps(payload), encoding="utf-8")
    recovered, failures = repository.discover()
    assert recovered == []
    assert "画中画素材引用无效" in failures[0]["error"]


def test_structurally_corrupt_existing_snapshot_is_never_overwritten(
    tmp_path: Path,
):
    repository = make_repository(tmp_path)
    job, source_path = make_project(tmp_path)
    repository.save(str(job["id"]), source_path, job)
    snapshot_path = repository.snapshot_path(str(job["id"]))
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    payload["source"] = {"filename": "source.mp4"}
    snapshot_path.write_text(json.dumps(payload), encoding="utf-8")
    original = snapshot_path.read_bytes()

    with pytest.raises(
        project_repository.ProjectSnapshotError,
        match="未覆盖原文件",
    ):
        repository.save(str(job["id"]), source_path, job)

    assert snapshot_path.read_bytes() == original


def test_legacy_source_only_recovery_does_not_apply_old_cut_draft(
    tmp_path: Path,
):
    repository = make_repository(tmp_path)
    job_id = "22222222-2222-4222-8222-222222222222"
    job_dir = tmp_path / "jobs" / job_id
    job_dir.mkdir(parents=True)
    source_path = job_dir / "source.mov"
    source_path.write_bytes(b"legacy")
    (job_dir / "cut-draft.json").write_text(
        json.dumps({"revision": 99, "splitPoints": [{"sourceTime": 0.5}]}),
        encoding="utf-8",
    )

    recovered, failures = repository.discover()

    assert failures == []
    assert recovered[0]["legacy"] is True
    assert recovered[0]["job"]["status"] == "interrupted"
    assert recovered[0]["job"]["result"] is None
    assert recovered[0]["job"]["cutDraft"] is None
    assert recovered[0]["sourcePath"] == source_path

    app_module.DATA_DIR = tmp_path
    app_module.restore_projects_from_disk()
    with TestClient(app_module.app) as client:
        response = client.get(f"/api/transcriptions/{job_id}")
    assert response.status_code == 200
    assert response.json()["cutDraft"] is None


def test_concurrent_save_remains_valid_and_can_preserve_retention_mtime(
    tmp_path: Path,
):
    repository = make_repository(tmp_path)
    job, source_path = make_project(tmp_path)
    old_timestamp = 1_700_000_000
    os.utime(source_path.parent, (old_timestamp, old_timestamp))

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = []
        for revision in range(20):
            candidate = dict(job)
            candidate["progress"] = revision
            futures.append(
                executor.submit(
                    repository.save,
                    str(job["id"]),
                    source_path,
                    candidate,
                    None,
                    preserve_directory_mtime=True,
                )
            )
        for future in futures:
            future.result()

    payload = json.loads(
        repository.snapshot_path(str(job["id"])).read_text(encoding="utf-8")
    )
    assert payload["job"]["progress"] in range(20)
    assert int(source_path.parent.stat().st_mtime) == old_timestamp
    assert not list(source_path.parent.glob(".project-state.json.*.tmp"))


def test_restore_projects_projects_running_states_to_interrupted(tmp_path: Path):
    job, source_path = make_project(tmp_path)
    job["edit"] = {
        "status": "processing",
        "attemptId": "old-edit-attempt",
        "stage": "正在剪辑",
        "progress": 50,
    }
    (source_path.parent / "cut-draft.json").write_text(
        json.dumps({"schemaVersion": 1, "revision": 3, "splitPoints": []}),
        encoding="utf-8",
    )
    repository = make_repository(tmp_path)
    repository.save(str(job["id"]), source_path, job)
    app_module.DATA_DIR = tmp_path

    with app_module.JOBS_LOCK:
        app_module.JOBS.clear()
        app_module.JOB_FILES.clear()
    result = app_module.restore_projects_from_disk()

    assert result["restored"] == 1
    with app_module.JOBS_LOCK:
        restored = app_module.JOBS[str(job["id"])]
    assert restored["status"] == "completed"
    assert restored["edit"]["status"] == "interrupted"
    assert restored["edit"]["previousStatus"] == "processing"
    assert restored["cutDraft"]["revision"] == 3
    persisted = repository.load(str(job["id"]))["job"]
    assert persisted["edit"]["status"] == "interrupted"


def test_restore_uses_draft_authority_and_self_heals_snapshot_reference(
    tmp_path: Path,
):
    job, source_path = make_project(tmp_path)
    job["cutDraft"] = {"schemaVersion": 1, "revision": 1, "splitPoints": []}
    repository = make_repository(tmp_path)
    repository.save(str(job["id"]), source_path, job)
    authoritative_draft = {
        "schemaVersion": 1,
        "revision": 9,
        "splitPoints": [{"key": "split-9", "sourceTime": 0.5}],
    }
    (source_path.parent / "cut-draft.json").write_text(
        json.dumps(authoritative_draft),
        encoding="utf-8",
    )
    app_module.DATA_DIR = tmp_path

    result = app_module.restore_projects_from_disk()

    assert result["restored"] == 1
    with app_module.JOBS_LOCK:
        restored = app_module.JOBS[str(job["id"])]
        assert restored["status"] == "completed"
        assert restored["cutDraft"] == authoritative_draft
        assert "cut-draft.json" in restored["recoveryWarnings"][0]
    healed = repository.load(str(job["id"]))
    assert healed["cutDraft"] == {"present": True, "revision": 9}
    assert "recoveryWarnings" not in healed["job"]


def test_restore_downgrades_completed_projection_when_output_is_missing(
    tmp_path: Path,
):
    job, source_path = make_project(tmp_path)
    job["edit"] = {
        "status": "completed",
        "attemptId": "completed-edit-attempt",
        "stage": "剪辑已完成",
        "outputUrl": f"/api/transcriptions/{job['id']}/edited-video",
    }
    repository = make_repository(tmp_path)
    repository.save(str(job["id"]), source_path, job)
    app_module.DATA_DIR = tmp_path

    result = app_module.restore_projects_from_disk()

    assert result["restored"] == 1
    with app_module.JOBS_LOCK:
        restored = app_module.JOBS[str(job["id"])]
        assert restored["status"] == "completed"
        assert restored["edit"]["status"] == "interrupted"
        assert restored["edit"]["outputUrl"] is None
        assert restored["edit"]["retryable"] is True


def test_corrupt_recovery_returns_diagnostic_instead_of_restart_404(
    tmp_path: Path,
):
    job, _source_path = make_project(tmp_path)
    snapshot_path = make_repository(tmp_path).snapshot_path(str(job["id"]))
    snapshot_path.write_text("{broken", encoding="utf-8")
    app_module.DATA_DIR = tmp_path

    result = app_module.restore_projects_from_disk()

    assert result["restored"] == 0
    with TestClient(app_module.app) as client:
        response = client.get(f"/api/transcriptions/{job['id']}")
    assert response.status_code == 409
    assert "任务工程无法恢复" in response.json()["detail"]


def test_output_promotion_releases_jobs_lock_and_cancel_blocks_late_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job, source_path = make_project(tmp_path)
    attempt_id = "active-edit-attempt"
    job["edit"] = {
        "status": "processing",
        "attemptId": attempt_id,
        "stage": "正在剪辑",
    }
    with app_module.JOBS_LOCK:
        app_module.JOBS[str(job["id"])] = job
        app_module.JOB_FILES[str(job["id"])] = source_path

    temporary_path = source_path.parent / ".edited-active-edit-attempt.tmp.mp4"
    output_path = source_path.parent / "edited.mp4"
    temporary_path.write_bytes(b"new-output")
    entered_replace = threading.Event()
    release_replace = threading.Event()
    original_replace = Path.replace

    def controlled_replace(path: Path, target: Path):
        if path == temporary_path:
            assert not app_module.JOBS_LOCK.locked()
            entered_replace.set()
            assert release_replace.wait(timeout=2)
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", controlled_replace)
    promotion = threading.Thread(
        target=app_module.promote_attempt_output,
        args=(
            str(job["id"]),
            attempt_id,
            "edit",
            temporary_path,
            output_path,
        ),
    )
    promotion.start()
    assert entered_replace.wait(timeout=2)
    assert app_module.JOBS_LOCK.acquire(timeout=0.2)
    app_module.JOBS_LOCK.release()

    cancellation = threading.Thread(
        target=app_module.mark_job_cancelled,
        args=(str(job["id"]),),
    )
    cancellation.start()
    release_replace.set()
    promotion.join(timeout=2)
    cancellation.join(timeout=2)

    assert not promotion.is_alive()
    assert not cancellation.is_alive()
    assert output_path.read_bytes() == b"new-output"
    assert not app_module.update_edit_job(
        str(job["id"]),
        expected_attempt_id=attempt_id,
        status="completed",
        outputUrl=f"/api/transcriptions/{job['id']}/edited-video",
    )
    with app_module.JOBS_LOCK:
        assert app_module.JOBS[str(job["id"])]["edit"]["status"] == "cancelled"
    with app_module.JOB_ATTEMPT_LOCKS_GUARD:
        assert str(job["id"]) not in app_module.JOB_ATTEMPT_LOCKS


def test_cancelled_sub_attempts_stay_stale_after_another_task_clears_cancel(
    tmp_path: Path,
):
    job, source_path = make_project(tmp_path)
    suggestion_attempt = "old-suggestion-attempt"
    asset_id = "pip-video-1"
    video_attempt = "old-video-attempt"
    job["artSuggestion"] = {
        "status": "processing",
        "attemptId": suggestion_attempt,
    }
    job["pictureInPictureVideos"] = [
        {
            "id": asset_id,
            "status": "processing",
            "attemptId": video_attempt,
        }
    ]
    with app_module.JOBS_LOCK:
        app_module.JOBS[str(job["id"])] = job
        app_module.JOB_FILES[str(job["id"])] = source_path

    app_module.mark_job_cancelled(str(job["id"]))
    # Starting a different task legitimately clears the job-wide cancellation flag.
    # The cancelled attempt identities must still remain terminal and unusable.
    with app_module.JOBS_LOCK:
        job["cancelRequested"] = False
        job["art"] = {
            "status": "queued",
            "attemptId": "new-art-attempt",
        }

    with pytest.raises(app_module.GenerationCancelledError):
        app_module.check_attempt_active(
            str(job["id"]),
            suggestion_attempt,
            "artSuggestion",
        )
    with pytest.raises(app_module.GenerationCancelledError):
        app_module.check_attempt_active(
            str(job["id"]),
            video_attempt,
            "pictureInPictureVideos",
            asset_id=asset_id,
        )
    assert not app_module.update_art_suggestion_job(
        str(job["id"]),
        expected_attempt_id=suggestion_attempt,
        status="completed",
    )
    assert not app_module.update_picture_in_picture_video_asset(
        str(job["id"]),
        asset_id,
        expected_attempt_id=video_attempt,
        status="completed",
    )


def test_progress_updates_skip_snapshot_io_and_stale_attempt_is_noop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job, source_path = make_project(tmp_path)
    job["status"] = "transcribing"
    job["attemptId"] = "current-attempt"
    with app_module.JOBS_LOCK:
        app_module.JOBS[str(job["id"])] = job
        app_module.JOB_FILES[str(job["id"])] = source_path
    writes: list[str] = []

    def record_write(job_id: str, *args, **kwargs) -> bool:
        assert not app_module.JOBS_LOCK.locked()
        writes.append(job_id)
        return True

    monkeypatch.setattr(app_module, "_persist_snapshot_copy", record_write)
    for progress in range(100):
        assert app_module.update_job(
            str(job["id"]),
            expected_attempt_id="current-attempt",
            progress=progress,
            stage=f"stage-{progress}",
        )
    assert writes == []

    assert not app_module.update_job(
        str(job["id"]),
        expected_attempt_id="stale-attempt",
        status="completed",
        result={"text": "stale"},
    )
    assert app_module.update_job(
        str(job["id"]),
        expected_attempt_id="current-attempt",
        status="failed",
        error="retryable",
    )
    assert writes == [str(job["id"])]
    assert job["status"] == "failed"


def test_retry_reuses_job_and_rejects_duplicate_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job, source_path = make_project(tmp_path, status="failed")
    job["attemptId"] = "failed-attempt"
    job["result"] = None
    job["error"] = "first failure"
    with app_module.JOBS_LOCK:
        app_module.JOBS[str(job["id"])] = job
        app_module.JOB_FILES[str(job["id"])] = source_path
    app_module.persist_job_snapshot(str(job["id"]), raise_on_error=True)
    scheduled: list[tuple[str, str | None]] = []
    monkeypatch.setattr(app_module, "get_asr_api_key", lambda: "test-key")
    monkeypatch.setattr(app_module, "probe_video", lambda _path: 1.25)
    monkeypatch.setattr(
        app_module,
        "process_job",
        lambda job_id, attempt_id=None: scheduled.append((job_id, attempt_id)),
    )

    with TestClient(app_module.app) as client:
        first = client.post(f"/api/transcriptions/{job['id']}/retry")
        second = client.post(f"/api/transcriptions/{job['id']}/retry")

    assert first.status_code == 202
    assert second.status_code == 409
    payload = first.json()
    assert payload["id"] == job["id"]
    assert payload["status"] == "queued"
    assert payload["attemptId"] != "failed-attempt"
    assert scheduled == [(job["id"], payload["attemptId"])]


def test_retry_cleanup_failure_returns_job_to_retryable_failed_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job, source_path = make_project(tmp_path, status="interrupted")
    job["attemptId"] = "interrupted-attempt"
    with app_module.JOBS_LOCK:
        app_module.JOBS[str(job["id"])] = job
        app_module.JOB_FILES[str(job["id"])] = source_path
    app_module.persist_job_snapshot(str(job["id"]), raise_on_error=True)
    monkeypatch.setattr(app_module, "get_asr_api_key", lambda: "test-key")
    monkeypatch.setattr(
        app_module,
        "cleanup_transcription_attempt_artifacts",
        lambda _path: (_ for _ in ()).throw(OSError("cleanup denied")),
    )

    with TestClient(app_module.app) as client:
        response = client.post(f"/api/transcriptions/{job['id']}/retry")

    assert response.status_code == 409
    with app_module.JOBS_LOCK:
        current = app_module.JOBS[str(job["id"])]
        assert current["status"] == "failed"
        assert current["retryable"] is True
        assert current["error"] == "cleanup denied"
