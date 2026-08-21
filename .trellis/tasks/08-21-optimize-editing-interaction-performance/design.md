# 剪辑交互性能优化技术设计

## 1. Design Goal

把删除段落等高频操作的点击任务缩短为“一次语义提交 + 下一帧可见反馈”，将缩略图抽帧、历史持久化和草稿网络保存移出关键交互路径；服务端复用同一源媒体的 PCM 解码结果。所有优化只改变调度、缓存和重复工作，不改变删除语义、声学边界、revision、撤销/重做、预览或生成结果。

## 2. Current Bottleneck Boundary

当前 `updateSelectionSummary()` 把五类不同职责串在一次操作中：

```text
selection mutation
  -> semantic range derivation
  -> transcript/history rendering
  -> EditorProjectStore synchronization
  -> timeline + thumbnail reconstruction
  -> local and remote persistence
```

其中只有语义状态提交和可见删除/恢复反馈必须在下一帧完成。缩略图 seek/JPEG、localStorage 序列化和服务端 PUT 都是可合并副作用。Store 的全量 clone/signature 有独立成本，但本任务先消除重复 dispatch/hydrate，不重写 Store。

## 3. Target Interaction Pipeline

### 3.1 Frame-coalesced cut commit

引入单一 cut commit scheduler，持有最新选择快照、dirty flags 和唯一 `requestAnimationFrame` handle。删除、恢复、空白切换、撤销/重做和时间轴确认继续更新各自现有的内存选择 owner，但每个用户命令必须在 handler 内同步捕获 `{ before, after, label, coalesceKey }` 历史事务，再请求一次可见 commit。不能继续依赖单个 `cutHistoryPendingMeta` 等到 rAF 才推断命令边界。

同一 animation frame 内的多次请求合并为 latest-state commit：

1. 从当前 `selectedRanges` / `selectedNoSpeechRanges` 派生一次 merged selection。
2. 更新文字行和删除/恢复可见状态。
3. 向 EditorSuite 提交一次 `CUT_TIMING_CHANGED`。
4. 用同一 frame 刷新时间轴几何、公共预览和 compose projection。
5. 按捕获顺序把本帧历史事务写入内存栈；将历史落盘、缩略图映射和草稿保存投递到 frame 之后的 effect 队列。

调度器只合并渲染和 effect，不合并用户历史语义：同帧两个命令形成两个有序 before/after，既有 `coalesceKey + 800ms` 规则仍可显式合并同一拖动事务。`flushCutDraftSave()` 在需要时先同步执行尚未提交的最新 cut commit 和内存历史事务，避免生成读取前一帧状态。

可见性能测量不能在 rAF 回调入口结束。测试在输入时记录起点，在 commit rAF 内完成关键 DOM 更新，再在后续 rAF 中确认目标 DOM 已更新并记录终点；这覆盖 commit 回调本身及至少一次浏览器绘制机会。frame 后 effects 不进入关键反馈路径。

### 3.2 One Store action, no re-hydration

`EditorSuite.setCutDraft()` 继续是 cut 状态进入共享 Store 的唯一入口。它提交 `CUT_TIMING_CHANGED` 后调用非 hydrate 渲染路径，例如 `renderJobState(currentJob, { hydrateProject: false })`，或直接渲染已提交的 project frame；不得用同一 job 再尝试 `PROJECT_HYDRATED`。

服务端规范化草稿响应仍通过既有 revision guard 应用。一次本地 cut commit 的验收计数固定为：一个 `CUT_TIMING_CHANGED`、零个 `PROJECT_HYDRATED`，公共 video、preview、timeline 和 compose selector 观察到同一个 timing revision。

## 4. Source-time Thumbnail Cache

### 4.1 Cache identity

缩略图缓存以源媒体而不是删除区间为权威。cache key 仅包含会改变源帧内容或采样计划的输入：

- job/source 稳定标识与媒体指纹；
- 源时长和可 seek 范围；
- 缩略图密度、尺寸和编码参数；
- 必要的资源版本。

`selectedRanges`、`selectedNoSpeechRanges`、cut revision 和剪后时长不得进入 source-frame key。

缓存条目保存 `{ sourceTime, image, width, height }`。选择变化后，根据现有 source-time / edited-time 映射把缓存帧投影到剪后时间轴；落在删除区间的帧隐藏或跳过，其余帧只调整位置。密度变化时可以复用重合 source sample，只补抽缺失帧。

### 4.2 Active cancellation

缩略图构建由唯一 extractor owner 管理。开始不同 source/key 的构建前必须 cancel 当前 extractor：移除 seek/load/error listener、暂停 video、清空 `src`、调用 `load()` 释放媒体资源，并撤销仅由该任务创建的 object URL。generation token 继续作为迟到回调的写入门禁，但不能代替资源释放。

以下事件都执行同一个 teardown：job/source 切换、页面重置、媒体错误、密度重建和编辑器销毁。取消后的任务不得再更新缓存、状态文案或 DOM。相同 source key 已完整缓存时不创建 extractor，也不改写基础预览 video 的 `src`。

## 5. Persistence Coalescing

### 5.1 Draft save queue

草稿保存队列维护四类相互独立的状态：

```text
desired semantic snapshot + semantic signature
debounce timer
single in-flight { semantic signature, request revision, payload }
acknowledged { semantic signature, normalized snapshot, server revision }
```

语义签名只描述用户意图：`automaticNoSpeechInitialized`、稳定 range key、文字/timeline 的 `originalStart/originalEnd`、文字内容，以及 no-speech 的规范化范围。服务端派生的文字/timeline 物理 `start/end`、草稿 revision、diagnostics 和更新时间不得进入语义签名，否则一次声学校准响应会把已确认请求变成新的“未保存修改”。旧草稿缺少 `original*` 时先通过既有规范化入口得到语义范围，再计算签名。

普通编辑先立即更新现有本地恢复快照，再用约 300ms trailing debounce 请求 server save。timer 到期后，若无请求在途，则用最新 desired semantic snapshot 与最近一次 acknowledged server revision 现场构造请求 envelope；不得发送编辑发生时冻结的旧 revision。若已有请求在途，只更新 desired。请求结束后最多启动一个 latest-state 请求，继续保持并发数为 1。

响应先校验 job/source 与 in-flight 身份。成功响应始终推进 acknowledged server revision，供下一次请求 rebase；只有响应对应的 semantic signature 仍等于当前 desired 时，才原子应用规范化物理 `start/end`、记录 acknowledged semantic signature，并把规范化草稿写入本地恢复状态。若等待期间发生新编辑，旧响应不得覆盖新物理范围，但下一次 latest-state PUT 必须携带该响应的新 revision。409 保持现有跨页面冲突语义，不自动无限重试。失败保留 dirty desired 状态和现有错误提示/重试语义，不把 localStorage 写入标记成服务端成功。

`flushCutDraftSave()`：

1. 提交待处理的 frame commit；
2. 取消 debounce timer；
3. 立即 pump 最新 desired；
4. 等待 in-flight 完成；
5. 若等待期间 desired 改变，继续 pump；
6. 仅当无待处理 commit、无 timer、无 in-flight、`desiredSemanticSignature === acknowledgedSemanticSignature` 且 acknowledged revision 对应当前 job/source 时返回。

因此点击生成时仍获得稳定、可生成的最新 revision，而保存期间继续编辑不会丢失。

### 5.2 Idle history persistence

每个命令的 history transaction 继续同步写内存，保证当前会话立即可用且同帧命令不会丢失。localStorage 序列化由单一 dirty flag 合并到 `requestIdleCallback`；不支持该 API 时使用短 debounce，并为 idle callback 设置 timeout，避免永久不落盘。

`pagehide`、文档进入 hidden 和显式 flush 对 dirty history 做一次同步最终写入。写入失败沿用容量/存储错误处理，不阻止当前 cut commit，也不改变服务端草稿状态。

## 6. Bounded PCM LRU Cache

服务端在 cut-draft 声学校准入口增加进程内 PCM cache，key 至少包含解析后的媒体路径、文件大小和 `mtime_ns`；任一字段变化都会形成新 key。value 保存解码参数和不可由下游修改的 PCM 样本；当前 `array('h')` 的成本按 `len(samples) * samples.itemsize` 计算，不依赖不存在的 `.nbytes` 属性。

缓存使用明确的总字节预算（配置项，默认 256 MiB）和 LRU 淘汰。写入新 value 前淘汰最久未使用条目，单项大于总预算时只供当前请求使用而不入缓存。缓存引用被请求取得后，即使随后从 LRU 淘汰也不影响该请求；淘汰只释放内存引用，绝不删除媒体或 sidecar。

并发控制采用“全局元数据锁 + per-key in-flight decode”：

- 命中时在锁内更新 LRU，随后返回共享只读 PCM；若继续使用可变 `array`，helper 必须通过封装和测试保证所有消费者只读，不能把共享引用暴露给写路径；
- 首个 miss 注册 in-flight 后在锁外执行 FFmpeg；
- 同 key 的其他请求等待同一结果，不重复解码；
- 解码成功后在锁内按预算插入并唤醒等待者；
- 解码失败不缓存失败值，唤醒等待者后走现有语义范围安全回退。

缓存只复用媒体解码，不缓存 range alignment 结果。每次 PUT 仍使用最新 text/timeline ranges 执行完整边界解析，避免相邻删除状态和重复文案改变 transition trust 时误用旧边界。

## 7. Data Flow After Optimization

```text
user cut command
  -> mutate existing selection owner
  -> one next-frame cut commit
       -> visible transcript/timeline state
       -> one CUT_TIMING_CHANGED
       -> source-frame thumbnail remap
  -> deferred effects
       -> idle history persistence
       -> 300ms latest-state draft queue
            -> one in-flight PUT
            -> fingerprint-keyed PCM LRU
            -> existing full acoustic range resolver
            -> guarded normalized revision
```

不存在第二套选择状态、时间轴状态或声学边界算法。

## 8. Compatibility And Failure Matrix

| Condition | Required behavior |
| --- | --- |
| 缩略图缓存未完成 | 文字删除仍在下一帧可见；时间轴显示现有 loading/占位状态 |
| extractor 被新 job 或密度构建替代 | 主动 teardown；迟到回调无写权限 |
| 草稿 PUT 很慢 | UI 和撤销继续工作；后续编辑合并为 latest desired |
| 草稿 PUT 失败 | 保留 dirty 状态和重试能力；生成 flush 不虚报稳定 revision |
| 旧响应晚于新编辑 | 不应用旧物理范围到新选择 |
| 首个 PUT 在途时继续编辑 | 首个响应推进 server revision；第二个 latest-state 请求以新 revision 发送 |
| 服务端校准改变物理 `start/end` | 当前语义只确认一次，不因物理签名变化循环 PUT |
| localStorage 不可用或超额 | 当前会话内存历史继续工作；服务端保存语义不受影响 |
| PCM cache miss/eviction | 重新解码，结果与未缓存路径一致 |
| PCM decode 失败 | 沿用现有语义范围安全回退，不改变错误契约 |
| 媒体 size/mtime 变化 | 新指纹 miss，不复用旧 PCM/缩略图 |
| 同一帧发生两个独立命令 | 可见渲染合并一次；history 保留两个有序事务，可逐次撤销 |
| cut frame 重绘时 ArtTool 正在使用 | 三页签、listbox 焦点/关闭状态和 selection 不被无关 cut revision 重置 |

## 9. Instrumentation And Verification

浏览器测试加入可注入计数器或 spy，稳定断言每次/每组操作的：extractor 创建数、基础 video `load()` 次数、Store action 类型、草稿 PUT 数与最大并发数、history serialize 次数。计数是 CI 主门禁，不依赖机器速度。

代表性 fixture 至少包含 600 个可见字符和 30 个既有删除区间。浏览器用 `performance.mark/measure` 记录输入事件到 post-commit 第二个 animation frame 的延迟，在终点断言目标 DOM 已更新，并通过 `PerformanceObserver` 收集 long task；禁止以第一个 rAF 回调入口冒充可见完成。本机 gate 记录浏览器、硬件、样本数、P50/P95/max 和原始测量结果。

服务端测试以 decode spy 证明同一指纹并发/连续请求只解码一次、变更指纹会 miss、LRU 按实际字节淘汰且失败不污染缓存。另用现有声学范围 fixture 对比缓存开关前后的规范化 payload 完全一致，固定覆盖完整段落跨段 forced/PCM、立即起音、delete-start/delete-end、“得/你”、“一起给”和 retained-side hard limit；每例同时断言被删尾音消失、下一段起音不受损、`original*` 与 diagnostics 不漂移。

浏览器集成回归除 cut/art/pip 三工具 identity 外，还覆盖 ArtTool 三页签、selection 从有变无的返回规则、模板 listbox 键盘/焦点/关闭语义，以及 cut commit 前后的 active tab、selection、document/video identity 不变。

## 10. Rollback

- frame scheduler、thumbnail cache、draft queue、history idle writer 和 PCM cache 分阶段提交，任何阶段都可独立回滚。
- thumbnail cache 回滚后恢复现有 generation guard，不触碰用户媒体和选择数据。
- draft queue 回滚只恢复请求调度；草稿 schema、revision 和 API 不变。
- PCM cache 可通过配置将预算设为 0 禁用；未命中路径就是当前完整解码路径。
- 若完成这些优化后代表性 fixture 仍超过预算，保留测量结果，另行规划 keyed transcript reconciliation、列表虚拟化或 Store structural sharing，不在本任务中扩大重构范围。
