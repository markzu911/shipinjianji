# 媒体与时间轴

## 时间轴语义

系统同时存在源视频时间和剪后时间：

- ASR word/segment 时间戳首先锚定源视频。
- 删除区间经 `normalize_delete_ranges`、`build_keep_ranges` 和音频边界吸附形成物理剪切计划。
- 剪后 transcript、艺术字和画中画需要使用 retained transcript/source anchor 映射，不能凭相同秒数猜测。
- 预览和最终合成必须消费同一组归一化 overlay 数据。
- 有效 word 或已有 character timing 是全文艺术字的语义时间权威；音频 quiet range 不得压缩、重排或覆盖这些边界。静音只允许在缺少可靠文字时间时作为降级参考。
- 全文艺术字在逐字时间写回 cue 后必须再次按 `trackId` 规范边界：任何正值重叠（包括小于 `1ms` 的误差）都必须只把前一 cue 的 `end` 严格收紧到后一 cue 的真实 `start`，并把前一 cue 的全部 `characterTimings` 按原顺序约束在新范围内。不得后移后一 cue、删除字符、改写 `sourceStart/sourceEnd` 或触碰基础视频和音频。`normalize_text_overlays()` 必须复用同一规范化入口，避免预览与 compose 产生两套时间。
- 实时艺术字 AI 草稿的 `start/end/duration` 属于剪后时间，`sourceStart/sourceEnd` 属于原片时间。关键帧样本必须显式携带 `{mediaTime, displayTime}`：FFmpeg seek 使用 `mediaTime`，联系表标签和模型提示使用 `displayTime`。

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
- `draftTranscript` 属于不可信浏览器输入；段落、`words/asrWords` 的结构、数量、文本总量、有限区间和成对 source anchor 必须在进入后台任务前统一校验，旧请求可继续省略草稿字段。
- 不允许输出路径逃逸 `DATA_DIR`，也不允许清理任意用户路径。

## 验证重点

- 删除边界不会吞掉保留语音；媒体吸附不改变文字选择。
- 原视频直接加艺术字/画中画与剪后源都可用。
- 预览组合与最终输出在时间、位置和样式上相同。
- Windows 长命令、缺失字体、取消、失败清理和音频规范化有回归测试。

参考：`server/app.py` 的 `timeline_after_deletions`、`build_retained_transcript`、`render_*`；`tests/test_app.py` 的 cut boundary、art text、picture-in-picture 和 preview composition 用例。

## 场景：语义保留字符投影到物理剪后时间

### 1. Scope / Trigger

- 修改文字删除、手动时间轴删除、cut-draft GET/PUT、剪辑/组合生成、完成稿文案恢复或浏览器公共时间轴时，必须使用本场景。
- 字符身份与媒体边界属于两层权威：语义范围只决定保留哪些字符，物理范围只负责把已保留字符映射到剪后时间。

### 2. Signatures

- 后端：`build_retained_transcript(segments, delete_ranges, output_duration, timeline_delete_ranges=None, timeline_semantic_delete_ranges=None, audio_quiet_ranges=None, alignment_cache=None, editable_segments=None)`。
- 后端：`load_acoustic_alignment_cache(media_path, segments, job_directory)` 只读并复验已有 sidecar，不运行模型。
- API：`GET|PUT /api/transcriptions/{job_id}/cut-draft -> {cutDraft, retainedTranscript}`。
- 前端：`getCurrentRetainedProjection()`、`applyServerRetainedProjection(transcript, {jobId, signature, revision})`、`loadServerRetainedProjection(jobId, signature, revision)`。
- Store：`transcriptTextChanged` 可携带 `cutTranscript`，在同一 revision 中更新文案和 cut transcript。

### 3. Contracts

- `delete_ranges` 只使用 `textRanges[].originalStart/originalEnd` 归一化后的文字语义范围，并按展示字符时间决定字符身份；`timeline_semantic_delete_ranges` 只使用 `timelineRanges[].originalStart/originalEnd`，且仅与完整句段复验有效的 forced 字符区间比较。两种来源不得先合并再按粗 ASR 时间统一判删。
- `timeline_delete_ranges` 使用所有物理 `start/end`，只执行 `timeline_after_deletions()` 时间扭曲。forced 缺失或无效时，timeline-only 删除保守保留不确定字符，但不得缩小、扩大或取消已经确认的媒体物理删除范围。显式空列表不得按 truthy fallback 回退到另一层范围。
- timeline-only 字符身份要求 forced 区间与手动语义范围的重叠量严格大于半个字符时长。小于等于半字的边缘擦碰不得整字删除，超过半字的明确覆盖仍按用户意图删除。
- 已有 sidecar 只有在字符顺序、finite 单调区间和 segment 包络复验全部通过时才提供 forced timing；无效或缺失时使用粗时间，但不得删除语义保留字符，也不得调用 FunASR 或写 sidecar。
- `segments/words/asrWords` 输出 edited `start/end` 和成对 `sourceStart/sourceEnd`；segment 还携带 `sourceSegmentIndex`。edited 时间必须有限、正时长、单调且不越过 `duration`。
- `editable_segments` 只有在 spoken-character identity 构成完整、按 source 顺序排列的 source transcript 分区时才启用；每个 retained segment 携带当前数组索引对应的 `editableSegmentId`。缺失、非法、错序或不完整的历史数据必须整体回退 source-segment 分组，不能部分安装或使 API 失败。
- 同一 editable segment 的内部字符被删除时，删除前后必须输出两个不连续 retained runs；两段可共享 `editableSegmentId`，但不得跨删除洞合并，且各自保留独立 word/source anchors。editable split/merge/text 操作都要同步刷新已有 completed edit 的派生 transcript。
- `retainedTranscript` 是 source transcript、草稿 revision 和既有 alignment 的派生响应，不属于 `CutDraftRequest`，不写入 `cut-draft.json`。旧草稿在 GET 时只读重建，不迁移。
- 浏览器只在 job id、语义 signature 和 revision 同时匹配时安装服务端投影；过期或旧服务响应保持本地语义投影。文字保存应在一次 `transcriptTextChanged` 中原子安装当前投影，不改变 cut ranges、split track、art/PiP source anchors 或 `timingRevision`。
- `/cuts`、`/compose`、完成 edit 恢复与后续文案修正使用同一 helper；历史 edit 只有在 `transcriptRanges` 字段缺失/无效时才回退 `requestedRanges/ranges`，显式 `transcriptRanges=[]` 表示不删文字。
- `transcriptRanges` 保持文字与手动时间轴语义范围合并后的公开兼容形状；消费当前草稿的新 edit 同时保存 `textTranscriptRanges` 和 `timelineTranscriptRanges`。后台剪辑、组合生成和 completed edit 重建优先使用来源字段，历史 edit 缺失任一来源字段时整体回退旧扁平语义，不能部分安装。
- 只有请求携带并通过校验的 `cutDraftRevision` 才证明它消费当前草稿，进而允许保存上述来源字段。旧请求即使 ranges 数值恰好等于草稿结果，也只能保留扁平 `transcriptRanges` 兼容语义，禁止按秒数相等猜测范围来源。

### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| semantic range 删除字符，物理 range 更宽或覆盖下一个粗 token | 仍按 semantic range 保留字符，再用 forced/coarse timing 映射 |
| timeline range 与粗字符时间重叠，但结束于有效 forced 起音之前 | 媒体范围保持不变，字符保留并从 forced 起音投影 |
| timeline range 与有效 forced 字符区间相交 | 删除该字符；文字选区的判定方式不受影响 |
| timeline range 只擦到 forced 字符 `22ms` 或 `60ms`，字符时长 `180ms` | 未超过半字，保留字符；媒体范围保持精确 |
| timeline range 命中粗时间，但 forced 缺失或整段复验失败 | timeline-only 字符保守保留，媒体仍按原物理范围裁切 |
| 物理映射使一个或多个保留字符坍缩 | 保留全部字符，并在输出时长内分配最小正时长 |
| sidecar 缺失、文字错序、时间非单调或越出包络 | 整个受影响 segment 回退粗时间，不运行模型 |
| cut-draft GET/PUT 的 job、signature 或 revision 过期 | 前端拒绝服务端投影，不覆盖当前编辑 |
| 旧服务不返回 `retainedTranscript` | 使用本地语义投影，保存流程继续兼容 |
| 完成 edit 显式保存 `transcriptRanges=[]` | 保留全部文字，只用 `ranges` 扭曲时间 |
| history edit 缺少 `transcriptRanges` | 兼容回退 `requestedRanges/ranges` |

### 5. Good / Base / Bad Cases

- Good：语义只删第一处“一起给”，即使物理范围覆盖下一处“一起”的粗时间，输出仍为“所有人一起给你画”，并优先使用下一处“一起”的有效 forced 起音。
- Good：手动空白选区 `32.053-39.829s` 虽与下一字粗时间 `37.120-37.480s` 重叠，但下一字 forced 起音为 `39.850s`，因此物理空白被删除而下一字保留。
- Good：跨既有删除洞的选区保存为多个源 `timelineRanges`；右段与 `39.850-40.030s` 字符只重叠 `22ms` 或 `60ms` 时字符保留，而 `39.860-40.000s` 的明确覆盖超过半字并删除该字符。
- Base：无 sidecar 的旧 job 对 timeline-only 字符使用保守保留；旧客户端和历史 edit 仍可省略新增来源字段并走旧兼容读取。
- Bad：把文字范围与 timeline 范围先压成一份 `delete_ranges`，再统一与粗 ASR 字符时间相交，会把真实起音仍在选区外的后文误删。

### 6. Tests Required

- 后端纯函数：语义/物理范围错位、显式空物理范围、timeline 仅命中粗时间/forced 边缘擦碰/超过有效覆盖阈值/forced 缺失四种字符身份、单个与多个坍缩字符、forced 正常/错序/非单调/越包络、跨自然词和 ASR token、source anchors 与 segment identity；另覆盖重复短语、标点、跨 source editable 分区、非法 legacy fallback 和同 editable id 的内部删除多 run。
- API：cut-draft GET/PUT 同 revision 返回派生投影，请求模型和 JSON 文件不包含派生字段，旧草稿/无 sidecar 兼容，过期 revision 冲突。
- 生成与恢复：`/cuts`、`/compose`、completed edit 文案修正和 history 使用一致文字；显式空 `transcriptRanges` 不回退物理范围。
- 来源持久化：带有效 revision 的 `/cuts`、`/compose` 保存两类来源；未带 revision 的相同数值请求不保存来源字段并继续走旧扁平兼容路径。
- 前端/Store：本地降级不丢字，stale job/signature/revision 被拒绝，文字保存原子更新 cut transcript 且不改变 ranges、split、art/PiP anchors 或 `timingRevision`。
- 声学回归：物理 ranges、transition resolver、FFmpeg 输入和首字残音边界保持不变。

### 7. Wrong vs Correct

```python
# Wrong: 空语义范围会错误回退为物理删除范围。
semantic_ranges = edit.get("transcriptRanges") or edit.get("ranges") or []

# Correct: 只有字段缺失或无效时兼容回退，显式空列表有业务含义。
semantic_ranges = edit.get("transcriptRanges")
if not isinstance(semantic_ranges, list):
    semantic_ranges = edit.get("requestedRanges") or edit.get("ranges") or []
```

```python
# Wrong: 合并来源后只能用粗字符时间统一判删。
semantic_ranges = [*text_ranges, *timeline_ranges]

# Correct: 文字范围按语义字符判删；timeline 范围只按有效 forced 字符判删。
build_retained_transcript(
    segments,
    text_ranges,
    output_duration,
    timeline_delete_ranges=media_ranges,
    timeline_semantic_delete_ranges=timeline_ranges,
)
```

```javascript
// Wrong: 文字保存后永久停留在本地粗时间投影。
const cutTranscript = buildLocalRetainedProjection();

// Correct: 先用三重守卫安装服务端派生值，失败才保留本地降级。
await loadServerRetainedProjection(jobId, signature, revision);
const cutTranscript = getCurrentRetainedProjection();
```

## 场景：跨 ASR 源句合并后的文案归属

### 1. Scope / Trigger

- 用户把属于不同 ASR `sourceSegmentIndex` 的相邻 editable 段合并，随后执行文字修改、再次拆分、删除或刷新恢复时适用。
- 一个 editable 父段被删除状态拆成多个可见 run，浏览器只修改或合并其中一个连续字符片段时同样适用。
- editable 段是展示和操作单元，不再隐含“只属于一个源句”；源句仍是 retained transcript、声学映射和艺术字 source anchor 的稳定存储单元。

### 2. Signatures

- `apply_transcript_segment_operation(editable_segments, operation, source_segments=None) -> editable_segments`。
- `sync_source_segments_from_editable(source_segments, editable_segments) -> source_segments`。
- `PUT /api/transcriptions/{job_id}/editable-segments` 的请求 action 保持 `merge_up|merge_down|split|text`；`selectionStart/selectionEnd` 是可选的父段 Unicode code point 半开范围。响应中的 mixed-source editable 段携带主归属 `sourceSegmentIndex`、有序完整归属 `sourceSegmentIndexes[]`，其 `words[]` 携带逐 token `sourceSegmentIndex`。

### 3. Contracts

- merge 必须把两个输入段的逐字符 token 和 owner 一起拼接；`sourceSegmentIndex` 只作兼容主归属，不能代表 mixed-source 段的全部内容。
- text 修改按旧字符的单调 owner 序列做差分投影；相同字符保持 owner，替换/插入只分配到受影响或相邻 owner，并精确保留内部空白。禁止按新文本总长度或整段时长比例重新切两个源句。
- split 必须切逐字符 token；每个新段从自身 token 重建 `sourceSegmentIndexes`，不能继承合并段的完整 owner 列表。
- source 回写按 token owner 聚合，所有源句拼接文本必须严格等于 editable 文本。某个已声明 owner 被编辑为空时保留该 source segment 的稳定索引，但清空其 `text/words`，不得保留旧源句造成重复。
- retained transcript、editable acoustic boundary、已有 edit projection 和 transcript art cue 均消费同一 token owner；一个 mixed-source editable id 可映射多个 source segment。源句清空时对应艺术字 cue 进入既有 suppressed 流程。
- 旧草稿没有 token owner 时，只能按每个字符的时间中点和已声明源句包络单调恢复；一个旧自然词跨源时不得用整词中点统一归属。无法形成完整单调分区时使用既有安全回退，不得部分安装映射。
- 以上只改变语义归属；不得修改 VAD/forced alignment 候选、物理删除范围或声学吸附算法。
- `text` 带 selection 时只重分词并替换目标 token slice，前后 token 的文字、时间和 owner 不变；无 selection 时保持旧整段替换。
- 局部 `merge_up` 要求 selection start 为 `0`，先把未选 suffix 隔离，再合并上一段与目标 prefix；局部 `merge_down` 要求 selection end 等于父段 token 数，先隔离未选 prefix，再合并目标 suffix 与下一段。隔离和合并只安装一次最终列表，不持久化中间结构。

### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| token owner 非整数、越界、缺失或回退后非单调 | mixed-source 映射无效；retained/boundary 使用既有安全回退，不部分消费错误 owner |
| text 修改包含内部空格或标点 | 精确保留原输入字符，并继续按 owner 回写 |
| 替换文字比原跨源文本短，后一 owner 无剩余字符 | 清空对应 source 文本与 words；retained 和艺术字不保留旧字符 |
| 旧 merged words 的单个词跨两个 source 包络 | 按逐字符时间中点恢复两个 owner，字符数量守恒 |
| source words/anchors 合法 | 回写后的 word 时间有限、单调、位于各自 source 包络内 |
| action 后工程快照写入失败 | 路由保持既有 `500 分段状态保存失败`，不得报告伪成功 |
| selection 只提供一个端点、为空或越界 | 返回稳定 400，不执行局部写入 |
| 局部 merge 范围未贴对应父段边界 | 返回方向明确的稳定 400，不跨越未选/删除文字 |

### 5. Good / Base / Bad Cases

- Good：源句“所有人。”和“一起出发。”合并后改成“所有人。共同出发。”，回写仍是两个源句且拼接恰好等于新文案；同一 editable id 可投影到两个 retained segment。
- Base：同一源句内 split/merge/text 仍只有一个 owner，既有 API 和时间行为不变。
- Bad：合并段只继承首句 owner，再把全文写回首句；后一源句会保留旧文案并产生重复。按字符数量比例硬切也会把用户修改错分到另一源句。
- Good：父段含两处相同短语时，用明确 `selectionStart/selectionEnd` 修改第二处；第一处和被删除前缀逐字符不变。
- Bad：服务端用 replacement 文字搜索父段，或局部 merge 先持久化 split 再发第二次 merge；前者命中错误实例，后者暴露半完成 revision。

### 6. Tests Required

- 纯函数：跨源 `merge -> text -> split`，断言 exact text、owner 单调、字符守恒、内部空白、短替换、源句清空和 word 时间包络。
- legacy：删除 `sourceSegmentIndexes` 和 token owner 后恢复；覆盖一个自然词跨 source 边界，断言逐字符归属而非整词中点归属。
- API/持久化：真实连续 merge/text PUT 后，同时检查内存 job 与 `project-state.json` 中的 source segments、editable segments、retained transcript 和艺术字 cue 无重复且拼接一致。
- 回归：完整 `test_cut_draft.py`、声学边界和艺术字 API/track 测试；物理删除边界结果不得变化。
- scoped operation：覆盖第二处重复短语、emoji、prefix/suffix token 快照、局部双向 merge、非法范围 400，以及无 selection 的旧整段请求。

### 7. Wrong vs Correct

```python
# Wrong: mixed-source 段被整体写回第一源句，第二源句仍保留旧文本。
parts = [item for item in editable_segments if item["sourceSegmentIndex"] == index]
source["text"] = "".join(item["text"] for item in parts)

# Correct: 兼容主归属只用于旧消费者，真实回写按逐 token owner 聚合。
for token in editable_segment_character_tokens(editable, source_segments):
    words_by_source[token["sourceSegmentIndex"]].append(token)
```

```python
# Wrong: 先模糊搜索文字，或用两个请求拆分再合并。
start = segment["text"].index(request.text)

# Correct: 验证父段 code point 范围，在同一个内存结果中组装最终 replacement。
selection_start, _selection_end = optional_transcript_operation_range(
    operation,
    len(tokens),
)
replacement_segments = [
    build_editable_segment_from_tokens(tokens[:selection_start], owner),
    build_editable_segment_from_tokens(
        [*tokens[selection_start:], *next_tokens],
        owner,
    ),
]
segments[index:index + 2] = replacement_segments
```

## 场景：实时艺术字草稿使用双时间坐标

### 1. Scope / Trigger

- 在未生成 `edited.mp4` 的文字剪辑草稿上生成全文艺术字或 AI 建议时，浏览器必须提交当前剪后 transcript 和时长，后端继续从原视频取帧。
- 该契约跨越艺术字请求 schema、草稿校验、关键帧采样、AI 提示词和浏览器 overlay 确认；修改任一环节时都必须同时验证剪后时间与原片时间。

### 2. Signatures

- API：`POST /api/transcriptions/{job_id}/art-text/transcript-track`
- 请求：`TranscriptArtTextTrackRequest(..., draftTranscript?: object, draftDuration?: number)`
- API：`POST /api/transcriptions/{job_id}/art-text/suggestions`
- 请求：`ArtTextSuggestionRequest(count, source="edited", existingOverlays=[], draftTranscript?: object, draftDuration?: number)`
- 后端：`validate_live_art_transcript(draft_transcript, duration, source_duration=None)`
- 后端：`select_art_frame_samples(transcript, duration, count) -> list[{mediaTime, displayTime}]`
- 后端：`create_art_contact_sheet(input_path, output_dir, frame_samples)`

### 3. Contracts

- `draftTranscript.segments[].start/end`、嵌套 `words/asrWords[].start/end` 和 `draftDuration` 都是剪后时间；可选 `sourceStart/sourceEnd` 成对出现并表示原片锚点。
- `draftTranscript` 存在时 `draftDuration` 必填。后端使用草稿 transcript 生成建议范围和提示词，但 `input_path` 仍指向原视频，不生成中间视频。
- 每个关键帧样本都必须携带 `{mediaTime, displayTime}`：FFmpeg seek 只读 `mediaTime`，联系表标签和模型提示只读 `displayTime`。
- 草稿最多 `1000` 个 segment、`50000` 个 `words/asrWords` 条目；segment 文本总量和词级文本总量分别不得超过 `50000` 字符。
- 所有 edited/source 区间必须有限、非负且 `end > start`；edited 终点不得超过 `draftDuration + 0.01s`，source 终点不得超过原视频时长 `+0.01s`。
- 旧客户端可同时省略 `draftTranscript/draftDuration`，此时沿用已生成 edit 或原片 transcript，并允许 `mediaTime === displayTime` 的单时间路径。
- AI 返回和确认后的 overlay 的 `start/end` 始终是剪后时间；浏览器通过唯一 `MediaController` 补齐 `sourceStart/sourceEnd`，Store、预览和 compose 不得重新解释坐标。

### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| 只提交 `draftTranscript`，缺少 `draftDuration` | `400`，提示剪辑草稿缺少视频时长，不创建后台任务 |
| segment 为空、非对象、无文字或超过 `1000` 个 | `400`，提示草稿文案格式无效或没有可用文案 |
| `words/asrWords` 非数组、包含非对象或总数超过 `50000` | `400`，提示词级时间格式无效或词级文案过长 |
| segment 或词级文本超过 `50000` 字符 | `400`，不截断后继续请求 AI |
| edited/source 区间非有限、反向、越界 | `400`，提示草稿包含无效时间 |
| 仅有一个 source anchor | `400`，提示源时间锚点不完整 |
| 草稿字段全部省略 | 保持旧请求行为，读取 job 中既有 transcript/edit |
| 草稿存在且 source anchor 有效 | 建议使用剪后范围，关键帧从对应原片时间提取 |

### 5. Good / Base / Bad Cases

- Good：删除原片 `0-4.08s` 后，剪后 `3.21s` 的文字携带原片 `7.29s` 锚点；AI 提示显示 `3.21s`，FFmpeg 在 `7.29s` 附近取帧。
- Base：未发生文字剪辑或旧客户端未提交草稿时，展示时间与取帧时间相同，现有结果保持兼容。
- Bad：按剪后 `3.21s` 直接 seek 原片，或把原片 `7.29s` 写入建议 `start`，会造成画面分析和艺术字时间至少一侧错位。

### 6. Tests Required

- Schema/API：两个请求模型接受可选草稿字段；草稿与时长必须成套使用，旧请求继续通过。
- 校验单元测试：覆盖 segment、`words/asrWords` 的结构、数量、文本长度、有限区间、越界区间和成对 source anchor。
- 采样测试：断言 `{mediaTime, displayTime}` 同时存在，原片 seek 与剪后标签各自使用正确字段。
- AI API：捕获后台任务输入、联系表样本和提示词，确认实时草稿替代 job 旧 transcript，但媒体路径仍为原视频。
- 前端/浏览器：文字删除后无需生成中间视频即可请求、预览并确认艺术字；确认结果同时具有 edited range 和 source anchors。

### 7. Wrong vs Correct

```python
# Wrong: 剪后秒数不能直接用于原片取帧。
ffmpeg_seek = sample["displayTime"]

# Correct: 媒体读取与用户可见时间显式分离。
ffmpeg_seek = sample["mediaTime"]
prompt_label = sample["displayTime"]
```

```javascript
// Wrong: 只传 job 中的旧 transcript，AI 不知道当前文字删除结果。
body = { count, existingOverlays };

// Correct: 建议范围使用当前实时剪后草稿。
body = { count, existingOverlays, draftTranscript, draftDuration };
```

## 场景：文字草稿在预览前完成音频边界校准

### 1. Scope / Trigger

- 文字或手动时间轴删除范围接近语音时，必须在进入公共预览和最终生成前用完整句段强制对齐证据解析物理边界；强制对齐不可用时才使用受限波形回退。
- 已检测的无声范围不参与字符强制对齐；草稿解析为媒体范围时仍必须保护未明确删除的识别文字。

### 2. Signatures

- API：`PUT /api/transcriptions/{job_id}/cut-draft`
- API：`POST /api/transcriptions/{job_id}/cuts`，请求 `CutRequest(ranges, cutDraftRevision?: int)`
- API：`POST /api/transcriptions/{job_id}/compose`，请求 `PreviewCompositionRequest(..., cutDraftRevision?: int)`
- 后端：`ensure_acoustic_alignment_cache(media_path, segments, job_directory, model_cache_dir, *, segment_indexes=None)`
- 后端：`resolve_cut_draft_acoustic_boundaries(media_path, text_ranges, timeline_ranges, segments, duration)`
- 后端：`align_cut_draft_text_ranges_to_audio(media_path, text_ranges, segments, duration)`
- 后端：`refine_shared_character_boundary(left, right, fallback, samples, sample_rate, *, deletion_on_left, allow_token_extension=True)`
- 后端：`corroborate_forced_deleted_head_with_pcm(retained_limit, forced_candidate, samples, sample_rate) -> (boundary | None, evidence)`
- 后端：`find_quiet_token_extension_boundary(left, right, fallback, samples, sample_rate, *, deletion_on_left, enabled)`
- 后端：`resolve_cut_draft_delete_ranges(draft, suggestions, segments, duration, *, use_text_semantic_boundaries=False)`
- 后端：`normalize_cut_draft_split_points(points, duration)`
- 后端：`validate_split_exact_timeline_range(item, split_points, duration)`
- 后端：`normalize_delete_ranges(ranges, duration, protected_ranges=None)`
- 后端：`subtract_protected_ranges(ranges, protected_ranges, *, minimum_duration=0.0)`
- 前端：`applyPersistedCutDraftAlignment(draft, expectedSignature)`

### 3. Contracts

- `textRanges[].originalStart/originalEnd` 表示删除哪些文字，不因波形吸附而改变。
- `timelineRanges[].originalStart/originalEnd` 表示用户确认的精确时间语义；物理 `start/end` 只有在距离可靠字符状态转换不超过 `0.20s` 且不跨保留语音核心时才能独立吸附。coarse midpoint 判定出的连续删除 run 必须至少有一个 forced/acoustic 字符被选区覆盖超过一半，才能参与吸附。完全位于强制对齐 quiet gap 的范围保持精确。
- 仅由 VAD `silence/aggressive` 授权的最终物理端点也必须距用户端点不超过 `0.20s`；forced/PCM 已证明的尾音边界可继续超距。任意吸附结果如果与用户原选区完全失去交集，则整体回退精确原范围。
- `splitPoints[].sourceTime` 是播放头分割的源媒体锚点。`boundaryMode="split_exact"` 只允许完整匹配两个相邻 source anchors 及其 `splitClipKey`；验证成功后物理 `start/end` 严格等于 `original*`，不得加载 forced alignment、解码 PCM 或执行任何声学移动。缺少 mode 的历史/普通手动范围按 `speech_safe`。
- `textRanges[].start/end` 表示真实媒体删除范围；草稿 PUT 响应可以在上一保留文字结束与下一保留文字开始之间扩大，禁止为草稿对齐传入 head/tail guard 穿越保留文字。
- `adjacentSilenceBefore/After` 必须按校准后的物理边界重新计算。
- 音频解码或分析失败时，物理范围回退到 `originalStart/originalEnd`，不沿用客户端传入的可能越界 `start/end`。
- `noSpeechRanges` 先扣除全部识别文字；文字物理扩展和空白范围组成自动删除集后，还必须扣除“识别文字 - 文字语义删除 - 已提交手动时间轴删除”所得的保留片段。
- `normalize_delete_ranges` 的 `0.12s` 容差只能合并不穿越 `protected_ranges` 的区间；手动范围只放开它精确覆盖的文字片段，不能使整个识别词失去保护。
- 前端只有在当前草稿签名仍等于本次请求签名时才能应用响应；应用后更新当前撤销快照，不新增撤销记录。
- 剪辑任务的 `ranges/requestedRanges` 保持物理预览范围，另以 `transcriptRanges` 保存语义文字范围；生成和统一合成使用前者裁切媒体、使用后者重建剪后 transcript。
- 后续修正文案而重建剪后 transcript 时优先读取 `transcriptRanges`，历史任务缺少该字段时兼容回退到 `requestedRanges/ranges`。
- `/cuts`、`/compose` 和公共预览继续消费草稿中同一组 `start/end`；新客户端必须携带当前 `cutDraftRevision`，过期 revision 返回冲突，生成阶段不得再次吸附。
- `fa-zh` 对齐必须使用完整句段文本并校验字符数量/顺序、finite 单调时间、句段包络和相邻字符非坍缩结构；sidecar 的 `validation.valid` 不能替代读取时复验。旧任务只惰性补齐本次范围附近句段。
- 以下多尺度 RMS、字符走廊和 token 补充规则只用于强制对齐缺失或无效时的保守降级，不能覆盖有效 `fa-zh` 转换。
- 删除终点只能从语义 fallback 向后移动，删除起点只能向前移动；任何反方向候选均无效。边界移动必须相对 fallback 明显降低多尺度 RMS，fallback 已低但方向侧仍存在更低谷底时不得因固定 RMS 阈值提前停止。
- 同段、非重复且结构有效的 delete-start 不能把被删字符的 forced start 当作完整声学起音；上一保留字符的 forced end 是不可越过的 hard limit，forced start 只是候选上界。PCM 可在 candidate 之后读取由采样 step 与持续 attack block 数推导的有限邻近窗口，但这些样本只能补足“至少两个低能 block -> 至少两个高能 block -> 局部相对能量跃升”的起音佐证；成功切点必须直接来自 candidate 之前的已确认低能走廊，并满足 `retainedSpeechHardLimit <= final < forcedCandidate`，禁止固定毫秒 padding。
- candidate 后没有邻近持续起音、只有更晚的独立 quiet gap/attack，或 PCM 证据不足时，deleted-head helper 必须返回 `None`，保持 `boundaryTrustworthy=false` 和 `forced_deleted_head_pcm_not_corroborated`，再进入受 retained hard limit 下界保护的删除方向 waveform fallback；不得把同一个未佐证 forced candidate 重新标为可信，也不得用 hard limit 本身直接替代切点。
- 同一候选走廊存在多个静音段时必须选择 hard limit 后第一个具有持续起音佐证的静音段，不能倒序选择被删音节内部的后续短停顿。判定使用相对能量并保持非削波增益不变性；均匀低能、轻微噪声、单点尖谷、单调斜坡和立即起音均不构成前移证据。
- delete-start PCM 佐证成功时诊断记录 `trustReason=forced_deleted_head_pcm_valley`、`forcedCandidate`、`final`、`pcmValleyStart/End`、`pcmAttackStart`、`pcmAdjustment` 和 `retainedSpeechHardLimit`，且 helper 返回值必须与诊断中的最终低能点一致，不能依赖外层 resolver 再隐式改早。文字范围、靠近同一转换的 timeline 范围和用户点击文案拆分产生的 editable boundary 必须复用 shared forced boundary cache，得到相同物理点；`originalStart/originalEnd` 保持语义值。
- 字符中心走廊只接受相对 fallback 明显改善的内部局部低谷，或同时位于整条走廊谷底的方向端点；固定 RMS 阈值不得改变候选资格，单调斜坡和非谷底字符中心不能充当共享边界。
- 删除起点可以向前扩展到上一保留字符所属原始 ASR token 的起点，但补充走廊必须出现至少两个采样步长组成的相对低能量谷底，并且该谷底还要比字符中心走廊候选显著更低。token 只限定删除起点的补充声学走廊，不能被整体加入删除范围，也不能用固定毫秒扩张替代。
- 删除终点禁止越过字符中心走廊继续搜索下一保留字符的 token；下一字说完后的静音不能证明它的起音可以删除。
- 一个保留字符两侧都紧邻删除范围时禁用 token 补充走廊，防止两个物理范围从两侧夹穿该短字符；无合格相对谷底证据时继续使用字符走廊结果或语义 fallback。

### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| job、媒体或时长无效 | 沿用既有 `404` / `409` 契约，不写草稿 |
| range 非有限值或 `end <= start` | `400`，不写部分草稿 |
| 草稿 revision 过期 | 校准前或写入前返回 `409` |
| `/cuts` 或 `/compose` 携带 revision，但该 revision 不存在或已过期 | `409`，不使用请求中的旧范围猜测生成 |
| revision 匹配，但权威草稿没有任何删除范围 | `400`，不创建 no-op 生成任务 |
| 旧客户端省略 revision | 继续校验并使用请求中的扁平 `ranges`，保持兼容 |
| sidecar 标记 valid 但字符、时间或包络复验失败 | 丢弃该记录；只重算受影响完整句段，失败时安全降级并记录诊断 |
| 音频解码/分析失败 | 回退到语义文字范围，草稿仍可安全保存 |
| 自动空白部分/完全覆盖识别文字 | 扣除文字后只保留达到最短时长的无文字碎片；完全覆盖时不产生自动删除 |
| 小于 `0.12s` 的保留文字位于两个自动范围之间 | 保持两个范围，不用合并容差跨过该文字 |
| 手动时间轴范围只覆盖一个识别词的部分 | 仅该精确片段可删除，词的其余片段继续作为自动合并保护区 |
| 手动端点在可靠语音转换 `0.20s` 内 | 只吸附对应物理端点，`original*` 保持精确；另一端独立判定 |
| 手动范围完全位于强制对齐 quiet gap | 物理范围保持 `original*`，不扩大到相邻文案 |
| exact range 的端点、相邻关系或 `splitClipKey` 不匹配 | `400`，不写部分草稿且不降级为 speech-safe |
| speech-safe range 携带 split identity，或同一 split clip 重复 exact 删除 | `400`，拒绝歧义身份 |
| 合法 split_exact | 原样保存 `original*` 为物理端点，forced alignment/PCM 调用数均为 0 |
| 保存期间前端又发生编辑 | 只推进 revision，不用旧响应覆盖新编辑；队列继续同步新状态 |
| 删除起点字符中心走廊只有较浅相对低谷，上一 token 内存在更深且持续的相对谷底 | 使用上一 token 内离 fallback 最近的谷底点 |
| 删除终点字符中心走廊不足，但下一保留字符说完后存在静音 | 保持字符走廊结果或 fallback，不进入下一 token 尾部 |
| fallback 已安静但方向侧存在显著更低谷底 | 仍使用相对谷底，不因固定 RMS 阈值提前停止 |
| 方向侧只有单调斜坡、均匀低能量或谷底位于 token 外 | 保持 fallback，不扩大搜索 |
| 单个保留字符夹在两个删除范围之间 | 禁用两侧 token 补充走廊，保留字符物理核心不被覆盖 |
| 同段 delete-start 的持续起音需要 candidate 后的邻近高能 block 才能确认 | post-candidate block 只参与佐证；物理起点取 candidate 前第一条已确认低能走廊的保守边缘，严格早于 candidate |
| 同段 delete-start 存在多条静音走廊 | 使用 hard limit 后第一条带持续起音和局部跃升的走廊，不选择被删音节内部后续停顿 |
| candidate 后先出现独立 quiet gap，超过邻近确认窗口才出现另一段 attack | 拒绝该 attack，不用后续语音反向授权当前 deleted-head 边界 |
| 同段 delete-start 只有立即起音、短于两个 block 的凹点、单点、均匀低能、轻噪声或单调斜坡 | PCM 佐证失败并保持 `boundaryTrustworthy=false`；走受 retained hard limit 保护的方向性 waveform fallback |

### 5. Good / Base / Bad Cases

- Good：粗 ASR token 同时包含被删“得”和保留“你”时，用完整句段已知文本对齐取得被删字可靠尾点 `37.810s`；文字 `originalEnd` 仍为语义边界，物理 `end` 不吞后续 quiet gap，也不越过“你”的可靠起音。
- Good：删除起点前的真实停顿被 ASR 均摊到上一保留字符时间内，字符中心走廊只有较浅低谷时，起点在上一 token 内向前移动到更深且持续的相对谷底，但语义范围不变。
- Good：forced start 落在被删首字起音之后，且持续高能确认跨过 candidate 时，PCM 只用 candidate 后 block 证明 attack；物理 delete-start 仍取 candidate 前首条持续低能走廊的保守边缘，文字语义范围不变。
- Base：手动范围完全落在完整句段字符之间的 quiet gap 时，物理 `start/end` 等于 `original*`；重复保存命中 sidecar 且边界不继续漂移。
- Base：删除播放头分割形成的完整 clip 时先验证相邻 anchors，再保持精确端点；普通拖选仍独立使用语音安全吸附。
- Bad：在短音频窗内只对齐局部文字、把 DashScope token 时间当字符硬包络、把 candidate 后任意远的语音当当前起音、把单调衰减的响亮采样点当低谷、倒序选择被删音节内部静音，或直接把相邻 ASR token 整体扩进删除范围。

### 6. Tests Required

- Adapter/cache：完整句段字符顺序与时间结构、重复短语、非数字时间、相邻字符坍缩、损坏 valid 缓存复验、同 sidecar 并发串行、锁回收和旧任务受影响句段惰性补齐。
- 单元测试：低整体音量样本仍按相对能量改善识别尾音，不依赖固定 RMS 阈值。
- 单元测试：删除起点只向前、终点只向后；拒绝单调斜坡和非谷底方向端点，接受相对改善且位于走廊谷底的方向端点，均匀静音或均匀低能量保持不动。
- 性质测试：同一内部低谷、方向端点和起点 token 补充谷底在多组不削波增益下保持边界稳定；缩小增益后的单调斜坡仍回退，不能因跨过固定 RMS 阈值改变决策。
- 单元测试：删除起点字符走廊仅有较浅相对低谷而上一 token 内存在更深持续谷底时选择最近谷底点；谷底位于 token 外时回退；删除终点不得吸附到下一保留字符说完后的静音；短保留字符夹在两段删除之间时禁用扩展。
- 单元测试：forced delete-start 参数化 candidate 相对真实起音的前/中/后偏移、非削波增益、轻噪声和多个 attack；需要 candidate 后 block 才能确认时，返回点仍严格位于 candidate 前的首条已佐证低能走廊。文字/timeline/用户点击拆分共享 boundary 与诊断且 `original*` 不变；双静音走廊不得选后一个。晚到独立 attack、立即起音、单点、一个 `5ms` 短谷、均匀低能、轻噪声和单调缓升必须拒绝 PCM trust，并断言 retained hard limit 不因失败 evidence 被 null 覆盖。
- 单元测试：自动空白部分/完全覆盖文字、两个自动范围夹住小于 `0.12s` 的保留词、手动范围只删除词的部分时，断言保留片段不被合并穿越。
- API 测试：草稿 PUT 返回校准后的 `start/end`、原始语义边界和重算的相邻静音，并验证前后两侧保留文字限制、分析失败安全回退与重复 PUT 幂等。
- API 测试：历史草稿缺少 split 字段时恢复为空；split point clamp/sort/dedupe；合法 exact 不触发 alignment/PCM；伪造 key、非相邻 anchors、speech-safe identity 和重复 exact 均返回 `400`。
- 生成回归：`process_cut_job` 与组合生成不得再次调用边界吸附，最终 `ranges` 等于已保存草稿物理范围；物理范围延长时 `transcriptRanges` 仍只删除选中的语义文字；revision 过期、缺失草稿和空权威草稿分别断言冲突/拒绝。
- 前端契约：校准响应原子更新 text/timeline 和当前撤销快照，键盘微调同步 `original*`，旧请求响应不能覆盖并发新编辑，生成必须等待稳定保存队列；真实浏览器验证刷新、立即生成、公共预览/compose revision 和 375px。
- 真实媒体 gate：产品 resolver + FFmpeg/AAC 重生成后，二次 ASR 不再返回被删音节，下一保留字 PCM 相关、lag 和 RMS 不退化；人耳盲听仍是发布前人工门槛。
- 首音残片 gate：全文 ASR 不能作为唯一通过条件；必须记录源时间 hard limit/candidate/final、成片拼接前 `20-40ms` 短窗能量与峰值，并提供局部试听片段确认被删首音消失且下一保留表达完整。

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

```python
# Wrong: 短窗局部对齐和粗 token 硬包络会把真实字符边界压回错误时间。
characters = align(audio[fallback - 0.5:fallback + 0.5], selected_text)
physical_end = min(characters[-1].end, asr_token["end"])

# Correct: 完整句段已知文本对齐决定语言学边界，PCM 只做硬保护内微调。
segment = ensure_acoustic_alignment_cache(
    media_path,
    transcript_segments,
    job_directory,
    model_cache_dir,
    segment_indexes={affected_segment_index},
)
physical_end = resolve_cut_draft_acoustic_boundaries(...)[0][0]["end"]
```

```python
# Wrong: forced start 可能已经落在被删首字的低能起音之后。
physical_start = deleted_character["_forcedStart"]

# Correct: 保留字 forced end 是 hard limit；candidate 后只补起音证据，返回点仍在 candidate 前。
physical_start, evidence = corroborate_forced_deleted_head_with_pcm(
    retained_character["_forcedEnd"],
    deleted_character["_forcedStart"],
    samples,
    sample_rate,
)
assert physical_start is None or (
    retained_character["_forcedEnd"]
    <= physical_start
    < deleted_character["_forcedStart"]
)
```

```python
# Wrong: 分割片段边界进入普通吸附，会重新引入尾音或误删下一段起音。
aligned = align_cut_draft_timeline_ranges_to_audio([split_exact], ...)

# Correct: 验证相邻源锚点后保持用户建立的精确帧边界。
validate_split_exact_timeline_range(split_exact, split_points, duration)
split_exact["start"] = split_exact["originalStart"]
split_exact["end"] = split_exact["originalEnd"]
```

## 场景：相邻重复文案使用转场级可信度

### 1. Scope / Trigger

- 强制对齐字符参与删除/保留状态转换时适用，尤其是完整短语重复、删除 run 后缀与保留 run 前缀重叠、连续相同字符。
- `validation.valid` 只证明完整句段字符数量、顺序和时间结构可解析，不能证明重复文本映射到了正确实例。

### 2. Signatures

- `build_acoustic_transition_context(units, deleted, left_index) -> transition context`
- `forced_alignment_transition_boundary(..., transition_context=...) -> (boundary | None, diagnostic)`
- `corroborate_repeated_transition_with_pcm(fallback, forced_candidate, samples, sample_rate, *, deletion_on_left) -> (boundary | None, evidence)`
- `corroborate_forced_transition_quiet_gap(fallback, forced_candidate, retained_limit, samples, sample_rate, *, deletion_on_left) -> (boundary | None, evidence)`
- `resolve_cut_draft_acoustic_boundaries(...)` 是文字和手动时间轴范围的共享入口。

### 3. Contracts

- 重复检测按同一 segment 内相邻 deleted/retained run 的规范化可发声字符计算最长“左侧后缀 = 右侧前缀”；多字符重叠和连续同字均为 `repeatAmbiguous=true`，不依赖 AI 建议类型。
- 非重复且方向、相邻 forced 结构有效时维持 forced 主路径。`coarseTokenMaxBoundaryDeviationSeconds` 只进入诊断，禁止设置全局阈值拒绝“得/你”、长静音或其他合法大偏差。
- 重复且 forced 结构有效时，只在 semantic fallback 与 forced candidate 的有向走廊内寻找持续 PCM 谷底。谷底必须至少覆盖两个 `5ms` 采样点，以 `20ms` floor 和 `20/40/80ms` 多尺度肩部做相对能量比较；谷底不得比 fallback 更高能，并且必须相对 forced candidate 与双肩显著更低。fallback 本身已经安静时不要求固定比例改善；均匀低能、单点尖谷和单调斜坡不授权 forced candidate。
- 走廊内没有双肩谷底时，不能立即把所有重复转场退回 semantic fallback。若 forced candidate 与保留侧 forced limit 不重叠且其间存在独立 quiet gap，PCM 必须同时证明 gap 内持续低能、删除侧候选前持续高能、保留侧 limit 外持续高能，才可原样信任 forced candidate，记录 `trustReason=forced_pcm_gap`。最终边界不得推进到 quiet gap 尾部；gap 高能、缺少任一侧语音或 forced overlap 均拒绝。
- 内部谷底和 forced quiet gap 都失败时，只有保留侧 forced hard limit 前（delete-end）或后（delete-start）的最后 `80ms` 持续低能，并且 hard limit 保留侧的高能窗连续覆盖至少一个完整 `20ms` block（首尾验证窗不重叠），才可把终点推进到 hard limit 内的最低振幅样本，记录 `trustReason=repeat_retained_pcm_valley`。阈值由 quiet ceiling 与 retained peak 动态计算；单点爆音、噪声底轻微上升或搜索窗内没有持续保留语音均不得授权。
- 删除终点只向后、删除起点只向前。PCM 失败时 structurally valid 的歧义 forced candidate 回退 semantic/manual fallback；forced 缺失时仍允许既有受限 waveform 降级。
- 文字和 timeline 必须传入同一 transition context 并复用同一 forced boundary cache。cache key 至少包含 segment/character、方向、fallback 和 repeat overlap，避免不同删除状态复用动态 trust。
- 完整行/segment 删除形成的跨段转场必须按 units 列表中的物理邻接、相邻 segment index、前段最后字符和后段首字符共同确认。两段 forced 均有效且不重叠时使用删除侧 forced 边界并以保留侧 forced 边界为 hard limit；forced 缺失或 overlap 时复用同一个 sustained-valley helper，只在 semantic fallback 与 retained-side forced/acoustic/semantic 安全界限之间搜索。无谷底或保留语音立即起音时保持 fallback，禁止固定毫秒扩张。
- timeline 的普通 `0.20s` snap 门槛判断 requested endpoint 到 diagnostic semantic `fallback` 的距离；`boundaryTrustworthy=true` 时 final 可因可信尾音延迟超过 `0.20s`。requested 远离 semantic transition 时仍拒绝，完全位于相邻字符或 segment quiet gap 的范围保持精确。
- 诊断至少保留 `structureValid`、`boundaryTrustworthy`、`trustReason`、`repeatAmbiguous`、`repeatOverlapText/Length/Span`、`forcedCandidate`、`pcmCorroborated`、`pcmValleyStart/End`、`pcmGapCorroborated`、`pcmGapStart/End`、`retainedSpeechHardLimit` 和 `fallbackReason`。内部谷底路径的 `retainedSpeechHardLimit` 来自保留侧首次连续两个 `5ms` 点的显著能量回升；forced-gap 和 retained-limit 路径保留 forced retained limit。所有 hard limit 都必须位于最终切点的保留侧，失败的前置探测不得把已有 hard limit 覆盖为 null。动态 trust 不写回 alignment sidecar。

### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| forced 缺失或结构无效 | 既有受限 waveform/semantic 降级，`boundaryTrustworthy=false` |
| 非重复、forced 结构与方向有效 | 使用 forced 转场，`trustReason=forced_transition` |
| 重复、存在持续相对谷底 | 使用谷底内安全点，`trustReason=forced_pcm_valley` |
| 重复、候选后存在独立低能 gap 且两侧持续有声 | 保留 forced candidate，`trustReason=forced_pcm_gap` |
| 重复、前两类证据失败，但 hard limit 终端持续安静且保留侧持续起音 | 推进到不越过 hard limit 的最低振幅点，`trustReason=repeat_retained_pcm_valley` |
| forced gap 高能、缺少删除/保留侧持续语音或 forced overlap | 拒绝 gap 佐证，不把边界推进到 gap 尾部 |
| 重复、只有单点/噪声轻微波动/斜坡/均匀低能，或 hard limit 后无持续语音 | 拒绝 forced，`fallbackReason=repeat_pcm_not_corroborated` |
| forced 候选方向错误 | 拒绝候选，不扩大搜索 |
| timeline 命中已佐证的同一重复转场 | 复用同一 boundary，即使旧的 `0.20s` 普通吸附距离不足 |

### 5. Good / Base / Bad Cases

- Good：第一次“所以说啊”被删、第二次保留；forced 候选进入第二次起音，但 `141.795-141.815s` 持续谷底把最终边界限制在约 `141.814s`。
- Base：完整“你身边你身边人人都觉得 / 你身边人人都觉得…”上下文会形成重复重叠，但 forced candidate `37.790s` 到保留起音 `39.850s` 有约 `2.06s` 独立静音；PCM 两侧有声时继续使用 `37.790s`，不能退回 `37.120s` 留下“得”的尾音。
- Good：删除第一处“一起给”时，candidate/fallback `29.171s` 后仍有被删尾音，保留 hard limit `29.790s` 前最后 `80ms` 持续安静且其后有连续保留语音；最终点可推进到约 `29.789s`，但不得越过 `29.790s`。
- Bad：看到重复就统一退回 semantic fallback，或看到长静音就把边界推进到静音尾部；前者残留被删尾音，后者会删除下一段起音。

### 6. Tests Required

- 纯函数：完整重复、局部后缀/前缀、连续同字和非重复检测。
- 合成 PCM：持续谷底在多组非削波增益下稳定；forced candidate 后独立 quiet gap 和 retained hard-limit 终端静音的删除终点/起点对称通过；candidate 等于 fallback、早期孤立爆音、gap 高能、缺少保留侧语音、forced overlap、单点、噪声轻微波动、单调和均匀低能均有回退断言。
- 共享 resolver：文字与 timeline 得到同一物理点，`original*` 保持不变，diagnostic 字段完整。
- 非回归：必须使用完整重复上下文的“得/你”fixture，不能用只含两个字的简化 fixture；断言大 coarse deviation 仍走 `forced_pcm_gap` 且 hard limit 保持为下一 forced 起音。
- 真实媒体：同时证明被删尾音消失和下一次重复表达的起音未被削弱；用户媒体和 sidecar 全程只读。

### 7. Wrong vs Correct

```python
# Wrong: 结构有效不等于重复实例归属正确。
if alignment_record["validation"]["valid"]:
    boundary = left_character["end"]

# Correct: 动态删除状态先识别重复歧义，再要求局部 PCM 佐证。
context = build_acoustic_transition_context(units, deleted, left_index)
boundary, diagnostic = forced_alignment_transition_boundary(
    left,
    right,
    fallback,
    samples,
    sample_rate,
    deletion_on_left=True,
    transition_context=context,
)
```

## 场景：相邻字符联合使用 ASR、VAD 与 PCM

### 1. Scope / Trigger

- 修改文字删除、普通 timeline 删除、系统文字分段、用户在“调整文字分段”中的拆分，或公共预览/生成的删除边界时，必须复用本场景。
- VAD 只校准相邻字符之间的物理切点，不判断口误、不改变 AI 建议，也不改写用户选中的字符身份。

### 2. Signatures

- 后端：`resolve_adjacent_character_boundary(media_path, media_fingerprint, left, right, samples, sample_rate, *, directional_transition_contexts=None, forced_boundary_cache=None, adjacent_boundary_cache=None, vad_cache=None) -> boundary record`。
- 后端：`enrich_editable_segment_boundaries(media_path, source_segments, editable_segments, *, alignment_cache=None, existing_boundaries=None, samples=None) -> (editableSegments, editableSegmentBoundaries)`。
- VAD：`analyze_local_voice_activity(audio_path, duration, model_cache_dir) -> {status, reason, speechRanges, vad, modelId, modelRevision}`。
- 运行时：`load_funasr_auto_model() -> funasr.AutoModel`，是 FA 与 VAD 唯一允许使用的 FunASR 导入入口。
- API：`PUT /api/transcriptions/{job_id}/editable-segments` additive 返回 `editableSegments` 和 `editableSegmentBoundaries`；`PUT /api/transcriptions/{job_id}/cut-draft` 持久化最终物理范围及 `boundaryDiagnostics`。

### 3. Contracts

- 边界 key 必须包含源媒体 fingerprint、左右 source segment/可发声字符 ordinal/text，以及固定 FA/VAD revision；重复文本不得只按文字缓存。aggressive/fallback 记录还必须匹配 `deleteLeft/deleteRight` 的完整删除上下文，避免重复短语串用旧方向结果。
- `fa-zh` 确认字符身份与局部声学包络，FSMN-VAD 提供局部 speech/non-speech 证据，PCM 只在两者确认的持续低能走廊中选择精确采样点。VAD 不判断口误，也不改写 `originalStart/originalEnd`。
- 每个转场保存 `neutral/deleteLeft/deleteRight`。可信静音走廊存在时三者收敛到同一点；VAD 成功但无可信静音时使用方向性 aggressive 点，优先彻底删除被删侧语音；VAD 不可用时使用 FA+PCM fallback，并记录稳定 reason。
- `editableSegments[].start/end/words` 保持语义 ASR 时间，`mediaStart/mediaEnd` 负责未删除时的中性显示。删除某侧后，被删段和相邻保留段的可见时间必须同时使用同一个方向性物理点；若方向点使显示区间反转，起止点一起回退语义范围。
- cut draft 是物理删除范围权威。公共预览、`/cuts`、`/compose` 与 FFmpeg 只消费匹配 revision 的已保存 `start/end`，生成阶段不得再次调用 FA、VAD 或 PCM。播放帧回调必须先执行删除区间 seek，再更新旧 source time 对应的视觉状态。
- `boundaryMode=split_exact` 在解码或声学解析前直接保持精确原始锚点，FA/VAD/PCM 调用数必须为零。
- VAD 固定使用 `fsmn-vad` / `v2.0.4`、16 kHz 单声道 PCM WAV、CPU 单例和串行推理。局部 WAV 位于 job 目录并在所有退出路径清理；动态 VAD/PCM trust 不写入 `acoustic-alignment.json`。
- FA 与 VAD 必须通过共享 FunASR 运行时入口加载 `AutoModel`。初始化期间只允许 `funasr.*` 使用直接子模块枚举，避免递归导入无关可选模型及其原生依赖；非 FunASR 枚举仍委托标准 `pkgutil.walk_packages`。该临时替换必须由进程级锁串行化，并在成功或异常后无条件恢复，不能永久改变全局 Python 导入行为。
- “模型可用”必须以目标 Windows 运行环境中的真实 FA/VAD 初始化和至少一个真实媒体样本为发布门禁。mock 返回 `AutoModel` 只能验证导入隔离与降级契约，不能证明 Windows App Control、DLL 加载和模型推理实际可用。

### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| VAD 与 PCM 同时确认持续无声走廊 | `mode=silence`，三个 final 相同且位于交集内 |
| VAD 成功但字符连续发音或 PCM 不确认静音 | `mode=aggressive`，按删除方向选择不同 final，优先清除被删语音 |
| 模型下载、校验、加载、推理或局部 WAV 失败 | `mode=fallback`，公开稳定 reason，分段/保存/生成继续；`nonSpeechRanges=[]` |
| Windows App Control 阻止无关可选依赖的 DLL | 安全导入不得递归加载该依赖；FA/VAD 仍可初始化，不得误报 `runtime_unavailable` |
| FunASR 导入成功或抛出异常 | `pkgutil.walk_packages` 均恢复为调用前对象，其他包枚举行为不变 |
| 边界 key 或方向上下文不匹配 | 禁止复用旧 aggressive/fallback 记录，重新解析或安全降级 |
| 历史 job 缺少新增字段 | 继续按语义时间显示，首次相关操作惰性解析，不批量迁移 |
| 方向物理点造成 `mediaEnd <= mediaStart` | 两个展示端点一起回退语义范围，不混用一个物理端点和一个语义端点 |
| `split_exact` 范围合法 | 严格保留 `original*`，不得解码音频或调用模型 |

### 5. Good / Base / Bad Cases

- Good：删除第一处“一起给”时，重复上下文命中正确字符实例；无静音则用 aggressive 起止点完整覆盖被删语音，保留第二处“一起给你”，文案列表、时间轴、预览和 FFmpeg 使用同一拼接点。
- Good：目标 Windows 环境阻止未签名 `llvmlite.dll`，但该依赖属于未使用的可选模型；安全导入跳过递归扫描后，FA 与 FSMN-VAD 仍完成初始化，“你身边人人都觉得”的物理结束点使用真实 forced/VAD/PCM 证据。
- Base：历史 job 或 VAD 不可用时仍能拆分、保存和生成，诊断明确标记 fallback，且不把未知窗口伪报为静音。
- Bad：按相同文字复用另一处“一起给”的缓存、把 VAD padding 直接当采样切点、删除后相邻保留段仍显示 neutral，都会重新造成残音或显示与成片不一致。
- Bad：mock 测试中能取得 `AutoModel` 就认定运行时可用，或让 FA/VAD 各自修改全局包遍历器；前者会漏掉目标机 DLL 拦截，后者会留下竞态和全局状态污染。

### 6. Tests Required

- 单元：可信 VAD+PCM 交集、连续语音 aggressive 双方向、VAD fallback、短持续静音、单点谷底、均匀低能、轻噪声、单调缓升和多增益等价。
- 缓存：重复实例与完整方向上下文隔离；同 key 的文字/timeline/editable 路径一致，不同字符实例不得串用。
- API/草稿：用户拆分后立即返回中性边界；删除中段后两个相邻保留段同步使用方向点；刷新不漂移，生成阶段 FA/VAD/PCM 新增调用数为零。
- 浏览器：真实点击“拆分”再删除中段，断言文案、编辑弹窗和公共时间轴端点一致，基础 video `srcWrites/loadCalls` 为零；帧时钟先 seek 再渲染。
- 精确分割：`split_exact` 的 FA/VAD/PCM/音频解码调用数全部为零。
- FunASR 运行时：单元测试覆盖 FunASR 直接子模块枚举、非 FunASR 委托、成功/异常后的全局恢复；目标 Windows 环境用真实模型初始化并对真实媒体断言 alignment 至少有有效 segment、VAD 为 `completed`，不能只验证 mocked success。
- 打包：模型、jobs、history 和任务试听媒体不进入产物或 Git。

### 7. Wrong vs Correct

```python
# Wrong: VAD 不可用时，未知窗口不能被当成静音证据。
non_speech_ranges = complement(vad_result.get("speechRanges", []), window)

# Correct: 只有成功推理的公开 speech ranges 才能产生 non-speech。
non_speech_ranges = (
    complement(vad_result["speechRanges"], window)
    if vad_result.get("status") == "completed"
    else []
)
```

```python
# Wrong: FunASR 顶层导入会递归扫描并加载未使用模型的可选原生依赖。
from funasr import AutoModel

# Correct: FA 和 VAD 共享受锁保护、异常后恢复全局状态的安全入口。
from .funasr_runtime import load_funasr_auto_model

AutoModel = load_funasr_auto_model()
```

```javascript
// Wrong: 删除后仍用 neutral 显示相邻保留段。
displayEnd = segment.mediaEnd;

// Correct: 展示、预览和成片共享本次删除方向的物理端点。
displayEnd = deletedRightSide ? boundary.deleteRight : segment.mediaEnd;
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
- `timelineRanges` 是用户明确选择的时间轴语义范围，`original*` 不做字符扩展并允许只覆盖字符时间的一部分；物理 `start/end` 可按上节规则在 `0.20s` 内吸附到可靠语音转换。
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
| 手动时间轴范围只覆盖字符的一部分 | `original*` 保持精确；物理端点只在 `0.20s` 内有可靠转换时吸附 |
| 范围不与任何字符单元相交 | 保持已归一化范围，继续走既有范围校验 |

### 5. Good / Base / Bad Cases

- Good：`words=觉得/你`、`asrWords=觉/得你` 时，删除“觉得”最多结束于 `0.4s`，“你”继续保留；`words=一起/给/一起/给` 与 `asrWords=一起/给一/起给` 同理。
- Base：历史段落没有 `words` 时，从该段 `asrWords` 或 segment timing 逐字符派生；其他有 `words` 的段落不受影响。
- Bad：把 `asrWords=得你` 当成不可分割单元，使删除“觉得”扩展到“你”；或者每个范围虽已夹在字符边界内，最后仍用 `0.12s` 容差跨过中间短字符合并。

### 6. Tests Required

- 转写单元测试：多字 ASR word 的原始时间保存在 `asrWords`，Jieba `words` 可使用不同分词，标点校对不改变原始时间。
- 后端单元/API 测试：局部文字范围经草稿 PUT 扩展到相交字符；手动范围的 `original*` 保持精确、物理端点只在可靠转换附近吸附；混合段落按段回退 `words -> asrWords -> segment`。
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
