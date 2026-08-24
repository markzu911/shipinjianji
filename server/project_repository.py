from __future__ import annotations

import copy
import json
import math
import os
import re
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, ContextManager


PROJECT_STATE_FILENAME = "project-state.json"
PROJECT_STATE_SCHEMA_VERSION = 1
PROJECT_REPOSITORY_LOCK = threading.Lock()
_TOP_LEVEL_STATUSES = {
    "queued",
    "extracting",
    "transcribing",
    "processing",
    "completed",
    "failed",
    "cancelled",
    "interrupted",
}
_SUBJOB_STATUSES = {
    "queued",
    "processing",
    "completed",
    "failed",
    "cancelled",
    "interrupted",
}
_SAFE_ASSET_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")

__all__ = (
    "PROJECT_REPOSITORY_LOCK",
    "PROJECT_STATE_FILENAME",
    "PROJECT_STATE_SCHEMA_VERSION",
    "ProjectRepository",
    "ProjectSnapshotError",
)


class ProjectSnapshotError(RuntimeError):
    """Raised when a persisted project snapshot is unsafe or unreadable."""


class ProjectRepository:
    def __init__(
        self,
        *,
        data_dir: Path,
        allowed_extensions: set[str],
        lock: ContextManager[Any],
        utc_now: Callable[[], str],
    ) -> None:
        self.data_dir = data_dir
        self.allowed_extensions = {item.lower() for item in allowed_extensions}
        self.lock = lock
        self.utc_now = utc_now

    def jobs_directory(self) -> Path:
        return self.data_dir / "jobs"

    @staticmethod
    def is_job_id(value: str) -> bool:
        try:
            return str(uuid.UUID(value)) == value.lower()
        except (AttributeError, ValueError):
            return False

    def job_directory(self, job_id: str) -> Path:
        if not self.is_job_id(job_id):
            raise ProjectSnapshotError("无效的转写任务编号。")
        return self.jobs_directory() / job_id

    def snapshot_path(self, job_id: str) -> Path:
        return self.job_directory(job_id) / PROJECT_STATE_FILENAME

    def _validate_source(
        self,
        job_id: str,
        filename: str,
        *,
        expected_size: int | None = None,
        expected_mtime_ns: int | None = None,
    ) -> Path:
        if not filename or Path(filename).name != filename:
            raise ProjectSnapshotError("任务快照的源视频引用无效。")
        if Path(filename).suffix.lower() not in self.allowed_extensions:
            raise ProjectSnapshotError("任务快照的源视频格式无效。")

        job_dir = self.job_directory(job_id)
        if job_dir.is_symlink():
            raise ProjectSnapshotError("任务目录不能是符号链接。")
        source_path = job_dir / filename
        if source_path.is_symlink():
            raise ProjectSnapshotError("任务源视频不能是符号链接。")
        try:
            resolved_jobs_dir = self.jobs_directory().resolve(strict=True)
            resolved_job_dir = job_dir.resolve(strict=True)
            resolved_source = source_path.resolve(strict=True)
            stat = source_path.stat()
        except OSError as exc:
            raise ProjectSnapshotError("任务源视频不存在或无法读取。") from exc
        if (
            resolved_job_dir.parent != resolved_jobs_dir
            or resolved_source.parent != resolved_job_dir
            or not resolved_source.is_file()
        ):
            raise ProjectSnapshotError("任务源视频超出工程目录。")
        if expected_size is not None and stat.st_size != expected_size:
            raise ProjectSnapshotError("任务源视频大小与快照不一致。")
        if expected_mtime_ns is not None and stat.st_mtime_ns != expected_mtime_ns:
            raise ProjectSnapshotError("任务源视频指纹与快照不一致。")
        return source_path

    @staticmethod
    def _json_value(value: Any) -> Any:
        if value is None or isinstance(value, (str, bool, int)):
            return value
        if isinstance(value, float):
            return value if math.isfinite(value) else None
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for key, item in value.items():
                if not isinstance(key, str) or key.startswith("_"):
                    continue
                normalized_key = key.replace("_", "").lower()
                if normalized_key in {
                    "apikey",
                    "authorization",
                    "secret",
                    "password",
                    "credential",
                    "privatekey",
                    "accesstoken",
                    "refreshtoken",
                    "bearertoken",
                    "audiosamples",
                    "pcmsamples",
                    "process",
                    "recoverywarnings",
                } or normalized_key.endswith(("path", "directory")):
                    continue
                normalized = ProjectRepository._json_value(item)
                if normalized is not _SKIP:
                    result[key] = normalized
            return result
        if isinstance(value, (list, tuple)):
            return [
                normalized
                for item in value
                if (normalized := ProjectRepository._json_value(item)) is not _SKIP
            ]
        return _SKIP

    @staticmethod
    def _validate_job_shape(job: dict[str, Any]) -> None:
        if str(job.get("status") or "") not in _TOP_LEVEL_STATUSES:
            raise ProjectSnapshotError("任务快照的主任务状态无效。")
        for key in (
            "edit",
            "art",
            "artSuggestion",
            "pictureInPicture",
            "composition",
        ):
            state = job.get(key)
            if state is not None and (
                not isinstance(state, dict)
                or str(state.get("status") or "") not in _SUBJOB_STATUSES
            ):
                raise ProjectSnapshotError("任务快照的子任务状态无效。")

        seen_asset_ids: set[str] = set()
        for collection_name, status_required in (
            ("pictureInPictureImages", False),
            ("pictureInPictureVideos", True),
        ):
            records = job.get(collection_name, [])
            if not isinstance(records, list):
                raise ProjectSnapshotError("任务快照的画中画素材状态无效。")
            for record in records:
                if not isinstance(record, dict):
                    raise ProjectSnapshotError("任务快照的画中画素材引用无效。")
                asset_id = str(record.get("id") or "")
                if (
                    not _SAFE_ASSET_ID.fullmatch(asset_id)
                    or asset_id in seen_asset_ids
                    or (
                        status_required
                        and str(record.get("status") or "")
                        not in _SUBJOB_STATUSES
                    )
                ):
                    raise ProjectSnapshotError("任务快照的画中画素材引用无效。")
                seen_asset_ids.add(asset_id)

    def _validate_envelope(
        self,
        job_id: str,
        payload: Any,
        *,
        validate_source: bool,
    ) -> tuple[dict[str, Any], Path | None]:
        if not isinstance(payload, dict):
            raise ProjectSnapshotError("任务快照格式无效。")
        if payload.get("schemaVersion") != PROJECT_STATE_SCHEMA_VERSION:
            raise ProjectSnapshotError("任务快照版本不受支持。")
        if payload.get("jobId") != job_id:
            raise ProjectSnapshotError("任务快照与目录编号不一致。")
        source = payload.get("source")
        job = payload.get("job")
        cut_draft = payload.get("cutDraft")
        if not isinstance(source, dict) or not isinstance(job, dict):
            raise ProjectSnapshotError("任务快照缺少必要状态。")
        if str(job.get("id") or "") != job_id:
            raise ProjectSnapshotError("任务状态与目录编号不一致。")
        self._validate_job_shape(job)
        if cut_draft is not None and (
            not isinstance(cut_draft, dict)
            or not isinstance(cut_draft.get("present"), bool)
            or not isinstance(cut_draft.get("revision"), int)
            or int(cut_draft["revision"]) < 0
        ):
            raise ProjectSnapshotError("任务快照的剪辑草稿引用无效。")
        filename = str(source.get("filename") or "")
        try:
            size = int(source["size"])
            mtime_ns = int(source["mtimeNs"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ProjectSnapshotError("任务快照的源视频指纹无效。") from exc
        if size < 0 or mtime_ns < 0:
            raise ProjectSnapshotError("任务快照的源视频指纹无效。")
        source_path = None
        if validate_source:
            source_path = self._validate_source(
                job_id,
                filename,
                expected_size=size,
                expected_mtime_ns=mtime_ns,
            )
        elif not filename or Path(filename).name != filename:
            raise ProjectSnapshotError("任务快照的源视频引用无效。")
        return job, source_path

    def build_snapshot(
        self,
        job_id: str,
        source_path: Path,
        job: dict[str, Any],
        cut_draft: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if str(job.get("id") or "") != job_id:
            raise ProjectSnapshotError("任务快照与目录编号不一致。")
        validated_source = self._validate_source(job_id, source_path.name)
        if source_path.resolve() != validated_source.resolve():
            raise ProjectSnapshotError("任务源视频路径与工程不匹配。")
        stat = validated_source.stat()
        try:
            safe_job = self._json_value(copy.deepcopy(job))
        except Exception as exc:
            raise ProjectSnapshotError("任务状态无法序列化。") from exc
        if not isinstance(safe_job, dict):
            raise ProjectSnapshotError("任务状态无法序列化。")
        persisted_draft = cut_draft
        if persisted_draft is None and isinstance(job.get("cutDraft"), dict):
            persisted_draft = job["cutDraft"]
        safe_job.pop("cutDraft", None)
        try:
            revision = int((persisted_draft or {}).get("revision") or 0)
        except (TypeError, ValueError) as exc:
            raise ProjectSnapshotError("剪辑草稿版本无效，无法保存任务状态。") from exc
        if revision < 0:
            raise ProjectSnapshotError("剪辑草稿版本无效，无法保存任务状态。")
        payload = {
            "schemaVersion": PROJECT_STATE_SCHEMA_VERSION,
            "jobId": job_id,
            "source": {
                "filename": validated_source.name,
                "size": stat.st_size,
                "mtimeNs": stat.st_mtime_ns,
            },
            "job": safe_job,
            "cutDraft": {
                "present": persisted_draft is not None,
                "revision": revision,
            },
            "updatedAt": self.utc_now(),
        }
        try:
            json.dumps(payload, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ProjectSnapshotError("任务状态无法序列化。") from exc
        return payload

    def save(
        self,
        job_id: str,
        source_path: Path,
        job: dict[str, Any],
        cut_draft: dict[str, Any] | None = None,
        *,
        preserve_directory_mtime: bool = False,
    ) -> dict[str, Any]:
        payload = self.build_snapshot(job_id, source_path, job, cut_draft)
        path = self.snapshot_path(job_id)
        with self.lock:
            if not path.parent.is_dir():
                raise ProjectSnapshotError("任务目录已被清理，无法写入快照。")
            if path.is_file():
                try:
                    current = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise ProjectSnapshotError(
                        "任务快照已损坏，未覆盖原文件。"
                    ) from exc
                try:
                    self._validate_envelope(
                        job_id,
                        current,
                        validate_source=True,
                    )
                except ProjectSnapshotError as exc:
                    raise ProjectSnapshotError(
                        "任务快照格式无效，未覆盖原文件。"
                    ) from exc
                current_updated_at = str(
                    current["job"].get("updatedAt")
                    or current.get("updatedAt")
                    or ""
                )
                incoming_updated_at = str(
                    payload["job"].get("updatedAt")
                    or payload.get("updatedAt")
                    or ""
                )
                if current_updated_at > incoming_updated_at:
                    return current
            directory_stat = path.parent.stat()
            temporary_path = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
            try:
                with temporary_path.open("w", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, ensure_ascii=False, indent=2))
                    handle.flush()
                    os.fsync(handle.fileno())
                temporary_path.replace(path)
            finally:
                temporary_path.unlink(missing_ok=True)
                if preserve_directory_mtime and path.parent.is_dir():
                    os.utime(
                        path.parent,
                        ns=(directory_stat.st_atime_ns, directory_stat.st_mtime_ns),
                    )
        return payload

    def load(self, job_id: str) -> dict[str, Any]:
        path = self.snapshot_path(job_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProjectSnapshotError("任务快照无法读取。") from exc
        job, source_path = self._validate_envelope(
            job_id,
            payload,
            validate_source=True,
        )
        assert source_path is not None
        return {
            "job": copy.deepcopy(job),
            "sourcePath": source_path,
            "cutDraft": copy.deepcopy(payload.get("cutDraft") or {}),
            "legacy": False,
        }

    def _load_legacy(self, job_id: str) -> dict[str, Any]:
        job_dir = self.job_directory(job_id)
        candidates = [
            path
            for path in job_dir.iterdir()
            if path.is_file()
            and not path.is_symlink()
            and path.stem.lower() == "source"
            and path.suffix.lower() in self.allowed_extensions
        ]
        if len(candidates) != 1:
            raise ProjectSnapshotError("历史任务缺少唯一可用的源视频。")
        source_path = self._validate_source(job_id, candidates[0].name)
        stat = source_path.stat()
        created_at = datetime.fromtimestamp(stat.st_mtime, UTC).isoformat()
        return {
            "job": {
                "id": job_id,
                "filename": source_path.name,
                "fileSize": stat.st_size,
                "duration": 0.0,
                "status": "interrupted",
                "previousStatus": "unknown",
                "stage": "历史工程需要重新处理",
                "progress": 0,
                "result": None,
                "edit": None,
                "cutDraft": None,
                "art": None,
                "artSuggestion": None,
                "pictureInPictureImages": [],
                "pictureInPictureVideos": [],
                "pictureInPicture": None,
                "composition": None,
                "retryable": True,
                "recoveryKind": "legacy_source_only",
                "error": "服务升级后需要重新分析原视频。",
                "createdAt": created_at,
                "updatedAt": self.utc_now(),
            },
            "sourcePath": source_path,
            "cutDraft": {"present": False, "revision": 0},
            "legacy": True,
        }

    def discover(self) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        jobs_dir = self.jobs_directory()
        if not jobs_dir.is_dir():
            return [], []
        recovered: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []
        for job_dir in sorted(jobs_dir.iterdir(), key=lambda item: item.name):
            if (
                not job_dir.is_dir()
                or job_dir.is_symlink()
                or not self.is_job_id(job_dir.name)
            ):
                continue
            try:
                if (job_dir / PROJECT_STATE_FILENAME).is_file():
                    recovered.append(self.load(job_dir.name))
                else:
                    recovered.append(self._load_legacy(job_dir.name))
            except (OSError, ProjectSnapshotError) as exc:
                failures.append({"id": job_dir.name, "error": str(exc)})
        return recovered, failures


_SKIP = object()
