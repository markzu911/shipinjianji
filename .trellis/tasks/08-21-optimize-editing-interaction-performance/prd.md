# 优化剪辑交互卡顿

## Goal

让用户在文字删除、恢复、空白片段切换、撤销/重做和时间轴区间提交等高频剪辑操作中立即获得视觉反馈，避免主线程因重复全量渲染、媒体缩略图重建和同步本地持久化出现明显停顿；同时降低草稿服务端保存的重复音频解码成本。优化不得改变用户选择的文字语义范围、服务端声学吸附结果、草稿 revision、撤销/重做、刷新恢复、公共预览或最终生成结果。

## Background

- 一次选择变化由 `web/app.js:2982` 的 `updateSelectionSummary()` 同步触发历史快照、完整文字列表渲染、EditorSuite 草稿同步、完整时间轴刷新和本地/服务端草稿保存。
- `web/app.js:3662` 的 `buildCutTimelineThumbnails()` 把删除区间加入缓存签名；每次删除都会创建新 video extractor，逐次 seek、Canvas 绘制并编码 8-180 张 JPEG。旧任务只有 generation 检查，没有主动释放正在 seek 的 extractor。
- `web/editor-suite.js:1601` 的 `setCutDraft()` 先提交 `CUT_TIMING_CHANGED`，随后再次调用 `renderJobState(currentJob)`；后者默认尝试 `PROJECT_HYDRATED`，形成重复的全状态归一化路径。
- `web/editor-project-store.js:671-966` 每次 action 都克隆完整 project、计算多份稳定 JSON 签名并深冻结结果。以当前 634 字、18 段历史 transcript 做纯 Store 基准，单次 cut action中位数约 11.27ms、P95 约 15.70ms、最大约 24.60ms，尚未包含 DOM 和媒体工作。
- `web/app.js:2610` 的草稿保存没有防抖；每个稳定点击都可能提交完整范围集合。`server/app.py:4642-4698` 每次草稿 PUT 都重新解码完整媒体并处理全部范围。
- 以当前 68MB 源媒体和 32 个文字删除范围做只读基准：完整 PCM 解码约 190ms，已有 PCM 下范围对齐约 429-457ms。服务端工作不会直接阻塞浏览器线程，但延长保存状态，并可能在响应应用后触发第二轮前端刷新。
- `web/app.js:2731` 每次操作同步序列化最多 40 个撤销历史条目到 localStorage，历史越长，点击任务内的同步工作越多。
- 当前 `cutHistoryPendingMeta` 只能保存一个待提交命令。把多个入口延迟到同一 animation frame 时，如果不先同步捕获每个命令的 before/after，后一个命令会覆盖前一个命令的撤销元数据。
- 当前草稿选择签名包含服务端会校准的物理 `start/end`，而 PUT 响应会返回新的物理边界并递增 revision。保存队列不能把“用户语义未变化”“请求 payload 完全相等”和“服务端已确认当前 revision”合并成一个签名判断。
- 现有删除边界、双层词时间戳、草稿稳定队列和单页原子 frame 都已有严格规格与回归，不允许通过绕过服务端校准或建立第二套状态来换取速度。
- 当前 ArtTool 已固定为“选择艺术字 / 艺术字设置 / AI 推荐”三页签和 trigger + listbox 模板控件；任一 cut frame 调度变化都必须保持页签、焦点、selection 和同一 document/media identity。

## Requirements

- R1：删除、恢复、空白切换、撤销/重做和时间轴提交必须先更新可见交互状态，再调度非必要的结构渲染、预览 seek 和持久化；用户不等待服务端响应才能看到操作结果。可见反馈的耗时必须测到 DOM 提交后的下一次绘制机会，不能只测到 `requestAnimationFrame` 回调开始。
- R2：时间轴缩略图以源媒体为缓存权威。删除范围变化只重映射或隐藏已有源帧，不得重新加载同一媒体、重新 seek 或重新编码全部缩略图；job/source、源媒体指纹或缩略图密度真正变化时才允许补建缓存。
- R3：任一时刻只允许一个有效缩略图 extractor。新构建、job 切换、媒体错误、页面重置和销毁必须主动终止旧 extractor，并禁止迟到回调写入新 DOM。
- R4：一次 cut 语义变化只提交一次 `CUT_TIMING_CHANGED`。`renderJobState` 不得因本地 cut draft 变化再次 hydrate Store；公共媒体、预览、时间轴和 compose 继续消费同一个原子 frame。
- R5：草稿本地恢复状态仍在操作后立即可用；服务端 PUT 使用约 300ms 的 trailing debounce、latest-state-wins 和单 in-flight 语义。队列必须分别维护用户语义签名、在途请求签名/请求 revision、服务端确认的语义签名/规范化范围/revision；后续 PUT 必须用最近一次服务端确认的 revision 重建请求 envelope。`flushCutDraftSave()` 必须取消等待、强制发送最新语义状态，并只在当前语义签名已由当前 job/source 的服务端 revision 确认后允许生成。
- R6：每个独立用户命令的 before/after 和历史元数据在命令发生时同步捕获，不能因 frame 合并而丢失或合并；只有可见渲染和副作用允许按帧合并。撤销历史先写内存，localStorage 序列化合并到空闲阶段或短防抖中；页面离开和显式 flush 仍要保存最新可恢复历史。localStorage 不能冒充服务端草稿成功。
- R7：服务端为 cut-draft 声学校准复用按媒体指纹缓存的只读 PCM。缓存必须有并发保护、按 `len(samples) * samples.itemsize` 计算的明确字节上限/LRU 淘汰和源媒体变更失效；下游不得修改共享样本，音频解码失败仍走现有语义范围安全回退。
- R8：本任务不改变声学边界算法和 `originalStart/originalEnd` 与物理 `start/end` 的双层契约。缓存开关前后必须保持文字/timeline 范围、diagnostics 和 revision 完全一致，并明确覆盖完整段落跨段转场、“得/你”、“一起给”、delete-start/delete-end、保留侧 hard limit、下一段立即起音和短保留字符。未变化区间的增量声学校准只有在能证明相邻删除状态和重复转场不受影响后才能另行规划，本任务不以冒险复用旧边界换取耗时下降。
- R9：先通过删除操作的确定性工作计数验证优化，再补充本机性能测量。浏览器 wall-clock 使用“输入开始 -> 关键 DOM 已提交 -> 再一次 animation frame 回调”的双帧绘制机会代理，并同时记录 long task；不得只测首个 rAF 回调起点、主观手感或单次 wall-clock。
- R10：优化必须保持原生 JavaScript、无构建步骤和现有 FastAPI 单体边界，不引入前端框架、Web Worker 媒体副本、数据库或第二个时间轴/项目状态 owner。
- R11：cut commit 导致的 Store frame 重绘不得重置 ArtTool 当前页签、模板 listbox 焦点/关闭语义或艺术字 selection；“选择艺术字 / 艺术字设置 / AI 推荐”与 manual/transcript 轨道契约保持不变。

## Acceptance Criteria

- [ ] AC1：真实浏览器中点击删除后，目标行的删除/恢复状态在关键 DOM 提交后的下一次绘制机会可见；测试在后续 rAF 中读取最终 DOM，草稿网络请求延迟或失败不阻止该反馈。
- [ ] AC2：初始缩略图缓存完成后，连续执行文字删除、恢复、撤销和重做不会创建新的缩略图 extractor，不会改写基础 video `src`/调用 `load()`，已有缩略图节点或缓存帧被复用并按剪后时间正确重映射。
- [ ] AC3：同一 job/source 同时最多存在一个缩略图构建；切换 job、重置或新密度构建后，旧回调不再修改状态、状态文案或 DOM。
- [ ] AC4：一次删除操作恰好产生一个 Store `CUT_TIMING_CHANGED`，不产生 `PROJECT_HYDRATED`；公共 video/preview/timeline 的 project revision 与 timing revision 保持一致。
- [ ] AC5：300ms 内连续 10 次选择变化最多产生 1 次常规草稿 PUT；若首个请求已在途，后续变化最多合并为 1 次 latest-state PUT，且并发请求数恒为 1。第二次请求使用首个成功响应返回的 revision，不因冻结旧 revision 得到 409。
- [ ] AC6：点击“生成”或统一 compose 时，`flushCutDraftSave()` 能绕过 debounce，等待最新用户语义签名获得服务端 revision；保存期间的新编辑不会丢失，旧响应可以推进权威 revision，但不得把旧物理范围覆盖到新语义状态。服务端校准改变物理 `start/end` 后队列一次稳定，不循环重复 PUT。
- [ ] AC7：同一未变化媒体的连续和并发 cut-draft 校准只执行一次完整 PCM 解码；媒体大小或 mtime 指纹变化后重新解码。缓存超过预算时按 LRU 淘汰，淘汰不删除用户媒体或 sidecar；并发命中、缓存禁用和缓存失败路径的规范化 payload 完全一致。
- [ ] AC8：现有文字/空白删除、相邻静音保护、时间轴二次确认、撤销/重做、刷新恢复、三工具切换、公共预览与最终 compose 回归全部通过；声学校准明确覆盖完整段落跨段转场、“得/你”、“一起给”、双方向和保留侧 hard limit，同时证明尾音消失且下一段起音不受损。
- [ ] AC9：使用至少 600 个可见字符、30 个既有删除区间的隔离浏览器 fixture 连续执行 10 次操作；本机记录输入到 post-commit 第二个 rAF 的 P95 不高于 100ms，且无大于 200ms 的新增前端 long task。测量必须在后续 rAF 验证目标 DOM 已更新，并记录环境和原始数据；确定性计数仍是 CI 的主要门禁。
- [ ] AC10：完整 `tests/app/browser`、相关前后端测试、全部 `web/*.js` 语法检查和 `git diff --check` 通过；测试不读取真实 `data/jobs`、`data/history` 或外部模型。
- [ ] AC11：同一 animation frame 内连续执行两个独立剪辑命令只触发一次可见 commit，但形成两个有序 history entry，连续两次撤销分别恢复两个中间状态；cut frame 重绘期间 ArtTool 三页签、listbox 焦点/关闭状态和 selection 契约不漂移。

## Out of Scope

- 不全面重写 `EditorProjectStore`、引入不可变数据框架或更换前端技术栈；若完成本任务后 Store 仍超预算，另建结构优化任务。
- 不修改强制对齐、重复文案可信度、波形谷底、字符保护或媒体生成算法。
- 不实现长文案列表虚拟化；先消除重复渲染和媒体重建，只有测量仍超标时另行规划。
- 不改变缩略图的产品功能、增加用户设置或视觉改版；缩略图仍是导航辅助，文字和时间刻度仍是时间权威。
- 不清理现有用户媒体、历史、草稿或工作区中的其他未提交改动。
