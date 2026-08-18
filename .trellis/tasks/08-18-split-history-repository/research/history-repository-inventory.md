# History Repository Extraction Inventory

## Baseline

- Branch/HEAD: `develop` / `b39cfa5`
- Production refs: `master == origin/master == 7337413`
- `server/app.py`: 11,902 lines, 442,746 bytes
- Full pytest: 177 nodes
- History/maintenance tests: 9 nodes
- OpenAPI: 48 paths, 34 schemas
- Compact sorted OpenAPI SHA-256: `b5a659422daf83f5c424913b88765a1fa99f2e4363dc001b12d8cb1acd37f505`

## Move Implementation

| Current symbol | Current line | New owner |
| --- | ---: | --- |
| `normalize_history_version_name` | 672 | HistoryRepository/module helper |
| `history_library_directory` | 680 | HistoryRepository |
| `history_manifest_path` | 684 | HistoryRepository |
| `HISTORY_KINDS` | 688 | history_repository module |
| `history_kind_label` | 691 | HistoryRepository/module helper |
| `load_history_versions_unlocked` | 699 | HistoryRepository |
| `save_history_versions_unlocked` | 719 | HistoryRepository |
| `enforce_history_limit_unlocked` | 731 | HistoryRepository |
| `trim_history_versions` | 752 | HistoryRepository |
| `history_version_directory` | 777 | HistoryRepository |
| `public_history_version` | 783 | HistoryRepository |
| `list_history_versions` | 806 | HistoryRepository |
| `find_history_version` | 821 | HistoryRepository |
| `render_history_thumbnail` | 837 | HistoryRepository |
| `save_history_version` | 870 | HistoryRepository |

`server.app` retains thin compatibility functions for all 14 function names and re-exports the module-owned constant/lock.

## Explicit Dependencies

| Dependency | Why | Injection/owner |
| --- | --- | --- |
| `DATA_DIR` | library root | app factory passes current value |
| `HISTORY_MAX_STORED` | default retention cap | app factory passes current value |
| `HISTORY_LIBRARY_LOCK` | manifest serialization | module-owned, app re-export |
| `get_ffmpeg_binary` | thumbnail command | callback injected by app |
| `utc_now` | record timestamps | callback injected by app |
| `datetime.now` | default display name | callback injected by app |
| stdlib file/json/copy/uuid/subprocess | persistence implementation | imported directly by module |

## Stay In server.app

- `periodic_storage_cleanup` and `run_storage_maintenance`
- job directory cleanup and in-memory `JOBS`/`JOB_FILES`
- all `/api/history*` and `/api/transcriptions/*/history` routes
- history-to-job reuse and generation-completion coordination
- FastAPI response mapping and `HTTPException`

## Compatibility Evidence

- `tests/app/conftest.py` monkeypatches `app_module.DATA_DIR` for every app test.
- Existing tests call `app_module.save_history_version`, `history_version_directory`, `save/load_history_versions_unlocked` and `trim_history_versions` directly.
- App and tests contain 64 references to the owned symbol set; thin adapters avoid a broad call-site rewrite.
- No current test monkeypatches the history thumbnail helper or history lock; explicit callback/lock injection still preserves future testability.
