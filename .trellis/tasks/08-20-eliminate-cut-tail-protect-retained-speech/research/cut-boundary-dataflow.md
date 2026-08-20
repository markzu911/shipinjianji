# Research: 删除边界完整数据流与统一点

- Query: 梳理 AI 文案删除、手动文案删除和手动时间轴删除从前端预览、cut draft 持久化、后端范围解析、FFmpeg 生成到 retained transcript 的完整数据流；确定统一声学边界的落点、兼容约束和现有测试/规范。
- Scope: internal
- Date: 2026-08-20

## Findings

### 结论摘要

当前有两条不同的边界路径：AI 建议和手动点击文案都进入 `textRanges`，在保存 cut draft 时由后端做声学边界校准；手动时间轴删除进入 `timelineRanges`，前后端都只做时长 clamp，完全绕过声学校准。三类选择随后才在 `getMergedSelection()` / `resolve_cut_draft_delete_ranges()` 合并为媒体删除范围。

最小且完整的统一位置不是 FFmpeg 生成阶段，而是 `PUT /api/transcriptions/{job_id}/cut-draft`：这里已经具备原视频、原始 transcript、revision 和三类范围，也是前端预览能够接收最终物理范围的最早服务端边界。生成阶段必须继续只消费已持久化、已预览的范围，不能再次吸附。

统一后，`timelineRanges` 也必须像 `textRanges` 一样区分用户意图和媒体切点，但仍不做文字字符语义扩展：

- `originalStart/originalEnd`：用户拖拽并确认的精确源时间范围，也是 retained transcript 判断手动删除语义的输入。
- `start/end`：强制对齐/安全吸附后实际用于预览和 FFmpeg 的物理范围。
- 若端点不在可证明的语音交界附近、对齐失败或会越过下一保留发音，物理范围回退到原始手动范围。

现有声学上游并不是真正的字符/音素强制对齐。DashScope 只返回原始 word 时间，`transcript_acoustic_character_units()` 又在多字 token 内均分时间；这正是“得你”边界误判的来源。因此统一三条入口只能解决入口漂移，要根治尾音还需要在转写/媒体分析阶段产生一次可复用的真实字符/音素边界，并让 AI 建议和 cut draft 解析共同消费它。

### Files Found

| 文件 | 作用 |
| --- | --- |
| `server/schemas.py` | `CutRequest`、`CutDraftRequest`、`PreviewCompositionRequest` 的范围 DTO；目前 `timelineRanges` 只有 `start/end`。 |
| `server/app.py` | 转写、声学分析、草稿持久化、范围解析、retained transcript、FFmpeg 裁剪、`/cuts` 与 `/compose` 的单体实现。 |
| `web/app.js` | 三类删除入口、源时间预览、cut draft 本地/服务端同步、撤销历史和 `/cuts` 请求。 |
| `web/editor-project-store.js` | 将当前 cut 物理范围投影到公共预览、时间线和 compose DTO。 |
| `web/editor-suite.js` | 将 cut draft 写入顶层 Store，并从同一 frame 发起 `/compose`。 |
| `web/editor-media-controller.js` | 保存当前 cutRanges，执行源时间/剪后时间转换；实际跳过删除区间仍由 `web/app.js` 完成。 |
| `tests/app/test_cut_acoustic_boundaries.py` | 共享声学边界、增益稳定、连续 token、保留下一个字符等回归。 |
| `tests/app/test_cut_draft.py` | cut draft API、字符语义/物理范围分离、手动范围精确语义和保护区回归。 |
| `tests/app/test_cut_rendering.py` | `/cuts`、retained transcript、真实 FFmpeg 小样片和生成阶段不重吸附。 |
| `tests/app/test_composition.py` | `/compose` 使用同一 cut 范围并依次生成 cut/art/pip。 |
| `tests/app/test_frontend_contracts.py` | 前端范围合并、草稿回写、时间轴交互和当前“手动范围精确”静态/Node 契约。 |
| `tests/app/browser/test_editor_workflows.py` | 草稿刷新恢复、顶层 Store 和 compose 请求的真实浏览器契约。 |
| `.trellis/spec/backend/media-and-timeline.md` | 文字语义/媒体物理边界、保留语音保护、预览/生成一致性和 ASR 双层时间合同。 |
| `.trellis/spec/frontend/architecture-and-state.md` | `selectedRanges`、`timelineRanges`、展示态、保护顺序和公共 Store 的权威边界。 |
| `.trellis/spec/frontend/ui-and-interactions.md` | 当前手动时间轴只 clamp、不吸附的产品交互合同。 |
| `.trellis/spec/backend/persistence-and-jobs.md` | `cut-draft.json` 的 schema v1、revision、原子写入和旧草稿兼容。 |
| `.trellis/spec/backend/quality-guidelines.md` | 时间范围不变量、字段兼容、真实媒体测试和语义/物理分离要求。 |
| `.trellis/spec/testing/index.md` | 剪辑、浏览器、FFmpeg 回归的测试选择规则。 |

### 上游时间数据

1. `transcribe_audio()` 启用 DashScope `timestamp_alignment_enabled=True`，但实际只读取 sentence/word 的 `begin_time/end_time`（`server/app.py:9014-9084`）。
2. `retokenize_words()` 先把每个 ASR word 的时间在字符间均分，再用 Jieba 重组为自然词（`server/app.py:7780-7847`）。`build_sentence_segments()` 把自然词存入 `segments[].words`，把模型原始词另存为 `segments[].asrWords`（`server/app.py:7850-7910`）。
3. `process_job()` 已经在一次转写任务内解码 16kHz 单声道 PCM，用它检测 quiet range 和校准 AI 建议（`server/app.py:9130-9196`）。这是一次性生成并持久化字符/音素对齐结果的自然 owner，避免每次草稿 PUT 重新解码/重新推断。
4. 当前 `transcript_acoustic_character_units()` 对 `asrWords` 中的多字 token 再次等分 `_acousticStart/_acousticEnd`，仅在自然字符序列与 ASR 字符序列完全一致时使用（`server/app.py:2529-2626`）。项目中没有 transcript 级真实 `acousticCharacters`/phoneme alignment 字段；已有 `characterTimings` 只属于艺术字 overlay，不是剪辑声学权威。
5. 当前根因样本证据见 `research/current-media-evidence.md`：`得你` 被等分后，`37.190s` 的高能量局部谷值被误认作交界。纯波形局部低谷不足以代表语言学边界。

建议的上游兼容形状是给 segment 增加可选、带文本校验的声学字符边界（具体字段名由 design 决定）。新任务在 `process_job()` 中一次计算；旧 job/历史数据缺字段时可以在首次草稿校准时惰性计算并缓存，失败则走现有安全回退。消费前必须校验字符序列/版本指纹，防止用户修正文案后复用已过期的声学映射。

### 入口一：AI 文案删除

1. 服务端先由 `suggest_deletions()` 产生语义范围，再在 `process_job()` 中调用 `snap_suggestion_ranges_to_audio()`（`server/app.py:9185-9196`）。
2. `snap_suggestion_ranges_to_audio()` 规范文字语义、建立相邻保留字符限制，并通过共享声学边界写入物理 `start/end` 与语义 `originalStart/originalEnd`（`server/app.py:2377-2438`）。
3. 前端加载完成且没有旧草稿时，`seedAutomaticSuggestionRanges()` 将建议写入唯一的 `selectedRanges`；有 `original*` 时保留服务端给出的物理范围（`web/app.js:1321-1351`, `web/app.js:4702-4711`）。
4. 初始化后 `scheduleCutDraftSave()` 再把同一范围 PUT 到服务端，草稿 API 会按语义边界重新校准并返回最终范围。现有测试要求建议期和草稿期得到相同结果（`tests/app/test_cut_acoustic_boundaries.py:337-399`）。

### 入口二：手动点击文案删除

1. 文案点击事件从展示行读取源时间和文字，调用 `canonicalizeTextSelectionRange()` 扩到相交的自然字符单元，再用 `expandRangeToAdjacentSilence()` 形成保存前的临时物理范围，写入 `selectedRanges`（`web/app.js:5207-5253`）。
2. `canonicalizeTextSelectionRange()` 只定义删除哪些字符；`canonicalizeTextDeleteRange()` 保留已有 `originalStart/originalEnd`，允许服务端物理 `start/end` 独立扩张（`web/app.js:1565-1625`）。
3. AI 删除和手动文案删除从这里开始完全同路，都会在草稿 PUT 中调用 `align_cut_draft_text_ranges_to_audio()`（`server/app.py:10620-10638`）。因此当前高能量局部低谷误判会同时影响两者。

### 入口三：手动时间轴删除

1. pointer drag 创建 `timelineDeleteRanges`；`alignManualRangeToTranscript()` 名称虽含 align，实际只 clamp 到媒体时长，并把原始值原样复制到 `start/end/originalStart/originalEnd`（`web/app.js:1628-1646`, `web/app.js:3575-3599`）。
2. 用户确认后才由 `getCommittedTimelineDeleteRanges()` 纳入草稿、预览和生成（`web/app.js:1648-1652`, `web/app.js:3773-3784`）。
3. `buildPersistedCutDraftPayload()` 序列化 timeline 时调用 `serializableCutDraftRange()`，会丢弃 `originalStart/originalEnd` 和本地 id，只发送 `{start,end}`（`web/app.js:2190-2196`, `web/app.js:2225-2264`）。
4. 后端 PUT 对 `timelineRanges` 仅调用 `normalize_cut_draft_range()`，没有读取 PCM、文字边界或共享声学函数（`server/app.py:469-481`, `server/app.py:10639-10651`）。
5. 服务端响应应用函数只按 key 回写 `textRanges`，完全不处理 `timelineRanges`（`web/app.js:2333-2395`）。即使后端未来单独调整 timeline，当前前端也不会把最终物理范围同步到预览、撤销快照和 Store。

### 公共前端预览和草稿持久化

1. `getRetainedTranscriptRanges()` 用文字 `original*` 加已提交 timeline 范围决定哪些识别字符仍受保护；`getMergedSelection()` 再组合文字物理范围、空白范围和 timeline 范围，保护未明确删除的文字并执行合并（`web/app.js:1733-1771`）。
2. `buildEditedTimelineSpans()` 从 `getMergedSelection()` 建立源时间到剪后时间的 keep spans（`web/app.js:1791-1825`）。播放时 `skipSelectedRangeDuringPlayback()` 在原视频进入物理删除范围后 seek 到范围末尾（`web/app.js:3937-3959`）。浏览器预览是基于 `timeupdate`/frame callback 的跳转，不具备 FFmpeg 的采样级精度，但范围 owner 相同。
3. `buildLiveCutDraftState()` 把同一物理范围、映射后的 transcript 和时长发给顶层 EditorSuite（`web/app.js:2047-2082`）。`EditorProjectStore.selectCompositionRequest()` 同时把范围投影给公共 MediaController、预览和 compose 请求（`web/editor-project-store.js:1077-1113`）；EditorSuite 对同一个 frame 调用 media/preview/timeline/tool render（`web/editor-suite.js:1222-1239`）。
4. `updateSelectionSummary()` 是所有操作后的前端汇合点：失效时间缓存、更新 Store/预览/时间线并排队保存草稿（`web/app.js:2798-2858`）。
5. 草稿 payload 同时保存到 localStorage 和 `data/jobs/<job>/cut-draft.json`。服务端 PUT 以 revision 做保存前、耗时分析后两次并发校验，然后原子 replace 文件（`web/app.js:2398-2477`, `server/app.py:433-458`, `server/app.py:10590-10689`）。
6. `applyPersistedCutDraftAlignment()` 只有在响应对应的请求签名仍等于当前选择时才应用，应用后更新当前撤销快照而不新增操作（`web/app.js:2333-2395`）。统一 timeline 时必须复用同一并发门槛。

当前还有一个语义漂移点：`buildLiveCutDraftState()` 的 transcript 通过物理 keep spans 和 word midpoint 派生（`web/app.js:1904-1957`, `web/app.js:2047-2074`），而最终后端 transcript 使用独立语义删除范围。timeline 产生独立物理边界后，实时 transcript 也必须用 `original*` 决定删字、用物理范围只负责时间映射，否则预览艺术字/compose 草稿可能比最终 retained transcript 多删或少删一个字符。

### 后端范围解析、生成与 retained transcript

1. `resolve_cut_draft_delete_ranges()` 是当前草稿的媒体/语义投影 owner。它先规范 `textRanges[].original*`，把 timeline 精确范围视为显式文字删除，再保护剩余识别字符；媒体模式使用文字物理范围，语义模式使用文字语义范围，最后两种模式都直接加入 timeline 的同一个 `{start,end}`（`server/app.py:1858-1940`）。参数 `suggestions` 当前没有参与函数体计算。
2. `/cuts` 只收到扁平 `ranges`。它先归一化请求；仅当请求范围与保存草稿的直接合并结果或安全解析结果在 `15ms` 容差内匹配时，才从草稿恢复 `requestedRanges`（物理）和 `transcriptRanges`（语义）（`server/app.py:1645-1654`, `server/app.py:10912-10964`）。不匹配或无草稿时，直接把请求范围同时当作媒体和 transcript 删除范围。
3. `/compose` 使用相同的匹配/恢复逻辑，并把物理范围交给统一 preview composition job（`server/app.py:11718-11823`）。前端 compose 直接从当前 Editor frame POST，没有等待 cut draft save queue 的显式门槛（`web/editor-suite.js:1065-1089`）。`generateCut()` 同样直接从当前 `getMergedSelection()` POST（`web/app.js:4918-4953`）。用户刚编辑就立即生成时，保存草稿可能仍在队列中，这是统一声学边界后必须关闭的竞态。
4. `process_cut_job()` 和 `process_preview_composition_job()` 都复制已解析物理范围，不再做声学吸附；它们用物理范围调用 `render_cut_video()`，用语义范围决定保留哪些文字，再用物理范围重映射剪后时间（`server/app.py:9216-9278`, `server/app.py:9395-9485`）。
5. `render_cut_video()` 对每个 keep span 使用视频 `trim` 和音频 `atrim`，最多 8ms fade 后 concat、响度归一化并 AAC 编码（`server/app.py:3515-3555`）。FFmpeg 只忠实执行物理范围，不会修复错误边界。
6. `build_retained_transcript()` 以第一个 `delete_ranges` 参数判断字符/词是否删除，以 `timeline_delete_ranges` 映射剪后时间，因此已支持“语义删除”和“物理裁剪”分离（`server/app.py:3227-3409`）。文字修正后重建 transcript 时优先读 `edit.transcriptRanges`，旧任务兼容回退到 `requestedRanges/ranges`（`server/app.py:10754-10767`, `server/app.py:10818-10831`）。

### Exact Unification Points

1. **一次性字符/音素对齐 owner**：`process_job()` 在 `transcribe_audio()` 后、AI 建议前已经同时拥有 transcript 和解码 PCM（`server/app.py:9149-9195`）。在此生成可复用的真实声学字符边界；`transcript_acoustic_character_units()` 改为优先消费并严格校验该边界，旧数据才回退到现有 raw token 等分或安全语义边界。
2. **单一草稿物理计划 owner**：将 `align_cut_draft_text_ranges_to_audio()` 提升为同时处理 `textRanges` 和 `timelineRanges` 的 cut-draft boundary resolver，在一次 PCM/对齐读取中解析全部端点。`noSpeechRanges` 继续走识别文字扣除规则，不做字符/音素吸附。
3. **统一边界不等于统一语义**：text 仍先规范为完整字符；timeline 仍保留精确用户选择，不做字符扩展，只在靠近可证明语音交界时把物理端点吸附到该交界。下一保留字符/音素真实起音是硬上限，不能用固定毫秒扩张。
4. **timeline 双范围 DTO**：给 `timelineRanges` 增加可选 `originalStart/originalEnd`（以及需要时的稳定 client key）；旧草稿缺字段时按 `original == physical` 读取。后端 media 投影用 `start/end`，transcript 投影用 `original*`。
5. **前端响应原子应用**：扩展 `applyPersistedCutDraftAlignment()`，在同一个 expected-signature 校验下同时回写 text/timeline，更新当前 history snapshot、重建 `getMergedSelection()`、Store frame、播放跳过和时间线 clip。不能创建第二套删除状态。
6. **实时 retained transcript 分离**：前端列表和 live transcript 用 text/timeline 的 `original*` 判定删字；源到剪后时间、播放和媒体预览只用物理 `start/end`。这应与后端 `build_retained_transcript(delete_ranges, timeline_delete_ranges=...)` 的双输入合同同构。
7. **生成前同步门槛**：`generateCut()` 和 EditorSuite `generateCurrentPreview()` 在构造最终 frame/request 前必须等待当前 cut draft PUT 完成并确认 revision，然后重新读取最终物理 ranges。请求可新增可选 `cutDraftRevision`，新前端让服务端按 revision 读取权威草稿；旧客户端只传 `ranges` 时继续保持现有精确请求行为。
8. **生成不再校准**：`/cuts`、`/compose`、`process_*` 和 FFmpeg 继续禁止二次吸附。这样用户看到的 preview、保存的草稿、单独剪辑和统一合成严格使用同一物理计划。

### Compatibility Constraints

- `textRanges[].originalStart/originalEnd` 仍是文字删除语义权威，不能用强制对齐结果反写；现有 `start/end` 物理语义保持不变。
- `timelineRanges` 当前被规范和测试锁定为精确时间。改为“语义精确、物理可安全吸附”是本任务已确认的产品行为变更，必须同步更新 `.trellis/spec/backend/media-and-timeline.md:137-179,255-259`、`.trellis/spec/frontend/architecture-and-state.md:121-132` 和 `.trellis/spec/frontend/ui-and-interactions.md:74-79`，不能只改实现。
- 手动 timeline 仍允许删除一个字符时间的一部分；声学吸附不能先把它 canonicalize 成完整字符，也不能让相邻自动范围借 `0.12s` merge 容差吞掉其余字符。现有保护顺序必须保留。
- 旧 `cut-draft.json` 是 schema v1，缺少 timeline `original*`。兼容读取必须逐条回退 `originalStart=start`, `originalEnd=end`，下次正常 PUT 可惰性补齐；不得批量改写真实 `data/jobs`。
- 新的声学字符字段必须可选并逐 segment 回退。用户修改 transcript 文本后，只有字符序列/版本仍匹配时才能复用；否则重新对齐或回退，不能把旧字符时间套到新文字。
- 音频解码、强制对齐或模型映射失败时：text 回退规范后的字符语义范围；timeline 回退用户精确原始范围。失败不能沿用客户端伪造或上一次漂移的物理边界。
- 下一段保留语音的真实起音必须是硬边界。候选高能量、低置信度、对齐冲突或两个删除范围夹住短保留字符时，宁可回退原范围，也不能删除下一段声音。
- AI 建议期和草稿 PUT 必须调用同一纯 resolver/同一缓存对齐数据；否则首次页面显示和保存后预览会跳变。
- `ranges/requestedRanges`（媒体）与 `transcriptRanges`（语义）字段和历史兼容回退必须保留。`build_retained_transcript()` 的双范围接口不应合并。
- `CutRequest`/`PreviewCompositionRequest` 旧调用只提供 ranges，后端无法从扁平范围可靠推断来源。若不带匹配 draft/revision，继续按现有精确请求处理；新 UI 必须走保存并等待校准的权威路径。
- 如果新增公开 Pydantic model，需要同步 `server/schemas.py.__all__`、`server.app` 显式导入和 `tests/app/test_schemas.py:4-43`。

### Existing Tests and Required Changes

可保留并扩展的现有回归：

- `tests/app/test_cut_acoustic_boundaries.py:11-127` 覆盖“给一”“得你”同 token 内尾音；`337-399` 锁定 AI 建议与 draft 共用边界；`402-506` 覆盖单调斜坡和增益稳定；`593-625` 禁止删除终点进入保留字符后的静音；`628-670` 锁定保存的物理/语义分离。
- `tests/app/test_cut_draft.py:316-409` 覆盖 PUT 校准、相邻保留字限制和幂等；`412-513` 覆盖自然字符而非 raw token；`958-1007` 覆盖 semantic/media 双范围；`1010-1073` 覆盖删除“觉得”仍保留“你”；`1123-1227` 覆盖短保留字和部分手动删除保护。
- `tests/app/test_cut_rendering.py:297-374` 锁定 `/cuts` 使用保存物理范围但 transcript 使用语义范围；`377-458` 锁定跨界 `得你` 后保留“你”；`465` 起有真实 FFmpeg 音频规范化样片。
- `tests/app/test_composition.py:49-225` 锁定 compose 只消费当前 cut 范围且生成阶段不再次吸附。
- `tests/app/test_frontend_contracts.py:1454-1544` 锁定前端保留服务端物理范围；`tests/app/browser/test_editor_workflows.py:183-217` 锁定草稿刷新恢复；`1724-1781` 锁定 compose 请求来自当前 draft 物理范围。

必须修改的旧精确范围契约：

- `tests/app/test_cut_draft.py:516-548` 当前明确断言 manual timeline 保持 `{0.25,0.5}` 精确不变。应改为：语义 `original*` 保持精确；靠近可靠声学交界的物理 `start/end` 可吸附；无可靠证据时仍精确回退。
- `tests/app/test_frontend_contracts.py:381-406` 锁定页面文案“选区保持精确范围”；`552-580` 明确禁止 manual helper 使用文字/静音边界。这些断言和页面文案必须同步产品新语义。
- `.trellis/spec/frontend/ui-and-interactions.md:78`、`.trellis/spec/frontend/architecture-and-state.md:132`、`.trellis/spec/backend/media-and-timeline.md:138,179,259,272` 均锁定 manual timeline 不吸附，需通过 spec update 正式修改。

新增测试缺口：

- 强制对齐单元/性质测试：高能量局部谷值不能获得字符交界资格；相同语音在多组非削波增益、采样率和声道输入下边界稳定；“得你”删除终点不晚于“你”的真实起音。
- 对齐缓存/兼容测试：新 job 复用一次对齐结果；旧 job 惰性生成；缺字段、文本修正导致 fingerprint 不匹配、解码/对齐失败均安全回退。
- draft API 测试：一次 PUT 同时返回 text/timeline 的双范围，revision 冲突不写部分结果，重复 PUT 幂等，timeline `original*` 在刷新、撤销/重做后不漂移。
- 范围解析测试：timeline 物理范围用于 media，timeline 原始范围用于 transcript；部分手动删除仍保护词的其余片段；两个物理范围不能跨短保留字符合并。
- 前端 Node/浏览器测试：拖拽后先显示 pending 精确范围，服务端响应后原子更新到实际物理 clip；旧响应不覆盖新拖拽；不会增加额外 undo revision；列表删除态仍按原始范围；播放跳过、公共 Store、compose payload 与服务端草稿一致。
- 生成竞态测试：点击删除后立即点 `/cuts` 或统一生成，必须等待最新 draft revision；捕获的请求/最终 FFmpeg ranges 等于响应后的物理范围，不等于保存前临时范围。
- 真实媒体测试：对当前问题样本或脱敏短切片同时断言删除尾音窗口能量/频谱不再出现在拼接点，并断言下一保留字起音窗口仍存在；只断言时间数值不足以防止同类复发。

## Related Specs

- `.trellis/spec/backend/media-and-timeline.md:5-15,26-31,51-58,133-232,234-287`
- `.trellis/spec/backend/persistence-and-jobs.md:3-23,25-53`
- `.trellis/spec/backend/quality-guidelines.md:3-30`
- `.trellis/spec/frontend/architecture-and-state.md:80-132,172-221`
- `.trellis/spec/frontend/ui-and-interactions.md:72-82,125-177`
- `.trellis/spec/testing/index.md:13-55`
- `.trellis/spec/testing/browser-workflows.md:3-42`
- `.trellis/spec/guides/cross-layer-thinking-guide.md:3-35`

## External References

- None. 本文件只做当前仓库数据流和契约研究；具体强制对齐引擎、模型大小、许可和部署方案应在独立 research topic 中比较。

## Caveats / Not Found

- 当前仓库没有 transcript 级真实字符/音素强制对齐实现或持久字段；`timestamp_alignment_enabled=True` 不等于代码已经取得字符时间。
- 当前 `timelineRanges` 没有稳定持久 id，也没有 semantic/physical 双范围；异步服务端回写只能按顺序或新增兼容 key 关联，design 需要明确。
- 当前 `/cuts` 和 `/compose` 只接收扁平 ranges，不能可靠区分 AI、手动文案和手动 timeline 来源；若草稿尚未保存或范围不匹配，会绕过语义/物理分离。
- 当前真实浏览器测试没有覆盖手动 timeline 的声学校准、生成前 save race 或最终音频内容；现有真实 FFmpeg 测试主要验证可生成和响度规范化。
- 本 topic 未重新分析用户 MP4；真实边界和编码排除证据直接引用同任务的 `research/current-media-evidence.md`。
