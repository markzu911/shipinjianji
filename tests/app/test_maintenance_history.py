from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server.app as app_module


def test_job_cleanup_removes_only_stale_inactive_job_directories(tmp_path: Path):
    jobs_dir = app_module.jobs_directory()
    history_dir = app_module.history_library_directory() / (
        "history-11111111111111111111111111111111"
    )
    old_id = "11111111-1111-4111-8111-111111111111"
    new_id = "22222222-2222-4222-8222-222222222222"
    active_id = "33333333-3333-4333-8333-333333333333"
    overflow_ids = [
        "44444444-4444-4444-8444-444444444444",
        "55555555-5555-4555-8555-555555555555",
        "66666666-6666-4666-8666-666666666666",
    ]

    def make_job_dir(job_id: str, age_days: float, content: bytes = b"x") -> Path:
        path = jobs_dir / job_id
        path.mkdir(parents=True)
        (path / "source.mp4").write_bytes(content)
        modified_at = app_module.time.time() - age_days * 86400
        app_module.os.utime(path, (modified_at, modified_at))
        return path

    old_dir = make_job_dir(old_id, 9, b"old")
    new_dir = make_job_dir(new_id, 1, b"new")
    active_dir = make_job_dir(active_id, 20, b"active")
    invalid_dir = jobs_dir / "not-a-job-id"
    invalid_dir.mkdir()
    history_dir.mkdir(parents=True)
    (history_dir / "video.mp4").write_bytes(b"history")
    with app_module.JOBS_LOCK:
        app_module.JOBS[active_id] = {"id": active_id, "status": "processing"}
        app_module.JOB_FILES[active_id] = active_dir / "source.mp4"

    preview = app_module.cleanup_job_directories(
        max_age_days=7,
        max_directories=0,
        dry_run=True,
    )

    assert preview["dryRun"] is True
    assert preview["wouldDelete"] == 1
    assert preview["deleted"] == 0
    assert preview["items"][0]["id"] == old_id
    assert preview["items"][0]["reasons"] == ["expired"]
    assert old_dir.exists()

    result = app_module.cleanup_job_directories(
        max_age_days=7,
        max_directories=0,
        dry_run=False,
    )

    assert result["deleted"] == 1
    assert result["freedBytes"] >= len(b"old")
    assert not old_dir.exists()
    assert new_dir.exists()
    assert active_dir.exists()
    assert invalid_dir.exists()
    assert history_dir.exists()

    for index, job_id in enumerate(overflow_ids):
        make_job_dir(job_id, 2 + index, bytes([index]))

    overflow_result = app_module.cleanup_job_directories(
        max_age_days=999,
        max_directories=2,
        dry_run=False,
    )

    deleted_ids = {item["id"] for item in overflow_result["items"]}
    assert deleted_ids == set(overflow_ids[1:])
    assert (jobs_dir / overflow_ids[0]).exists()
    assert active_dir.exists()


def test_job_cleanup_removes_stale_completed_in_memory_job(tmp_path: Path):
    job_id = "abababab-abab-4bab-8bab-abababababab"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True)
    video_path = job_dir / "source.mp4"
    video_path.write_bytes(b"completed")
    old_time = app_module.time.time() - 8 * 86400
    app_module.os.utime(job_dir, (old_time, old_time))
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {"id": job_id, "status": "completed"}
        app_module.JOB_FILES[job_id] = video_path

    result = app_module.cleanup_job_directories(
        max_age_days=7,
        max_directories=0,
    )

    assert result["deleted"] == 1
    assert not job_dir.exists()
    assert job_id not in app_module.JOBS
    assert job_id not in app_module.JOB_FILES


def test_job_cleanup_rechecks_late_snapshot_and_running_transition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "acacacac-acac-4cac-8cac-acacacacacac"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True)
    video_path = job_dir / "source.mp4"
    video_path.write_bytes(b"completed")
    old_time = app_module.time.time() - 8 * 86400
    app_module.os.utime(job_dir, (old_time, old_time))
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {"id": job_id, "status": "completed"}
        app_module.JOB_FILES[job_id] = video_path

    original_size = app_module.directory_size_bytes

    def touch_during_scan(path: Path) -> int:
        size = original_size(path)
        app_module.os.utime(path, None)
        return size

    monkeypatch.setattr(app_module, "directory_size_bytes", touch_during_scan)
    touched = app_module.cleanup_job_directories(
        max_age_days=7,
        max_directories=0,
    )
    assert touched["deleted"] == 0
    assert job_dir.is_dir()

    app_module.os.utime(job_dir, (old_time, old_time))

    def start_work_during_scan(path: Path) -> int:
        size = original_size(path)
        with app_module.JOBS_LOCK:
            app_module.JOBS[job_id]["edit"] = {
                "status": "queued",
                "attemptId": "late-attempt",
            }
        return size

    monkeypatch.setattr(app_module, "directory_size_bytes", start_work_during_scan)
    running = app_module.cleanup_job_directories(
        max_age_days=7,
        max_directories=0,
    )
    assert running["deleted"] == 0
    assert running["protected"] == 1
    assert job_dir.is_dir()


def test_periodic_storage_cleanup_runs_after_interval(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list[bool] = []
    monkeypatch.setattr(
        app_module,
        "run_storage_maintenance",
        lambda: calls.append(True),
    )

    async def exercise() -> None:
        stop_event = asyncio.Event()
        task = asyncio.create_task(
            app_module.periodic_storage_cleanup(stop_event, interval_seconds=0.01)
        )
        for _ in range(50):
            if calls:
                break
            await asyncio.sleep(0.01)
        stop_event.set()
        await task

    asyncio.run(exercise())

    assert calls


def test_job_cleanup_api_supports_preview_and_execution(tmp_path: Path):
    jobs_dir = app_module.jobs_directory()
    old_id = "77777777-7777-4777-8777-777777777777"
    old_dir = jobs_dir / old_id
    old_dir.mkdir(parents=True)
    (old_dir / "source.mp4").write_bytes(b"cleanup")
    old_time = app_module.time.time() - 4 * 86400
    app_module.os.utime(old_dir, (old_time, old_time))

    with TestClient(app_module.app) as client:
        preview_response = client.post(
            "/api/maintenance/jobs/cleanup",
            json={"maxAgeDays": 3, "maxDirectories": 0, "dryRun": True},
        )
        execute_response = client.post(
            "/api/maintenance/jobs/cleanup",
            json={"maxAgeDays": 3, "maxDirectories": 0, "dryRun": False},
        )

    assert preview_response.status_code == 200
    assert preview_response.json()["wouldDelete"] == 1
    assert execute_response.status_code == 200
    assert execute_response.json()["deleted"] == 1
    assert not old_dir.exists()


def test_failed_transcription_preserves_source_for_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True)
    video_path = job_dir / "source.mp4"
    video_path.write_bytes(b"source")
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = {
            "id": job_id,
            "duration": 1.0,
            "status": "queued",
            "error": None,
        }
        app_module.JOB_FILES[job_id] = video_path

    monkeypatch.setattr(
        app_module,
        "extract_audio",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("测试解析失败")
        ),
    )

    app_module.process_job(job_id)

    with app_module.JOBS_LOCK:
        job = app_module.JOBS[job_id]
    assert job["status"] == "failed"
    assert job["error"] == "测试解析失败"
    assert job_dir.is_dir()
    assert video_path.is_file()
    assert (job_dir / "project-state.json").is_file()
    assert app_module.JOB_FILES[job_id] == video_path


def test_history_versions_are_persistent_manageable_and_reusable(
    sample_video: Path,
):
    transcript = {
        "text": "历史版本可以继续编辑。",
        "language": "zh",
        "languageProbability": 0.99,
        "duration": 1.0,
        "mediaDuration": 1.0,
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 1.0,
                "text": "历史版本可以继续编辑。",
                "words": [
                    {"text": "历史版本", "start": 0.0, "end": 0.45},
                    {"text": "可以继续编辑。", "start": 0.45, "end": 1.0},
                ],
            }
        ],
    }
    edited = app_module.save_history_version(
        job_id="source-job",
        kind="edited",
        source_video=sample_video,
        duration=1.0,
        transcript=transcript,
        original_filename="口播原片.mp4",
    )
    art = app_module.save_history_version(
        job_id="source-job",
        kind="art",
        source_video=sample_video,
        duration=1.0,
        transcript=transcript,
        original_filename="口播原片.mp4",
    )

    with app_module.JOBS_LOCK:
        app_module.JOBS.clear()
        app_module.JOB_FILES.clear()

    with TestClient(app_module.app) as client:
        history_response = client.get("/api/history")
        rename_response = client.patch(
            f"/api/history/{edited['id']}",
            json={"name": "客户确认版"},
        )
        video_response = client.get(f"/api/history/{edited['id']}/video")
        thumbnail_response = client.get(
            f"/api/history/{edited['id']}/thumbnail"
        )
        use_response = client.post(f"/api/history/{art['id']}/use")
        reused_job = client.get(
            f"/api/transcriptions/{use_response.json()['id']}"
        )
        delete_response = client.delete(f"/api/history/{edited['id']}")
        remaining_response = client.get("/api/history")

    assert history_response.status_code == 200
    assert history_response.json()["count"] == 2
    assert history_response.json()["editedCount"] == 1
    assert history_response.json()["artCount"] == 1
    assert {item["kind"] for item in history_response.json()["versions"]} == {
        "edited",
        "art",
    }
    assert rename_response.status_code == 200
    assert rename_response.json()["name"] == "客户确认版"
    assert video_response.status_code == 200
    assert video_response.headers["content-type"] == "video/mp4"
    assert thumbnail_response.status_code == 200
    assert thumbnail_response.headers["content-type"] == "image/jpeg"
    assert use_response.status_code == 201
    assert use_response.json()["status"] == "completed"
    assert use_response.json()["historySource"]["id"] == art["id"]
    assert reused_job.json()["result"]["text"] == transcript["text"]
    assert reused_job.json()["result"]["editableSegments"]
    assert delete_response.status_code == 200
    assert not app_module.history_version_directory(edited["id"]).exists()
    assert remaining_response.json()["count"] == 1
    assert remaining_response.json()["versions"][0]["id"] == art["id"]


def test_history_version_uses_custom_name_or_bounded_safe_default(
    sample_video: Path,
):
    transcript = {
        "text": "安全命名。",
        "duration": 1.0,
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 1.0,
                "text": "安全命名。",
                "words": [{"text": "安全命名。", "start": 0.0, "end": 1.0}],
            }
        ],
    }
    custom = app_module.save_history_version(
        job_id="custom-name-job",
        kind="art",
        source_video=sample_video,
        duration=1.0,
        transcript=transcript,
        original_filename="原片.mp4",
        custom_name="  客户确认版  ",
    )
    default = app_module.save_history_version(
        job_id="safe-default-job",
        kind="edited",
        source_video=sample_video,
        duration=1.0,
        transcript=transcript,
        original_filename=f"{'非常长的原视频名称' * 40}.mp4",
    )

    assert custom["name"] == "客户确认版"
    assert 1 <= len(default["name"]) <= 80
    assert "剪辑版" in default["name"]
    assert not any(character in default["name"] for character in '<>:"/\\|?*')


def test_history_limit_keeps_latest_twenty_and_removes_old_directories(
    tmp_path: Path,
):
    records = []
    for index in range(22):
        history_id = f"history-{index:032x}"
        version_dir = app_module.history_version_directory(history_id)
        version_dir.mkdir(parents=True)
        (version_dir / "video.mp4").write_bytes(str(index).encode())
        records.append(
            {
                "id": history_id,
                "name": f"版本 {index}",
                "kind": "composed",
                "duration": 1.0,
                "fileSize": 1,
                "sourceJobId": "source-job",
                "videoFilename": "video.mp4",
                "transcriptFilename": "transcript.json",
                "thumbnailFilename": None,
                "createdAt": f"2026-01-{index + 1:02d}T00:00:00+00:00",
                "updatedAt": f"2026-01-{index + 1:02d}T00:00:00+00:00",
            }
        )
    app_module.save_history_versions_unlocked(records)

    result = app_module.trim_history_versions(max_stored=20)
    retained = app_module.load_history_versions_unlocked()

    assert result["deleted"] == 2
    assert len(retained) == 20
    assert {record["id"] for record in retained} == {
        record["id"] for record in records[2:]
    }
    assert not app_module.history_version_directory(records[0]["id"]).exists()
    assert not app_module.history_version_directory(records[1]["id"]).exists()


def test_missing_job_returns_404():
    with TestClient(app_module.app) as client:
        response = client.get("/api/transcriptions/not-found")

    assert response.status_code == 404
