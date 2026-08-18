# 历史版本仓库拆分设计

## Boundaries And Ownership

- `server/history_repository.py` 唯一拥有历史版本磁盘模型和操作实现。
- `server/app.py` 继续拥有 FastAPI app、history 路由、job 状态、定时维护协调和生成完成后的调用时机。
- `tests/app/test_history_repository.py` 验证模块边界与动态配置适配；`test_maintenance_history.py` 继续验证完整 API 和文件生命周期。

```text
stdlib: pathlib/json/copy/shutil/subprocess/threading/uuid
                           |
                           v
             server/history_repository.py
                 HistoryRepository
                           |
                           v
server/app.py compatibility adapters -> routes / jobs / maintenance
```

新模块禁止反向导入 `server.app`。API 路由不导入仓库实例，只调用 app 内的兼容函数，避免本任务同时发生路由迁移。

## Repository Configuration

`HistoryRepository` 构造参数：

- `data_dir: Path`
- `max_stored: int`
- `lock: threading.Lock`
- `resolve_ffmpeg: Callable[[str], str]`
- `utc_now: Callable[[], str]`
- `local_now: Callable[[], datetime]`

仓库对象在一次公开操作内固定配置。`server.app._history_repository()` 每次调用时使用当前 app 全局创建对象：

```python
def _history_repository() -> HistoryRepository:
    return HistoryRepository(
        data_dir=DATA_DIR,
        max_stored=HISTORY_MAX_STORED,
        lock=HISTORY_LIBRARY_LOCK,
        resolve_ffmpeg=get_ffmpeg_binary,
        utc_now=utc_now,
        local_now=datetime.now,
    )
```

这不是业务单例：fixture 对 `app.DATA_DIR` 或容量上限的 monkeypatch 会在下一次调用生效。共享锁由 `history_repository.py` 创建并由 app 显式重导出，所有临时仓库对象仍串行访问同一 manifest。

## Public And Compatibility API

模块显式 `__all__` 至少包含：

- `HISTORY_KINDS`
- `HISTORY_LIBRARY_LOCK`
- `HistoryRepository`

仓库公开方法覆盖当前 14 个函数的实现职责。`server.app` 保留同名适配器：

- `normalize_history_version_name`
- `history_library_directory`
- `history_manifest_path`
- `history_kind_label`
- `load_history_versions_unlocked`
- `save_history_versions_unlocked`
- `enforce_history_limit_unlocked`
- `trim_history_versions`
- `history_version_directory`
- `public_history_version`
- `list_history_versions`
- `find_history_version`
- `render_history_thumbnail`
- `save_history_version`

纯格式化函数也经仓库/模块所有者实现，app 不保留第二份正则、kind label 或 URL 投影逻辑。

## Persistence Contract

- library root 保持 `<DATA_DIR>/history`。
- manifest 保持 `manifest.json`，只接受合法 id、kind 和 `video.mp4` 记录。
- manifest 保存继续先写 `.tmp` 再 `replace`。
- version id 保持 `history-` 加 32 位 hex；目录内文件名保持 `video.mp4`、`transcript.json`、`thumbnail.jpg`。
- 视频和 transcript 继续先写临时文件再 replace；任一异常删除整个新版本目录。
- 保留上限先保存裁剪后的 manifest，再删除被淘汰目录。
- 公共 URL、排序和深拷贝行为保持不变。

## Compatibility And Tests

- app 函数签名不变，现有测试和内部调用方无需迁移。
- OpenAPI path/schema 数量和哈希作为路由零变化门禁。
- 聚焦测试用临时 `DATA_DIR` 和 `HISTORY_MAX_STORED = 1` 验证懒配置；同时断言 app 重导出的锁/常量来自新模块。
- 独立进程只导入 `server.history_repository`，断言 `server.app` 未进入 `sys.modules`。
- 维护/历史 9 个现有测试继续覆盖真实短视频、FFmpeg thumbnail、API、复用和清理。

## Tradeoffs

- 选择配置对象而不是大量自由函数参数：一次保存操作涉及目录、上限、锁、时钟和 FFmpeg，集中依赖能避免内部调用漏传或重新读取全局。
- 保留 app 适配器而不立即修改所有 64 处引用：本次目标是建立所有权边界和兼容模板，路由拆分属于下一层任务。
- 不抽象通用 repository 基类：当前只有 history 磁盘协议已稳定；等 ProjectDocument repository 落地后再依据真实共性提取。

## Rollback

无数据迁移。单提交回滚时把 14 个函数实现移回 `server/app.py`，删除模块、适配测试和规范说明即可；历史文件和 manifest 不需要恢复或重写。
