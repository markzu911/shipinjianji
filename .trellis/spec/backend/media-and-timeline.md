# 媒体与时间轴

## 时间轴语义

系统同时存在源视频时间和剪后时间：

- ASR word/segment 时间戳首先锚定源视频。
- 删除区间经 `normalize_delete_ranges`、`build_keep_ranges` 和音频边界吸附形成物理剪切计划。
- 剪后 transcript、艺术字和画中画需要使用 retained transcript/source anchor 映射，不能凭相同秒数猜测。
- 预览和最终合成必须消费同一组归一化 overlay 数据。

任何跨剪辑边界功能都应明确输入时间轴、输出时间轴和转换函数，并增加往返测试。

## FFmpeg/FFprobe

- 可执行文件通过 `get_ffmpeg_binary` 获取。
- 统一经 `run_ffmpeg` 执行需要取消支持的生成命令。
- 参数使用列表，不启用 shell 字符串拼接。
- 先 probe 时长/尺寸；不合法媒体在进入后台长任务前失败。
- 输出写入同目录临时文件，成功后原子替换。
- 文字资源使用 UTF-8 临时文本/filter script，避免直接把长文案塞入命令行。

## 渲染契约

- `render_cut_video` 只负责删除范围后的基础成片和音频规范化。
- `render_art_text_video` 使用已经归一化的文字 overlay；安全区由 `ART_TEXT_SAFE_AREA_RATIO` 保护。
- `render_picture_in_picture_video` 使用已确认素材和标准化位置/尺寸。
- `process_preview_composition_job` 是剪辑、艺术字、画中画统一预览链路；修改任一层时同时验证单功能和组合功能。

画中画宽度只要求 finite 且不小于 `0.15`，不得添加任意产品最大值。`x/y` 始终表示素材中心；小于主画面时坐标限制在完整可见区，大于主画面时允许负 overlay 坐标并按中心裁切：

```text
min_x = min(0, main_w - overlay_w)
max_x = max(0, main_w - overlay_w)
x = clamp(main_w * center_x - overlay_w / 2, min_x, max_x)
```

`y` 使用同一公式。公共浏览器 compositor、草稿、compose DTO 和 FFmpeg 必须保留相同 width；禁止浏览器接受 175% 而后端截断，或浏览器居中裁切但 FFmpeg 固定从左上角裁切。

## 资源与安全

- 临时图片、视频、字幕文本和 filter script 必须位于 job 工作目录。
- 下载外部视频后重新 probe/规范化，不信任扩展名或响应声明。
- 用户可控颜色、字体、位置、尺寸、时长先经过白名单或 clamp。
- 不允许输出路径逃逸 `DATA_DIR`，也不允许清理任意用户路径。

## 验证重点

- 删除边界不会吞掉保留语音；媒体吸附不改变文字选择。
- 原视频直接加艺术字/画中画与剪后源都可用。
- 预览组合与最终输出在时间、位置和样式上相同。
- Windows 长命令、缺失字体、取消、失败清理和音频规范化有回归测试。

参考：`server/app.py` 的 `timeline_after_deletions`、`build_retained_transcript`、`render_*`；`tests/test_app.py` 的 cut boundary、art text、picture-in-picture 和 preview composition 用例。

## 场景：文字草稿在预览前完成音频边界校准

### 1. Scope / Trigger

- 文字删除范围来自 ASR word/segment 时间戳时，必须在进入公共预览和最终生成前吸附到真实音频低谷。
- 时间轴手动范围和已检测的无声范围不参与这次文字边界校准，但草稿解析为媒体范围时必须同样保护未明确删除的识别文字。

### 2. Signatures

- API：`PUT /api/transcriptions/{job_id}/cut-draft`
- 后端：`align_cut_draft_text_ranges_to_audio(media_path, text_ranges, segments, duration)`
- 后端：`refine_shared_character_boundary(left, right, fallback, samples, sample_rate, *, deletion_on_left, allow_token_extension=True)`
- 后端：`find_quiet_token_extension_boundary(left, right, fallback, samples, sample_rate, *, deletion_on_left, enabled)`
- 后端：`resolve_cut_draft_delete_ranges(draft, suggestions, segments, duration, *, use_text_semantic_boundaries=False)`
- 后端：`normalize_delete_ranges(ranges, duration, protected_ranges=None)`
- 后端：`subtract_protected_ranges(ranges, protected_ranges, *, minimum_duration=0.0)`
- 前端：`applyPersistedCutDraftAlignment(draft, expectedSignature)`

### 3. Contracts

- `textRanges[].originalStart/originalEnd` 表示删除哪些文字，不因波形吸附而改变。
- `textRanges[].start/end` 表示真实媒体删除范围；草稿 PUT 响应可以在上一保留文字结束与下一保留文字开始之间扩大，禁止为草稿对齐传入 head/tail guard 穿越保留文字。
- `adjacentSilenceBefore/After` 必须按校准后的物理边界重新计算。
- 音频解码或分析失败时，物理范围回退到 `originalStart/originalEnd`，不沿用客户端传入的可能越界 `start/end`。
- `noSpeechRanges` 先扣除全部识别文字；文字物理扩展和空白范围组成自动删除集后，还必须扣除“识别文字 - 文字语义删除 - 已提交手动时间轴删除”所得的保留片段。
- `normalize_delete_ranges` 的 `0.12s` 容差只能合并不穿越 `protected_ranges` 的区间；手动范围只放开它精确覆盖的文字片段，不能使整个识别词失去保护。
- 前端只有在当前草稿签名仍等于本次请求签名时才能应用响应；应用后更新当前撤销快照，不新增撤销记录。
- 剪辑任务的 `ranges/requestedRanges` 保持物理预览范围，另以 `transcriptRanges` 保存语义文字范围；生成和统一合成使用前者裁切媒体、使用后者重建剪后 transcript。
- 后续修正文案而重建剪后 transcript 时优先读取 `transcriptRanges`，历史任务缺少该字段时兼容回退到 `requestedRanges/ranges`。
- `/cuts`、`/compose` 和公共预览继续消费草稿中同一组 `start/end`，生成阶段不得再次吸附。
- 删除终点只能从语义 fallback 向后移动，删除起点只能向前移动；任何反方向候选均无效。fallback 的多尺度 RMS 已不高于 `CUT_LOW_ENERGY_RMS_THRESHOLD` 时保持不动，避免安静边界重复漂移。
- 字符中心走廊只接受内部局部低谷或足够安静且相对 fallback 明显改善的方向端点；单调斜坡和响亮字符中心不能充当共享边界。
- 若删除起点的字符中心走廊最佳候选仍高于绝对安静阈值，可以向前扩展到上一保留字符所属原始 ASR token 的起点，选择离 fallback 最近且 RMS 不高于阈值的安静点。token 只限定删除起点的补充声学走廊，不能被整体加入删除范围，也不能用固定毫秒扩张替代。
- 删除终点禁止越过字符中心走廊继续搜索下一保留字符的 token；下一字说完后的静音不能证明它的起音可以删除。
- 一个保留字符两侧都紧邻删除范围时禁用 token 补充走廊，防止两个物理范围从两侧夹穿该短字符；无绝对安静证据时继续使用字符走廊结果或语义 fallback。

### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| job、媒体或时长无效 | 沿用既有 `404` / `409` 契约，不写草稿 |
| range 非有限值或 `end <= start` | `400`，不写部分草稿 |
| 草稿 revision 过期 | 校准前或写入前返回 `409` |
| 音频解码/分析失败 | 回退到语义文字范围，草稿仍可安全保存 |
| 自动空白部分/完全覆盖识别文字 | 扣除文字后只保留达到最短时长的无文字碎片；完全覆盖时不产生自动删除 |
| 小于 `0.12s` 的保留文字位于两个自动范围之间 | 保持两个范围，不用合并容差跨过该文字 |
| 手动时间轴范围只覆盖一个识别词的部分 | 仅该精确片段可删除，词的其余片段继续作为自动合并保护区 |
| 保存期间前端又发生编辑 | 只推进 revision，不用旧响应覆盖新编辑；队列继续同步新状态 |
| 删除起点字符中心走廊只有响亮相对低谷，上一 token 内存在真静音 | 使用上一 token 内离 fallback 最近的绝对安静点 |
| 删除终点字符中心走廊不足，但下一保留字符说完后存在静音 | 保持字符走廊结果或 fallback，不进入下一 token 尾部 |
| fallback 已安静、方向侧只有单调斜坡或静音位于 token 外 | 保持 fallback，不扩大搜索 |
| 单个保留字符夹在两个删除范围之间 | 禁用两侧 token 补充走廊，保留字符物理核心不被覆盖 |

### 5. Good / Base / Bad Cases

- Good：ASR 尾点落在低音量尾音中，物理 `end` 延伸到相对更低的局部谷值，文字 `originalEnd` 不变。
- Good：删除起点前的真实停顿被 ASR 均摊到上一保留字符时间内，字符中心走廊只有响亮低谷时，起点在上一 token 内向前移动到最近真静音，但语义范围不变。
- Base：ASR 边界已经位于同等低的谷值，或者更低谷值落在保留文字内，返回语义边界/保留文字边界，重复保存不继续漂移。
- Bad：把单调衰减的响亮采样点当低谷，向反方向移动边界，或直接把相邻 ASR token 整体扩进删除范围。

### 6. Tests Required

- 单元测试：低整体音量样本仍按相对能量改善识别尾音，不依赖固定 RMS 阈值。
- 单元测试：删除起点只向前、终点只向后；拒绝单调斜坡和响亮方向端点，接受足够安静的方向端点，fallback 已安静时保持不动。
- 单元测试：删除起点字符走廊仅有响亮相对低谷而上一 token 内存在真静音时选择最近安静点；静音位于 token 外时回退；删除终点不得吸附到下一保留字符说完后的静音；短保留字符夹在两段删除之间时禁用扩展。
- 单元测试：自动空白部分/完全覆盖文字、两个自动范围夹住小于 `0.12s` 的保留词、手动范围只删除词的部分时，断言保留片段不被合并穿越。
- API 测试：草稿 PUT 返回校准后的 `start/end`、原始语义边界和重算的相邻静音，并验证前后两侧保留文字限制、分析失败安全回退与重复 PUT 幂等。
- 生成回归：`process_cut_job` 与组合生成不得再次调用边界吸附，最终 `ranges` 等于已保存草稿物理范围；物理范围延长时 `transcriptRanges` 仍只删除选中的语义文字。
- 前端契约：校准响应更新预览和当前撤销快照，旧请求响应不能覆盖并发新编辑；真实浏览器验证删除空白不会使相邻文字进入删除态或从预览时间轴消失。

### 7. Wrong vs Correct

```python
# Wrong: 用容差合并已扣除识别文字的自动范围，会把短保留词合并回去。
media_ranges = normalize_delete_ranges(automatic_ranges, duration)

# Correct: 合并容差始终感知精确保留片段。
media_ranges = normalize_delete_ranges(
    [DeleteRange(**item) for item in automatic_and_manual_ranges],
    duration,
    protected_ranges=retained_text_fragments,
)
```

```python
# Wrong: 把下一保留字符 token 尾部的静音当作删除终点，会连字一起吞掉。
physical_end = next_retained_asr_token["end"]

# Correct: token 补充搜索只用于删除起点，并且只向上一保留 token 内移动。
physical_start = refine_shared_character_boundary(
    retained_character,
    deleted_character,
    semantic_start,
    samples,
    sample_rate,
    deletion_on_left=False,
)
```

## 场景：ASR 原始 word 与展示分词使用双层时间契约

### 1. Scope / Trigger

- 新转写、草稿文字删除、剪后 transcript 或任何读取文字时间戳的功能都必须区分模型原始 word 与中文展示分词。
- 该字段跨越转写 API、浏览器草稿、剪辑预览和最终生成，因此修改任一消费者时都必须验证字符级保护和兼容回退。

### 2. Signatures

- 响应字段：`segments[].asrWords?: Array<{ text: string, start: number, end: number }>`
- 后端：`build_sentence_segments(words, asr_words=None)`
- 后端：`transcript_segment_timed_items(segment, *, require_text)`
- 后端：`transcript_character_units(segments)`
- 后端：`canonicalize_transcript_semantic_ranges(ranges, segments, duration)`
- 前端：`getSegmentTokens(segment)` / `getTranscriptCharacterUnits(segments = null)`
- 前端：`canonicalizeTextSelectionRange(range)`

### 3. Contracts

- `segments[].asrWords` 原样保留 ASR 返回的 word 起止边界；标点校对可以改变 `text` 的标点附着，但不得重算 `start/end`。
- `segments[].words` 继续由 Jieba 自然分词生成，用于文案展示、逐字编辑、AI 语义分析和字符时序派生；原始 `asrWords` 只作声学/模型参考。
- 每段独立选择第一个有效时间层 `words -> asrWords -> segment`，再把有文字的条目按可发声字符均分时间。不得用全局字段存在性决定其他段，也不得优先使用跨自然词边界的原始 ASR token。
- 文案点击、AI 建议初始化、草稿恢复和撤销/重做把相交范围扩展到完整字符单元后写入 `originalStart/originalEnd`；`start/end` 仍可独立扩展到安全静音边界。
- 后端在草稿 PUT、预览/生成范围解析和 retained transcript 构建前重复执行字符级规范化，不信任旧客户端或伪造客户端提交的局部字符范围。
- 音频低谷吸附的边界不能越过上一保留字符结束或下一保留字符开始；多个吸附范围的 `0.12s` 合并同样不得跨过短保留字符。
- `timelineRanges` 是用户明确选择的时间轴范围，不做字符扩展，继续允许精确删除字符时间的一部分。
- 剪后 transcript 必须同步保留和重定时 `words` 与可选 `asrWords`；当删除只覆盖原始 ASR token 的部分字符时，可以把其保留部分拆成新的时间条目。旧数据无需迁移。

### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| `words` 有有效条目 | 按当前段自然词逐字符派生删除和保护单元 |
| `words` 缺失、为空或全部时间无效 | 仅该段回退到有效 `asrWords`，不影响其他段 |
| `asrWords` 也缺失或无有效条目 | 从 segment 文本和时间逐字符回退 |
| 原始 ASR token 跨越两个自然词 | 删除以前者派生字符为准，不吞掉后一自然词的字符 |
| 文字范围只覆盖字符时间的一部分 | `originalStart/originalEnd` 扩展到该字符边界 |
| 两个自动范围夹住小于 `0.12s` 的保留字符 | 保持两个范围，禁止容差合并跨越字符 |
| 手动时间轴范围只覆盖字符的一部分 | 保持精确范围，不扩展 |
| 范围不与任何字符单元相交 | 保持已归一化范围，继续走既有范围校验 |

### 5. Good / Base / Bad Cases

- Good：`words=觉得/你`、`asrWords=觉/得你` 时，删除“觉得”最多结束于 `0.4s`，“你”继续保留；`words=一起/给/一起/给` 与 `asrWords=一起/给一/起给` 同理。
- Base：历史段落没有 `words` 时，从该段 `asrWords` 或 segment timing 逐字符派生；其他有 `words` 的段落不受影响。
- Bad：把 `asrWords=得你` 当成不可分割单元，使删除“觉得”扩展到“你”；或者每个范围虽已夹在字符边界内，最后仍用 `0.12s` 容差跨过中间短字符合并。

### 6. Tests Required

- 转写单元测试：多字 ASR word 的原始时间保存在 `asrWords`，Jieba `words` 可使用不同分词，标点校对不改变原始时间。
- 后端单元/API 测试：局部文字范围经草稿 PUT 扩展到相交字符，手动范围保持精确；混合段落按段回退 `words -> asrWords -> segment`。
- 建议/生成测试：低谷吸附不越过前后保留字符，两个自动范围不跨短保留字符合并，公共预览、剪辑和组合消费同一安全范围。
- retained transcript 测试：删除“觉得”仍保留“你”；跨界 ASR token 的保留字符被拆分、重定时，`words` 与 `asrWords` 一致。
- 前端契约/浏览器测试：文案选择、草稿恢复、撤销/重做和刷新均保持字符级结果；375px 下文字和操作按钮无溢出。

### 7. Wrong vs Correct

```python
# Wrong: 原始 ASR token 可能跨过自然词边界，不能作为删除最小单元。
items = segment.get("asrWords") or segment.get("words") or [segment]

# Correct: 每段先选自然词层，再把带时间文本拆为字符安全单元。
items = segment.get("words") or segment.get("asrWords") or [segment]
character_units = [
    unit
    for item in items
    for unit in split_timed_text_units(item["text"], item["start"], item["end"])
]
```
