from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, ContextManager, Literal


HISTORY_KINDS = {"edited", "art", "composed"}
HISTORY_LIBRARY_LOCK = threading.Lock()

__all__ = (
    "HISTORY_KINDS",
    "HISTORY_LIBRARY_LOCK",
    "HistoryRepository",
)


class HistoryRepository:
    def __init__(
        self,
        *,
        data_dir: Path,
        max_stored: int,
        lock: ContextManager[Any],
        resolve_ffmpeg: Callable[[str], str],
        utc_now: Callable[[], str],
        local_now: Callable[[], datetime],
    ) -> None:
        self.data_dir = data_dir
        self.max_stored = max_stored
        self.lock = lock
        self.resolve_ffmpeg = resolve_ffmpeg
        self.utc_now = utc_now
        self.local_now = local_now

    def normalize_history_version_name(
        self,
        value: str | None,
        fallback: str = "",
    ) -> str:
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", str(value or ""))
        name = re.sub(r"\s+", " ", name).strip(" .")
        if not name:
            name = fallback
        return name[:80].rstrip(" .")

    def history_library_directory(self) -> Path:
        return self.data_dir / "history"

    def history_manifest_path(self) -> Path:
        return self.history_library_directory() / "manifest.json"

    def history_kind_label(self, kind: str) -> str:
        if kind == "edited":
            return "剪辑版"
        if kind == "composed":
            return "成片"
        return "艺术字版"

    def load_history_versions_unlocked(self) -> list[dict[str, Any]]:
        manifest_path = self.history_manifest_path()
        if not manifest_path.is_file():
            return []
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("剪辑历史索引读取失败。") from exc
        if not isinstance(payload, list):
            raise RuntimeError("剪辑历史索引格式无效。")
        return [
            item
            for item in payload
            if isinstance(item, dict)
            and re.fullmatch(
                r"history-[0-9a-f]{32}",
                str(item.get("id") or ""),
            )
            and item.get("kind") in HISTORY_KINDS
            and str(item.get("videoFilename") or "") == "video.mp4"
        ]

    def save_history_versions_unlocked(
        self,
        records: list[dict[str, Any]],
    ) -> None:
        library_dir = self.history_library_directory()
        library_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.history_manifest_path()
        temporary_path = manifest_path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(manifest_path)

    def enforce_history_limit_unlocked(
        self,
        records: list[dict[str, Any]],
        max_stored: int | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        limit = self.max_stored if max_stored is None else max_stored
        limit = max(0, int(limit))
        if limit == 0 or len(records) <= limit:
            return records, []
        newest_ids = {
            str(record["id"])
            for record in sorted(
                records,
                key=lambda item: str(item.get("createdAt") or ""),
                reverse=True,
            )[:limit]
        }
        retained = [
            record for record in records if str(record["id"]) in newest_ids
        ]
        removed = [
            record
            for record in records
            if str(record["id"]) not in newest_ids
        ]
        return retained, removed

    def trim_history_versions(
        self,
        max_stored: int | None = None,
    ) -> dict[str, Any]:
        with self.lock:
            records = self.load_history_versions_unlocked()
            retained, removed = self.enforce_history_limit_unlocked(
                records,
                max_stored,
            )
            if removed:
                self.save_history_versions_unlocked(retained)
        for record in removed:
            shutil.rmtree(
                self.history_version_directory(str(record["id"])),
                ignore_errors=True,
            )
        return {
            "retained": len(retained),
            "deleted": len(removed),
            "deletedIds": [str(record["id"]) for record in removed],
        }

    def history_version_directory(self, history_id: str) -> Path:
        if not re.fullmatch(r"history-[0-9a-f]{32}", history_id):
            raise ValueError("历史版本编号无效。")
        return self.history_library_directory() / history_id

    def public_history_version(self, record: dict[str, Any]) -> dict[str, Any]:
        history_id = str(record["id"])
        version_dir = self.history_version_directory(history_id)
        thumbnail_filename = str(record.get("thumbnailFilename") or "")
        thumbnail_url = None
        if thumbnail_filename and (version_dir / thumbnail_filename).is_file():
            thumbnail_url = f"/api/history/{history_id}/thumbnail"
        return {
            "id": history_id,
            "name": str(record.get("name") or "未命名版本"),
            "kind": str(record["kind"]),
            "kindLabel": self.history_kind_label(str(record["kind"])),
            "duration": round(float(record.get("duration") or 0), 3),
            "fileSize": int(record.get("fileSize") or 0),
            "sourceJobId": str(record.get("sourceJobId") or ""),
            "videoUrl": f"/api/history/{history_id}/video",
            "downloadUrl": f"/api/history/{history_id}/video?download=true",
            "thumbnailUrl": thumbnail_url,
            "createdAt": record.get("createdAt"),
            "updatedAt": record.get("updatedAt"),
        }

    def list_history_versions(self) -> list[dict[str, Any]]:
        with self.lock:
            records = self.load_history_versions_unlocked()
            available = [
                record
                for record in records
                if (
                    self.history_version_directory(str(record["id"]))
                    / str(record["videoFilename"])
                ).is_file()
            ]
        available.sort(
            key=lambda item: str(item.get("createdAt") or ""),
            reverse=True,
        )
        return [self.public_history_version(record) for record in available]

    def find_history_version(
        self,
        history_id: str,
    ) -> dict[str, Any] | None:
        try:
            self.history_version_directory(history_id)
        except ValueError:
            return None
        with self.lock:
            return next(
                (
                    copy.deepcopy(record)
                    for record in self.load_history_versions_unlocked()
                    if record.get("id") == history_id
                ),
                None,
            )

    def render_history_thumbnail(
        self,
        video_path: Path,
        thumbnail_path: Path,
        duration: float,
    ) -> bool:
        seek_time = min(max(duration * 0.18, 0.08), 2.0)
        command = [
            self.resolve_ffmpeg("ffmpeg"),
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{seek_time:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-vf",
            "scale=360:-2:force_original_aspect_ratio=decrease",
            "-q:v",
            "4",
            str(thumbnail_path),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True)
        except (OSError, subprocess.SubprocessError):
            thumbnail_path.unlink(missing_ok=True)
            return False
        return thumbnail_path.is_file()

    def save_history_version(
        self,
        *,
        job_id: str,
        kind: Literal["edited", "art", "composed"],
        source_video: Path,
        duration: float,
        transcript: dict[str, Any],
        original_filename: str,
        custom_name: str | None = None,
    ) -> dict[str, Any]:
        if not source_video.is_file():
            raise RuntimeError("要保存到剪辑历史的视频文件不存在。")
        if not transcript or not isinstance(transcript.get("segments"), list):
            raise RuntimeError("要保存到剪辑历史的文字时间轴不存在。")

        history_id = f"history-{uuid.uuid4().hex}"
        version_dir = self.history_version_directory(history_id)
        version_dir.mkdir(parents=True, exist_ok=False)
        video_path = version_dir / "video.mp4"
        temporary_video_path = version_dir / ".video.tmp.mp4"
        transcript_path = version_dir / "transcript.json"
        temporary_transcript_path = version_dir / ".transcript.tmp.json"
        thumbnail_path = version_dir / "thumbnail.jpg"
        now = self.utc_now()
        kind_label = self.history_kind_label(kind)
        source_name = self.normalize_history_version_name(
            Path(original_filename).stem,
            "视频",
        )[:32].rstrip(" .")
        display_time = self.local_now().strftime("%m-%d %H-%M")
        default_name = f"{source_name} · {kind_label} {display_time}"
        history_name = self.normalize_history_version_name(
            custom_name,
            default_name,
        )

        try:
            shutil.copy2(source_video, temporary_video_path)
            temporary_video_path.replace(video_path)
            transcript_snapshot = copy.deepcopy(transcript)
            transcript_snapshot["duration"] = round(duration, 3)
            transcript_snapshot["mediaDuration"] = round(duration, 3)
            temporary_transcript_path.write_text(
                json.dumps(transcript_snapshot, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary_transcript_path.replace(transcript_path)
            has_thumbnail = self.render_history_thumbnail(
                video_path,
                thumbnail_path,
                duration,
            )
            record = {
                "id": history_id,
                "name": history_name,
                "kind": kind,
                "duration": round(duration, 3),
                "fileSize": video_path.stat().st_size,
                "sourceJobId": job_id,
                "videoFilename": video_path.name,
                "transcriptFilename": transcript_path.name,
                "thumbnailFilename": thumbnail_path.name if has_thumbnail else None,
                "createdAt": now,
                "updatedAt": now,
            }
            removed_records: list[dict[str, Any]] = []
            with self.lock:
                records = self.load_history_versions_unlocked()
                records.append(record)
                records, removed_records = self.enforce_history_limit_unlocked(
                    records
                )
                self.save_history_versions_unlocked(records)
            for removed_record in removed_records:
                shutil.rmtree(
                    self.history_version_directory(str(removed_record["id"])),
                    ignore_errors=True,
                )
        except Exception:
            shutil.rmtree(version_dir, ignore_errors=True)
            raise
        return self.public_history_version(record)
