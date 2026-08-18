# 测试边界拆分设计

## Boundaries And Ownership

- `tests/app/conftest.py` 只拥有应用测试共享的 `isolated_jobs` 和 `sample_video` fixture。
- `tests/app/test_*.py` 按产品功能域拥有测试；每个原测试函数只迁移到一个模块。
- `tests/test_build_mac_package.py` 保持在 `tests/` 根目录，不继承 `tests/app/conftest.py` 的 autouse fixture。
- `server/`、`web/` 和运行配置不是本任务的修改所有者，Git diff 必须为空。

## Target Structure

```text
tests/
  app/
    conftest.py
    test_settings.py
    test_maintenance_history.py
    test_frontend_contracts.py
    test_asset_libraries.py
    test_transcription_suggestions.py
    test_cut_draft.py
    test_cut_acoustic_boundaries.py
    test_cut_rendering.py
    test_art_text_api.py
    test_composition.py
    test_picture_in_picture.py
    test_art_text_track.py
    test_art_text_rendering.py
  test_build_mac_package.py
```

不增加 `tests/app/__init__.py`。当前没有 pytest 配置或插件要求测试目录成为 Python package，保持默认目录收集可以降低隐式导入风险。

## Migration Contract

1. 以函数名作为稳定身份，根据 `research/test-split-migration-matrix.md` 把 164 个原测试恰好迁移一次。
2. 两个参数化装饰器必须与对应函数一起迁移：应用测试仍从 164 个函数展开为 167 个节点。
3. 原前端综合契约测试替换为 9 个测试，830 条 `assert` 按研究矩阵恰好分配一次，因此应用测试最终为 175 个节点，加 Mac 打包测试共 176 个。
4. `_build_track_words` 只迁移到 `test_art_text_track.py`；Node 行为测试的脚本提取逻辑保持就地，不在本次新增公共 runner。
5. 原 `tests/test_app.py` 在全部迁移完成后删除，不保留重复导入或兼容收集层。

## Fixture And State Isolation

`isolated_jobs` 原样移动到 `tests/app/conftest.py`，继续在每个应用测试前：

- 保存并恢复模型名、请求 URL 与 DashScope 客户端 URL；
- 把 `DATA_DIR` monkeypatch 到函数级 `tmp_path`；
- 清除 API key 环境变量；
- 在 `JOBS_LOCK` 下清空 `JOBS` 和 `JOB_FILES`。

fixture 不移动到 `tests/conftest.py`，否则 sibling 的 Mac 打包测试会无意导入 `server.app` 并执行应用级 autouse 隔离。

## Frontend Contract Decomposition

`test_frontend_assets_are_versioned_and_not_cached` 拆成共享资源、EditorSuite、上传/历史、剪辑时间轴/草稿、剪辑范围/文案、艺术字、画中画、艺术字模板库和字体管理 9 个测试。

每个测试使用函数级 `_fetch_frontend_assets(*paths)` 小 helper，只请求本测试断言需要的资源。禁止模块级响应缓存，因为 `/api/art-templates` 必须在函数级临时 `DATA_DIR` 下读取。

静态断言仅继续覆盖资源版本、缓存头、DOM/ARIA、脚本引用和消息安全；现有 Node 行为测试保持原样，不能用新的源码字符串断言替代。

## Compatibility And Rollback

- 生产 API、页面、媒体输出和测试断言语义保持不变。
- 单个模块迁移后立即独立执行，发现导入或隔离问题时只调整目标测试模块/fixture。
- 最终提交是纯测试结构变更；回滚可整体撤销该提交，不需要数据迁移或生产兼容逻辑。

## Validation Strategy

- AST 对比 163 个不变测试名和 9 个新前端测试名，确保无丢失或重复。
- `pytest --collect-only -q` 必须收集 176 个节点。
- 13 个应用测试模块逐个独立执行。
- Mac 测试用 `--setup-show` 验证不出现 `isolated_jobs`。
- AST 检查任何单个测试函数不超过 300 行。
- 完整 pytest、`git diff --check` 和 `server/`/`web/` 零 diff 作为最终门禁。
