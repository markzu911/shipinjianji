# 实施计划

## Phase 1: Regression First

- [x] 在 `tests/app/test_cut_draft.py` 增加两个现场同构 fixture，锁定“一起”/“你”粗时间完全落在物理 cut 内时的当前丢字。
- [x] 增加 forced timing 可用、无 alignment 和错序 alignment 回归，断言文字完整且时间 finite/positive/monotonic。
- [x] 在 `tests/app/test_frontend_contracts.py` 增加 Node 回归，覆盖完全坍缩 token 和 stale projection。

## Phase 2: Backend Projection

- [x] 抽取“语义选字 -> forced/coarse timing -> physical warp”纯函数。
- [x] 重构 `build_retained_transcript()`，使用字符投影真值聚合 `words/asrWords`，不再因时长坍缩删字。
- [x] 增加可选 `alignment_cache`、source anchors 和 `sourceSegmentIndex`，保持旧调用兼容。

## Phase 3: Cut Draft Derived Transcript

- [x] 新增从 job + normalized draft 构建 retained transcript 的共享 helper。
- [x] cut-draft PUT/GET 返回 `{cutDraft, retainedTranscript}`，不改 CutDraftRequest 或 `cut-draft.json`。
- [x] 增加 revision 一致、旧草稿恢复、缺少 sidecar 和过期 revision API 测试。

## Phase 4: Generation And Recovery

- [x] 让 `/cuts`、`/compose` 传入已有 alignment sidecar，不触发新模型推理或二次边界解析。
- [x] 更新 project-state/edit 恢复路径，复用同一投影契约。
- [x] 断言生成/history transcript 一致，FFmpeg 物理 ranges 不变。

## Phase 5: Frontend Single Projection

- [x] 引入受 job/signature/revision 守卫的 server retained projection，在本地编辑、撤销/重做、恢复和 job 切换时失效。
- [x] 重构 `getRetainedSegmentParts()` 为先语义选字、后物理映射，去掉 keep-span 不相交就删字的行为。
- [x] 抽取 `getCurrentRetainedProjection()`，供 live draft、时间轴、播放命中和 EditorSuite/Store 共用。
- [x] 增加 server projection 缺失、响应前瞬时降级和 stale response 契约。

## Phase 6: Verification

- [x] 增加 Store/TimelineController 和浏览器回归，断言列表、live transcript、frame timeline 和 compose DTO 逐字一致。
- [x] 用真实 job 数据只读运行投影器，核对期望文字、forced 起音和物理 ranges。
- [x] 定向运行 `test_cut_draft.py` 、`test_cut_rendering.py`、`test_cut_acoustic_boundaries.py`、`test_frontend_contracts.py`、Store/TimelineController 和 composition。
- [x] 运行相关全量 pytest、`.venv\Scripts\python.exe -m compileall -q server` 和 `git diff --check`。
- [x] 使用 `trellis-check` 审计 spec、数据流、兼容性、测试和工作区范围。

## Risky Files And Rollback Points

- `server/app.py`：每完成 backend/cut-draft/generation 一阶段先跑 retained transcript 和声学定向测试。
- `web/app.js`：只修投影与 revision guard，不改文字选择 UX、boundary resolver 或 UI 布局。
- 若物理 range 或声学 boundary 发生变化，立即回到投影层重审，不修改 resolver 迁就文字测试。

## Implementation Evidence

- 真实 job `99c068e5-7442-482f-84d0-5b36ab8a39e5` 只读投影包含“所有人一起给你画”和“你身边人人都觉得”。
- 同一 job 的物理 ranges 保持 `28.299-29.807s` 与 `32.730-37.790s`。
- 定向验证：声学边界 `90 passed`；剪辑草稿/渲染/前端契约/转写建议 `94 passed`；Store/TimelineController/compositor/composition `32 passed`。
- `node --check web/app.js`、`.venv\\Scripts\\python.exe -m compileall -q server`、`git diff --check` 通过。
- Phase 2.2 审查补齐显式空 semantic/physical range 兼容、文字保存投影守卫和 stale effect 重试；核心与支持性定向测试合计 `265 passed`。
- 最终浏览器 workflow：`45 passed`；完整非浏览器 pytest：`372 passed`（仅既有 Starlette/httpx 弃用警告）。
- `node --check web/app.js web/editor-suite.js web/editor-project-store.js`、`.venv\Scripts\python.exe -m compileall -q server` 和 `git diff --check` 最终通过。
