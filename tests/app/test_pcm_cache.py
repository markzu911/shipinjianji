from __future__ import annotations

import os
import threading
import time
from array import array
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from server.pcm_cache import FingerprintPcmCache, ReadOnlyPcmSamples


def test_pcm_cache_reuses_read_only_samples_and_counts_actual_bytes(
    tmp_path: Path,
):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source")
    cache = FingerprintPcmCache()
    decode_calls = 0

    def decode(_path: Path) -> array:
        nonlocal decode_calls
        decode_calls += 1
        return array("h", [10, 20, 30, 40])

    first = cache.get_or_decode(media_path, decode, max_bytes=32)
    second = cache.get_or_decode(media_path, decode, max_bytes=32)

    assert first is second
    assert isinstance(first, ReadOnlyPcmSamples)
    assert list(first) == [10, 20, 30, 40]
    assert decode_calls == 1
    assert cache.snapshot()["totalBytes"] == len(first) * first.itemsize == 8
    with pytest.raises(TypeError):
        first[0] = 99  # type: ignore[index]


def test_pcm_cache_deduplicates_concurrent_decode(tmp_path: Path):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source")
    cache = FingerprintPcmCache()
    decoder_started = threading.Event()
    release_decoder = threading.Event()
    decode_calls = 0
    worker_count = 6

    def decode(_path: Path) -> array:
        nonlocal decode_calls
        decode_calls += 1
        decoder_started.set()
        assert release_decoder.wait(timeout=5)
        return array("h", [1, 2, 3])

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(cache.get_or_decode, media_path, decode, max_bytes=64)
            for _ in range(worker_count)
        ]
        assert decoder_started.wait(timeout=5)
        deadline = time.monotonic() + 5
        while cache.snapshot()["waiterCount"] < worker_count - 1:
            assert time.monotonic() < deadline
            threading.Event().wait(0.005)
        release_decoder.set()
        results = [future.result(timeout=5) for future in futures]

    assert decode_calls == 1
    assert all(result is results[0] for result in results)


def test_pcm_cache_invalidates_changed_size_and_mtime(tmp_path: Path):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"one")
    cache = FingerprintPcmCache()
    decode_calls = 0

    def decode(_path: Path) -> array:
        nonlocal decode_calls
        decode_calls += 1
        return array("h", [decode_calls])

    first = cache.get_or_decode(media_path, decode, max_bytes=64)
    media_path.write_bytes(b"larger")
    second = cache.get_or_decode(media_path, decode, max_bytes=64)
    metadata = media_path.stat()
    os.utime(
        media_path,
        ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 1_000_000_000),
    )
    third = cache.get_or_decode(media_path, decode, max_bytes=64)

    assert [first[0], second[0], third[0]] == [1, 2, 3]
    assert decode_calls == 3
    assert cache.snapshot()["entryCount"] == 1


def test_pcm_cache_evicts_least_recently_used_by_actual_bytes(tmp_path: Path):
    paths = [tmp_path / f"{name}.mp4" for name in "abc"]
    for path in paths:
        path.write_bytes(path.name.encode("ascii"))
    cache = FingerprintPcmCache()
    decode_calls: dict[str, int] = {}

    def decode(path: Path) -> array:
        decode_calls[path.name] = decode_calls.get(path.name, 0) + 1
        return array("h", [1, 2])

    cache.get_or_decode(paths[0], decode, max_bytes=8)
    cache.get_or_decode(paths[1], decode, max_bytes=8)
    cache.get_or_decode(paths[0], decode, max_bytes=8)
    cache.get_or_decode(paths[2], decode, max_bytes=8)
    cache.get_or_decode(paths[1], decode, max_bytes=8)

    assert decode_calls == {"a.mp4": 1, "b.mp4": 2, "c.mp4": 1}
    assert cache.snapshot()["totalBytes"] == 8
    assert cache.snapshot()["entryCount"] == 2


def test_pcm_cache_does_not_store_oversized_or_disabled_entries(tmp_path: Path):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source")
    cache = FingerprintPcmCache()
    decode_calls = 0

    def decode(_path: Path) -> array:
        nonlocal decode_calls
        decode_calls += 1
        return array("h", range(10))

    cache.get_or_decode(media_path, decode, max_bytes=8)
    cache.get_or_decode(media_path, decode, max_bytes=8)
    assert decode_calls == 2
    assert cache.snapshot()["entryCount"] == 0

    cache.get_or_decode(media_path, decode, max_bytes=0)
    cache.get_or_decode(media_path, decode, max_bytes=0)
    assert decode_calls == 4
    assert cache.snapshot()["entryCount"] == 0
    assert cache.snapshot()["maxBytes"] == 0


def test_pcm_cache_failure_wakes_waiters_and_next_call_retries(tmp_path: Path):
    media_path = tmp_path / "source.mp4"
    media_path.write_bytes(b"source")
    cache = FingerprintPcmCache()
    decoder_started = threading.Event()
    release_decoder = threading.Event()
    decode_calls = 0
    worker_count = 4

    def decode(_path: Path) -> array:
        nonlocal decode_calls
        decode_calls += 1
        if decode_calls == 1:
            decoder_started.set()
            assert release_decoder.wait(timeout=5)
            raise RuntimeError("decode failed")
        return array("h", [7, 8])

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(cache.get_or_decode, media_path, decode, max_bytes=64)
            for _ in range(worker_count)
        ]
        assert decoder_started.wait(timeout=5)
        deadline = time.monotonic() + 5
        while cache.snapshot()["waiterCount"] < worker_count - 1:
            assert time.monotonic() < deadline
            threading.Event().wait(0.005)
        release_decoder.set()
        for future in futures:
            with pytest.raises(RuntimeError, match="decode failed"):
                future.result(timeout=5)

    assert decode_calls == 1
    assert cache.snapshot()["entryCount"] == 0
    recovered = cache.get_or_decode(media_path, decode, max_bytes=64)
    reused = cache.get_or_decode(media_path, decode, max_bytes=64)
    assert list(recovered) == [7, 8]
    assert reused is recovered
    assert decode_calls == 2
