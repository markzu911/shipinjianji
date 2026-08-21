# 剪辑交互性能优化实施计划

## Phase 0: Baseline And Deterministic Probes

- [ ] 在隔离浏览器 fixture 中构造至少 600 个可见字符、30 个既有删除区间，覆盖文字删除/恢复、空白切换、撤销/重做和时间轴提交。
- [ ] 为 thumbnail extractor 创建/取消、基础 video `src/load()`、Store action、history serialization、草稿 PUT 和请求并发增加测试 spy；不把生产日志作为断言接口。
- [ ] 记录优化前 10 次连续操作的 input-to-post-commit-second-rAF P50/P95/max、long task、extractor 数、Store action 数和 PUT 数；测量终点必须断言目标 DOM 已更新，把测试环境与原始结果保存到本任务 research。
- [ ] 增加慢 PUT 与 in-flight 期间继续编辑 fixture，先锁定旧响应只推进 revision、不覆盖新物理范围，以及下一请求用新 revision rebase 的 latest-state/flush 正确性。
- [ ] 增加服务端校准改变物理 `start/end` 的 fixture，证明语义签名保持稳定且不会循环 PUT。
- [ ] 增加同一 rAF 前连续两个独立剪辑命令的 fixture，先证明现状需要两个 history entry 和两次独立撤销。
- [ ] 回滚点：基准和测试夹具独立于业务优化，可单独保留。

## Phase 1: Source-keyed Thumbnail Cache

- [ ] 从 `buildCutTimelineThumbnails()` 的 cache key 移除删除范围和 cut revision，定义 source fingerprint、采样计划和帧条目。
- [ ] 将抽取结果保存为 source-time frames；选择变化只通过现有 source/edited time mapping 重映射或隐藏帧。
- [ ] 建立唯一 extractor owner 和幂等 teardown，覆盖新构建、job/source 切换、错误、重置与 destroy。
- [ ] 保留 generation token 作为迟到写入门禁，验证 cancel 同时释放 listener、video source 和 object URL。
- [ ] 测试初次构建后连续 cut/undo/redo 的 extractor 创建数为 0，密度或源指纹改变时只触发一次有效重建。
- [ ] 回滚点：缓存层不改变删除范围或 timeline authority，可恢复旧构建函数而不迁移数据。

## Phase 2: One Cut Commit Per Frame

- [ ] 将 `updateSelectionSummary()` 拆成一次 frame-coalesced commit 和 frame 后 effects，保持既有选择 owner 与命令历史边界。
- [ ] 让所有 cut 入口请求同一个 scheduler；同一帧只派生一次 merged selection、渲染一次可见状态并刷新一次 timeline projection。
- [ ] 在每个命令 handler 内同步捕获 before/after/history meta 并按顺序入内存栈；移除单个 pending meta 对 rAF 提交时机的依赖，同帧渲染合并不得合并独立命令。
- [ ] 修改 `EditorSuite.setCutDraft()` 的渲染调用，显式使用 `hydrateProject: false` 或等价非 hydrate 路径。
- [ ] 保证一次 commit 恰好一个 `CUT_TIMING_CHANGED`、零个 `PROJECT_HYDRATED`，并验证 project/timing revision 在公共消费者间一致。
- [ ] 让显式 flush 在读取 desired 草稿前提交尚未执行的 frame commit。
- [ ] 测试点击删除在 post-commit 第二个 animation frame 可观察，终点 DOM 已更新；慢网络、缩略图 loading 和 history persistence 不阻塞反馈。
- [ ] 测试同帧两个命令只产生一次可见 commit、两个有序 history entry，连续两次撤销恢复两个中间状态。
- [ ] 回滚点：scheduler 只包裹现有语义函数；Store reducer、selection schema 和 API payload 不变。

## Phase 3: Coalesced Browser Persistence

- [ ] 重构草稿保存状态为 desired semantic signature、in-flight request signature/revision、acknowledged normalized snapshot/revision、单 timer 和单 in-flight request；语义签名排除服务端派生的物理 `start/end`、revision、diagnostics 和更新时间。
- [ ] 实现约 300ms trailing debounce；在途编辑只更新 desired，请求结束后发送一个最新 snapshot。
- [ ] 每次 pump 以当前 acknowledged revision 现场重建请求 envelope；首个响应后将等待中的 latest desired rebase 到新 revision，409 不无限自动重试。
- [ ] 重写 `flushCutDraftSave()` 的稳定循环，覆盖待处理 frame commit、timer 取消、在途等待、等待期间新编辑、语义签名确认和最终 revision 匹配。
- [ ] 断言过期响应可以推进权威 revision 但不覆盖较新的选择/物理范围；服务端改变物理边界后一次稳定，失败状态不把 localStorage 当成服务端成功。
- [ ] 将 cut history localStorage 序列化移到 idle/短 debounce，使用 dirty flag 合并；为 `pagehide`、hidden 和显式 flush 增加最终写入。
- [ ] 测试 300ms 内 10 次变化、已有请求在途、revision rebase、物理边界规范化、失败重试、生成前 flush、刷新恢复和 localStorage 异常。
- [ ] 回滚点：不修改草稿 schema 和历史格式；可以分别关闭 debounce 和 idle writer。

## Phase 4: Fingerprint-keyed PCM LRU

- [ ] 在服务端声学校准解码边界建立独立 PCM cache helper，key 使用 resolved path、size 和 `mtime_ns`，value 成本按 `len(samples) * samples.itemsize` 计算并保持共享样本只读。
- [ ] 增加可配置总字节预算和 LRU 淘汰；预算为 0 时直通当前解码路径，超大单项不入缓存。
- [ ] 实现 metadata lock 与 per-key in-flight decode，保证解码在锁外执行、同 key 并发请求共享一次结果。
- [ ] 解码失败不进入 cache，等待者统一恢复并沿用现有安全 fallback；淘汰只释放内存引用。
- [ ] 测试连续命中、并发 miss 去重、size/mtime 失效、按字节淘汰、超大单项、失败重试和禁用路径。
- [ ] 对比缓存启用/禁用的 text/timeline 物理范围、diagnostics 和 revision，保证结果完全一致；固定覆盖完整段落跨段转场、“得/你”、“一起给”、双方向、立即起音和 retained-side hard limit，同时证明尾音消失且下一段起音不受损。
- [ ] 回滚点：cache 位于现有完整 decoder/resolver 之前，不缓存范围结果，也不修改媒体或 sidecar。

## Phase 5: Integration And Performance Gate

- [ ] 运行隔离浏览器工作流，覆盖删除/恢复、空白、撤销/重做、时间轴、刷新、三工具切换、公共预览与统一生成；ArtTool 额外覆盖三页签、selection 返回规则、模板 listbox 键盘/焦点/关闭状态，以及 cut commit 前后 document/video/tool root identity 不变。
- [ ] 断言初次缩略图完成后连续 10 次操作不新建 extractor、不 reload 基础 video；每 frame 至多一次 cut action。
- [ ] 断言 300ms burst 最多一次常规 PUT、最大并发为 1，生成 flush 等待当前 semantic signature/revision 稳定；在途编辑后的第二次 PUT 使用新 revision，规范化物理范围不触发额外 PUT。
- [ ] 在代表性 fixture 重新测量至少 10 次操作：input-to-post-commit-second-rAF P95 <= 100ms，终点 DOM 已更新且无新增 >200ms long task；把环境和原始数据写入 research。
- [ ] 运行前端语法、定向测试、完整 browser suite、完整 pytest 和仓库 whitespace 检查。
- [ ] 若 gate 未通过，用计数和 profile 确认剩余成本；Store structural sharing、keyed transcript reconciliation 或虚拟化必须另建任务，不能在本阶段顺带扩 scope。

## Validation Commands

```powershell
Get-ChildItem web -Filter *.js | ForEach-Object { node --check $_.FullName }
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_frontend_contracts.py tests/app/browser/test_editor_workflows.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_acoustic_alignment.py tests/app/test_cut_draft.py tests/app/test_cut_acoustic_boundaries.py tests/app/test_cut_rendering.py tests/app/test_composition.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q server
git diff --check
```

## Risky Files And Review Points

- `web/app.js`：高频 cut orchestration、缩略图、history 和 draft queue 集中在同一文件。每个 phase 只改一个责任域，并先跑确定性计数测试。
- `web/editor-suite.js`：禁止通过跳过 hydrate 建立第二个 project owner；必须证明所有公共消费者读取同一个提交后的 frame。
- `web/editor-project-store.js`：本任务只测量并减少重复 action，不做 clone/signature/deep-freeze 重写。
- `server/app.py`：PCM cache 只能包裹解码，不得绕过每次范围解析、revision 或安全 fallback。
- `tests/app/browser/test_editor_workflows.py`：性能 wall-clock 只作为本机 gate；CI 使用工作计数与最大并发等确定性断言。
- 真实 `data/jobs`、`data/history` 和用户媒体只读；性能 fixture 和临时输出使用隔离目录，不提交媒体、缓存或秘密。
