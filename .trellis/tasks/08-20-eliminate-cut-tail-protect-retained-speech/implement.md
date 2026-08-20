# 实施计划

## Phase 0: 对齐器准入 Spike

- [x] 固定 `fa-zh v2.0.4` 和 Windows CPU 运行时，在隔离环境记录依赖、许可、模型大小、冷加载和峰值 RSS。
- [x] 对用户源视频只读运行完整句段 `得/你`、`给/一` 三次对齐，并保存原始 token、字符结果、结构校验、quiet range、波形和耗时。
- [x] 自动化 Gate：真实 FFmpeg/AAC、二次 ASR 和 PCM 证明 `37.810s` 清除被删残留且不削弱下一“你”；人耳盲听保留到最终真实媒体验收。

## Phase 1: Alignment Adapter And Cache

- [x] 增加隔离的本地对齐 adapter，惰性导入/加载模型，固定 revision，并把模型缓存定位到 `DATA_DIR/models`。
- [x] 实现可发声字符归一化、完整 segment 音频上下文提取、重复文本单调映射、结果结构校验和明确失败原因；不覆盖 `words/asrWords`，也不以其粗时间限制逐字符结果。
- [x] 实现 source/text/model/schema fingerprint、进程锁、segment 级复用和原子 sidecar；新转写预计算，旧任务按影响句段惰性补齐。
- [x] 增加 adapter/cache 单元测试，外部下载和模型推理一律 monkeypatch；真实模型只进入本地验收 gate。

## Phase 2: Unified Backend Boundary Resolver

- [x] 将文字专用校准提升为统一 resolver，一次处理 text/timeline 端点并复用同一 boundary cache/PCM。
- [x] 强制对齐提供语言学共享点；PCM 仅在硬保护范围内做极小窗 de-click。收紧高能量谷值资格并保留安全降级诊断。
- [x] 为 timeline 接受/返回 `originalStart/originalEnd`，仅在 `0.20s` 内吸附可靠转换；无语音、字符核心或失败时保持请求点。
- [x] 更新 media/semantic 投影：timeline 物理范围用于媒体，timeline 原始范围用于 retained transcript；保留短字符保护和防跨越合并。
- [x] 在 AI 建议期和 cut-draft PUT 复用同一 resolver/缓存；生成阶段继续禁止二次校准。

## Phase 3: Persistence And Generation Revision

- [x] 扩展 Pydantic DTO 与 cut-draft 兼容读取；旧 timeline 缺 `original*` 时逐条回退，不迁移历史文件。
- [x] 持久化通用 boundary diagnostics，并保持 revision 双重并发检查和原子写入。
- [x] 给新 `/cuts`、`/compose` 请求增加可选 `cutDraftRevision`；匹配时从权威草稿读取物理/语义范围，过期时返回冲突，旧 ranges-only 请求保持兼容。
- [x] 验证 edit 的 `ranges/requestedRanges` 和 `transcriptRanges` 继续分别表示物理与语义范围。

## Phase 4: Frontend Atomic Apply

- [x] timeline 序列化保留 `original*` 和稳定关联 key；撤销/重做与 localStorage 兼容旧 `{start,end}`。
- [x] 扩展 `applyPersistedCutDraftAlignment()`，在同一签名/revision 门槛下原子回写 text/timeline，更新当前 snapshot 而不新增 undo。
- [x] live transcript 用 `original*` 判断删字，keep spans/播放/公共 Store 使用 `start/end` 重映射。
- [x] `generateCut()` 和 EditorSuite compose 等待最新草稿保存完成，再从更新后的 frame 发送 revision 与物理范围。
- [x] 更新时间轴确认文案与状态，明确最终范围可能在语音附近小幅吸附；无语音范围仍精确。

## Phase 5: Regression And Real-Media Gate

- [x] 更新当前“manual timeline 始终精确”的后端、前端和 spec 契约为双范围规则。
- [x] 定向运行 `test_cut_acoustic_boundaries.py`、`test_cut_draft.py`、`test_cut_rendering.py`、`test_composition.py`、`test_frontend_contracts.py`。
- [x] 运行真实 Chromium：三入口、旧响应、撤销/重做、刷新、立即生成、公共预览/compose 与 375px。
- [x] 用用户源媒体和同一草稿走产品 resolver + FFmpeg/AAC 临时生成，记录二次 ASR、源/输出边界 PCM/频谱；真实 jobs/history 保持只读。
- [ ] 对产品链临时成片人工盲听：无被删尾音且下一保留字完整。
  - 2026-08-20 产品 resolver、同草稿真实 FFmpeg、PCM 和 Faster Whisper 二次 ASR 自动 gate 已通过，证据见 `research/product-real-media-gate.md`；人耳盲听仍未执行，因此本项保持未完成。
- [x] 记录 Windows 隔离 spike 的冷启/峰值 RSS，并验证 Mac requirements marker、打包测试和模型目录不入包。
- [ ] 补测 Windows 1/3/10 分钟完整性能基准，并在 Mac Intel/Apple Silicon 实机验证安装与推理。
- [x] 运行 `\.venv\Scripts\python.exe -m pytest -q`、编译检查和 `git diff --check`。

## Phase 6: Knowledge And Delivery

- [x] 更新 backend/frontend/operations/testing specs，替换 timeline 精确旧契约并记录强制对齐、缓存、诊断和降级不变量。
- [x] 使用 `trellis-break-loop` 复盘此前多次 RMS/边界修复为何无法覆盖连续语音，并写入可执行防复发规则。
- [x] 运行 `trellis-check` 全范围检查；任何声学安全、预览/生成一致或依赖发布失败都回滚到相应 phase。

## Risky Files And Rollback Points

- `server/app.py`：转写、草稿、范围解析和生成汇合；每个 phase 后先跑定向测试，避免跨层一次性大改。
- `server/schemas.py`：公开 DTO 必须保留旧请求兼容，并同步 schema export 测试。
- `web/app.js`、`web/editor-suite.js`、`web/editor-project-store.js`：必须以服务端草稿 revision 为权威，避免双状态和保存竞态。
- `requirements.txt`、`tools/build_mac_package.py`：模型运行时可能显著增大安装面；adapter gate 未通过时不得提交依赖变更。
- `data/jobs`、`data/history`：只读验收；禁止迁移、重写或把真实媒体纳入 fixture。
