# 拆分测试边界

## Goal

将当前约 9,740 行的 `tests/test_app.py` 按产品功能域拆分为可独立运行、职责明确的测试模块，为后续拆分 `server/app.py`、`web/app.js` 和 `web/art-text.js` 建立稳定回归边界；本任务不改变任何产品行为或业务实现。

## Background

- `tests/test_app.py` 当前包含 164 个测试函数，覆盖设置、维护、历史、前端静态契约、转写、文字剪辑、艺术字、画中画和统一合成。
- `test_frontend_assets_are_versioned_and_not_cached` 单个函数超过 1,000 行，同时验证多个页面和功能，失败定位与后续模块迁移成本过高。
- 当前唯一的 `isolated_jobs` 自动夹具和 `sample_video` 夹具定义在单体文件中；拆分后必须继续只作用于应用测试，不能影响独立的 Mac 打包测试。
- 当前完整基线为 `168 passed, 1 warning`，生产代码已发布并且工作区在本任务创建前保持干净。

## Requirements

- R1：将应用测试迁移到 `tests/app/`，按设置/维护/历史、前端契约与 Node 行为、转写与建议、文字剪辑与时间轴、艺术字、画中画、统一合成等功能域组织。
- R2：把 `isolated_jobs` 与 `sample_video` 放入 `tests/app/conftest.py`；自动隔离只覆盖 `tests/app/`，不得让 `tests/test_build_mac_package.py` 隐式加载应用测试夹具。
- R3：拆分超过 1,000 行的前端综合静态测试，按稳定契约分成多个可诊断测试；资源版本和安全约束可以保留源码/HTML 断言，可观察行为继续使用现有 Node 或 API 行为测试。
- R4：迁移后的每个测试保持原断言强度、monkeypatch 边界、临时目录隔离和外部 AI 请求屏蔽；不得为了拆分降低或删除断言。
- R5：各功能测试文件必须能单独运行，不能依赖 pytest 默认收集顺序或其他模块留下的 `JOBS`、模型设置、DashScope URL、缓存或临时文件状态。
- R6：保持现有测试名称，除非拆分综合测试需要增加更具体的测试名称；避免复制大型 fixture、媒体生成逻辑或前端脚本提取逻辑。
- R7：本任务只允许修改 `tests/` 和当前 Trellis 任务/必要测试规范，不修改 `server/`、`web/`、运行配置、API 契约或用户数据。
- R8：迁移后 `tests/test_app.py` 被移除或只保留无测试逻辑的兼容说明，不保留第二份重复测试实现。

## Acceptance Criteria

- [ ] AC1：`pytest --collect-only -q` 收集 `176` 个测试节点：原 168 个节点完整保留，并因前端综合契约从 1 个测试拆成 9 个而增加 8 个；完整测试为 `176 passed`（允许保留既有 warning）。
- [ ] AC2：每个 `tests/app/test_*.py` 模块可单独执行并通过，任意模块不依赖其他模块先运行。
- [ ] AC3：`tests/test_build_mac_package.py` 可单独执行，且不加载 `tests/app/conftest.py` 的自动应用隔离夹具。
- [ ] AC4：不存在超过 300 行的单个测试函数；原前端综合契约已按功能拆分，失败能定位到具体页面或领域。
- [ ] AC5：没有测试被静默删除，没有断言被弱化，没有真实外部 AI/HTTP 请求或真实 `data/jobs`、`data/history` 被用作 fixture。
- [ ] AC6：`server/` 与 `web/` 的 Git diff 为空；`git diff --check`、Python 编译和完整 pytest 均通过。
- [ ] AC7：测试目录结构与功能边界记录到 testing spec，后续业务模块拆分可以找到对应回归入口。

## Out Of Scope

- 不拆分或重构 `server/app.py`、`web/app.js`、`web/art-text.js`、`web/styles.css`。
- 不新增 `ProjectDocument`、前端统一 store、浏览器 E2E 框架或新的 pytest 插件。
- 不改变测试所定义的产品契约、时间边界、媒体渲染结果或错误文案。
- 不在本任务中处理 Starlette/httpx 的既有弃用 warning。

## Key Decisions

- 使用 `tests/app/` 子目录隔离应用测试夹具，避免根级自动夹具污染打包测试。
- 先按功能域拆测试，再移动生产代码；测试模块边界将作为后续生产模块拆分的验收入口。
- 本次只做行为保持型结构迁移，不把修复失败测试或清理业务实现混入同一变更。

## Risks And Deferred Items

- 大量测试直接引用 `server.app` 全局状态，机械移动可能暴露原有顺序依赖；发现后只修复测试隔离，不借机重构生产状态。
- 多个媒体测试执行较慢，按模块单独验证会增加检查时间，但这是确认独立性的必要成本。
- 生产代码拆分将在本任务通过并提交后作为新的独立子任务规划。
