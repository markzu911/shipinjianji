from __future__ import annotations

import threading
from array import array
from collections import OrderedDict
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, overload


@dataclass(frozen=True)
class PcmMediaFingerprint:
    resolved_path: str
    size: int
    mtime_ns: int


class ReadOnlyPcmSamples(Sequence[int]):
    """A shared PCM buffer that exposes sequence reads but no mutation API."""

    __slots__ = ("_samples",)

    def __init__(self, samples: array) -> None:
        self._samples = samples

    @overload
    def __getitem__(self, index: int) -> int: ...

    @overload
    def __getitem__(self, index: slice) -> array: ...

    def __getitem__(self, index: int | slice) -> int | array:
        return self._samples[index]

    def __iter__(self) -> Iterator[int]:
        return iter(self._samples)

    def __len__(self) -> int:
        return len(self._samples)

    @property
    def itemsize(self) -> int:
        return self._samples.itemsize


@dataclass
class _CacheEntry:
    samples: ReadOnlyPcmSamples
    byte_size: int


@dataclass
class _InFlightDecode:
    event: threading.Event = field(default_factory=threading.Event)
    result: ReadOnlyPcmSamples | None = None
    error: BaseException | None = None
    waiter_count: int = 0


class FingerprintPcmCache:
    """Thread-safe byte-bounded LRU with one decoder owner per media fingerprint."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: OrderedDict[PcmMediaFingerprint, _CacheEntry] = OrderedDict()
        self._in_flight: dict[PcmMediaFingerprint, _InFlightDecode] = {}
        self._total_bytes = 0
        self._max_bytes = 0

    @staticmethod
    def _resolved_path(media_path: Path) -> Path:
        return Path(media_path).resolve()

    @classmethod
    def _fingerprint(cls, media_path: Path) -> tuple[Path, PcmMediaFingerprint]:
        resolved_path = cls._resolved_path(media_path)
        metadata = resolved_path.stat()
        return resolved_path, PcmMediaFingerprint(
            resolved_path=str(resolved_path),
            size=metadata.st_size,
            mtime_ns=metadata.st_mtime_ns,
        )

    def _remove_entry_unlocked(self, key: PcmMediaFingerprint) -> None:
        entry = self._entries.pop(key, None)
        if entry is not None:
            self._total_bytes -= entry.byte_size

    def _set_budget_unlocked(self, max_bytes: int) -> None:
        self._max_bytes = max_bytes
        while self._entries and self._total_bytes > max_bytes:
            _, entry = self._entries.popitem(last=False)
            self._total_bytes -= entry.byte_size

    def _remove_stale_path_entries_unlocked(
        self,
        current_key: PcmMediaFingerprint,
    ) -> None:
        for key in tuple(self._entries):
            if (
                key.resolved_path == current_key.resolved_path
                and key != current_key
            ):
                self._remove_entry_unlocked(key)

    def get_or_decode(
        self,
        media_path: Path,
        decoder: Callable[[Path], array],
        *,
        max_bytes: int,
    ) -> array | ReadOnlyPcmSamples:
        budget = max(0, int(max_bytes))
        resolved_path = self._resolved_path(media_path)
        if budget == 0:
            with self._lock:
                self._set_budget_unlocked(0)
            return decoder(resolved_path)

        resolved_path, key = self._fingerprint(resolved_path)
        with self._lock:
            self._set_budget_unlocked(budget)
            self._remove_stale_path_entries_unlocked(key)
            cached = self._entries.pop(key, None)
            if cached is not None:
                self._entries[key] = cached
                return cached.samples
            in_flight = self._in_flight.get(key)
            owns_decode = in_flight is None
            if in_flight is None:
                in_flight = _InFlightDecode()
                self._in_flight[key] = in_flight
            else:
                in_flight.waiter_count += 1

        if not owns_decode:
            in_flight.event.wait()
            if in_flight.error is not None:
                raise in_flight.error
            if in_flight.result is None:
                raise RuntimeError("PCM decode completed without a result.")
            return in_flight.result

        try:
            decoded = decoder(resolved_path)
            shared_samples = ReadOnlyPcmSamples(decoded)
            byte_size = len(decoded) * decoded.itemsize
        except BaseException as exc:
            with self._lock:
                in_flight.error = exc
                if self._in_flight.get(key) is in_flight:
                    self._in_flight.pop(key, None)
                in_flight.event.set()
            raise

        with self._lock:
            in_flight.result = shared_samples
            if byte_size <= self._max_bytes:
                self._entries[key] = _CacheEntry(shared_samples, byte_size)
                self._total_bytes += byte_size
                self._set_budget_unlocked(self._max_bytes)
            if self._in_flight.get(key) is in_flight:
                self._in_flight.pop(key, None)
            in_flight.event.set()
        return shared_samples

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._total_bytes = 0

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "entryCount": len(self._entries),
                "inFlightCount": len(self._in_flight),
                "waiterCount": sum(
                    item.waiter_count for item in self._in_flight.values()
                ),
                "totalBytes": self._total_bytes,
                "maxBytes": self._max_bytes,
                "fingerprints": tuple(self._entries),
            }
