# 重复文案转场边界可信度设计

## 1. Design Goal

修复“完整句段对齐结构合法，但相邻重复实例映射错位”的可信度缺口。现有 `fa-zh` sidecar 继续负责提供字符候选时间；共享删除边界解析器新增转场级语义歧义识别和 PCM 佐证，只有可信的转场才能成为物理切点。

## 2. Root Cause Boundary

当前链路包含两个不同问题域：

1. `server/acoustic_alignment.py` 验证模型结果是否可解析：字符数量和顺序一致、时间 finite/单调、位于完整句段包络。
2. `server/app.py` 决定某个删除/保留状态转换应在哪里切媒体。

第一类结构校验无法证明相同文字的第一个实例没有被映射到第二个实例。本例 `所以说啊所以说啊` 的 34 个字符全部合法且单调，但第一个“啊”的时间被拖到第二次表达的起音附近。设计上不把这种歧义塞进全局 `validation.valid`，而是在第二层引入 `boundaryTrustworthy`。

## 3. Transition Trust Contract

每个删除/保留状态转换生成一个 transition context：

```text
segmentIndex
leftCharacterIndex / rightCharacterIndex
deletionOnLeft
semanticFallback
forcedCandidate
forcedRetainedLimit
deletedContext[] / retainedContext[]
repeatOverlap
structureValid
boundaryTrustworthy
trustReason
```

- `structureValid` 继续来自 sidecar 的读取时复验，只表示 forced character timing 可作为候选。
- `repeatOverlap` 从状态转换两侧的规范化可发声字符计算。完整短语重复、删除侧后缀与保留侧前缀重叠、连续相同字符都标记为语义歧义；计算使用当前删除状态，不依赖建议类型。
- 非歧义转场维持现有路径：方向、相邻字符、forced 区间不重叠等条件通过后，forced candidate 可直接可信。
- 歧义转场必须再通过 transition-local PCM corroboration。优先使用 fallback 到 forced candidate 内的持续谷底；若该路径失败，但 forced candidate 到另一字符 hard limit 之间存在由两侧持续语音肩部夹住的独立 quiet gap，则保留删除侧 forced edge 并记录 `forced_pcm_gap`。两种证据都失败时 forced candidate 不获授权。
- `coarseTokenMaxBoundaryDeviationSeconds` 只记录上下文，不设置全局阈值。局部粗时间可以帮助限定方向走廊，但不能否决完整句段中其他已验证转场。

该可信度依赖当前删除状态，因此不写回 source alignment sidecar，也不改变 sidecar schema。它随草稿的 `boundaryDiagnostics` 持久化，旧草稿缺少字段时按现有兼容路径读取。

## 4. Repeated-Text Ambiguity Detection

在 `build_shared_acoustic_delete_boundaries()` 已建立全部字符及 deleted 状态后，为每个转换读取同一 segment 内相邻的删除 run 和保留 run：

- 删除在左：比较删除 run 的后缀和保留 run 的前缀。
- 删除在右：对称比较保留 run 的后缀和删除 run 的前缀。
- 忽略空格和标点，保留自然字符顺序。
- 记录最长相同跨度和两侧实例位置；多字符重叠直接视为歧义。连续同一字符即使跨度为一也视为歧义，避免“啊啊”“嗯嗯”被结构合法结果误导。
- 不跨 segment 猜测重复映射；跨 segment 只按已有边界保护和降级路径处理。

检测只决定 forced candidate 是否需要佐证，不直接改变切点，也不复用面向产品建议的重复检测器。这样不会让 AI 建议逻辑反向控制媒体安全。

## 5. Sustained Valley Corroboration

### 5.1 Corridor

歧义转场只在语义 fallback 与 forced candidate 之间搜索，方向与现有契约一致：

- 删除在左：`[fallback, forcedCandidate]`，候选只能向后。
- 删除在右：`[forcedCandidate, fallback]`，候选只能向前。

走廊还要裁到相邻 forced 字符的外包络、重复实例局部语义包络和媒体时长内。forced 保留字符的时间只作为最外层上限，不再直接等同于真实保留起音。

### 5.2 Relative, Sustained Evidence

复用一次解码的 `16kHz` PCM 和现有 `5ms` 步长、多尺度 `20/40/80ms` RMS：

1. 生成整个走廊的多尺度能量曲线。
2. 候选必须是内部相对谷底，且至少连续两个采样步长保持低能；单点尖谷不合格。
3. 谷底不得比 semantic fallback 更高能，并且必须相对 forced candidate 及两侧局部肩部有明确改善；fallback 本身可能已经落在静音中，因此不能要求固定比例改善。比较只使用相对值，不使用绝对音量阈值，整体非削波增益不改变结果。
4. 删除在左时选择方向上最靠后的合格谷底，随后在谷底范围内吸附低振幅样本；删除在右时对称选择最靠前的合格谷底。
5. 保留侧首次连续两个采样步长的显著能量上升定义保留起音限制。该限制必须位于谷底切点的保留侧，不能直接复用最终边界；最终边界不得越过该限制，也不得越过 forced 保留字符的最外层上限。
6. 没有合格谷底时，只有下节的独立 forced quiet gap 通过 PCM 佐证才可保留 forced candidate；否则返回未佐证，调用方进入现有受限 waveform/semantic fallback。

本例走廊约为 `141.156-142.010s`，应选择约 `141.880s` 的持续谷底，不选择处于保留“所”内部的 `142.010s`。

### 5.3 Independent Forced Quiet Gap

- 文本重叠只代表实例有歧义，不代表 forced 一定错误。若删除侧 forced edge 与保留侧 forced hard limit 不重叠，则检查两者之间是否为独立 quiet gap。
- gap 核心必须持续低于 fallback 到 candidate 的删除侧连续语音肩部，hard limit 另一侧必须出现连续保留语音回升；delete-start 完全对称。所有比较继续使用相对多尺度 RMS，非削波增益不改变结论。
- 成功时最终点保持 forced candidate，不移动到 gap 尾部；`retainedSpeechHardLimit` 保留另一字符 forced edge。forced gap 为零、gap 中夹有语音、均匀低能或任一侧缺少持续语音肩部时拒绝。
- 该证据区分合法“得/你”长静音与错误“所以说啊”首尾相接：前者可得到 `forced_pcm_gap`，后者 forced gap 为零，仍只能由 fallback 到 candidate 内部持续谷底授权。

### 5.4 Retained Hard-Limit Terminal Gate

- 内部谷底与 independent forced quiet gap 都失败后，same-segment 重复转场可使用保留字符 forced edge 作为第三层候选；该路径同时覆盖 forced candidate 等于 fallback 和 forced candidate 方向错误。
- delete-end 要求 hard limit 前最后 `80ms` 的所有 `20ms` RMS 窗持续低能，delete-start 完全对称；hard limit 保留侧高能窗必须连续覆盖至少一个完整 `20ms` block，使首尾验证窗互不重叠，避免同一个爆音样本同时抬高多个 `5ms` 滑动窗。
- 语音阈值取 quiet terminal ceiling 与 retained peak 的几何均值，并以 retained peak 的相对比例设下限；不得使用固定绝对音量，因此 `1x/2x/4x` 非削波增益结果一致。
- 成功时只在 terminal quiet run 内吸附 hard limit 附近最低振幅样本，final 严格位于 hard limit 删除侧；失败时保持 semantic fallback，且失败 evidence 不得把已有 `retainedSpeechHardLimit` 覆盖为 null。
- 该路径解决 `29.171-29.790s` 和 `122.370-124.248s` 中“噪声底轻微变化被误认成保留起音”的问题；单点爆音或搜索窗内没有持续保留语音不能通过。

## 6. Shared Resolver Integration

`forced_alignment_transition_boundary()` 扩展为消费 transition context，或由一个小型 trust helper 在调用前构造该 context。边界缓存 key 必须包含重复歧义/trust 输入，不能只按 segment、character、direction、fallback 复用不同语义状态的结果。

数据流保持：

```text
alignment sidecar (structurally valid candidates)
  + transcript semantic units
  + current text/timeline deletion state
  + shared decoded PCM
  -> transition ambiguity + trust evaluation
  -> one persisted physical boundary + diagnostic
  -> preview / cuts / compose / FFmpeg
```

- 文案删除继续通过 `build_shared_acoustic_delete_boundaries()`。
- timeline 端点通过 `align_manual_timeline_ranges_to_audio()` 调用同一 cached transition boundary；不得复制 repeat/PCM 算法。
- `resolve_cut_draft_acoustic_boundaries()` 仍一次解码、一次 alignment cache、一次 forced boundary cache，返回 text/timeline 物理范围和统一 diagnostics。
- 生成阶段只消费持久化范围，不运行 trust evaluation。

## 7. Frontend Display Projection

后端返回的 suggestion/cut draft range 同时携带两套坐标：

- `originalStart/originalEnd`：文字选择和展示语义。
- `start/end`：声学解析后的媒体切点。

`buildSegmentTextRuns()` 继续逐字符投影，但 `suggestionTextRangeKeysAtTime()` 必须先读取 `original*`，旧 suggestion 缺少这些字段时才兼容回退到 `start/end`。`selectedTextRangeKeysAtTime()` 已遵守该规则，不另建第二套删除状态。

普通保留字符的 `presentationKey` 只能因为语义 suggestion 边界改变，不能因为物理静音扩展、PCM 校准或 `noSpeechRanges` 改变。因此：

```text
semantic suggestion: [28.454, 29.171]
physical delete:     [28.328, 29.171]
retained "人" midpoint: 28.3345

media:   "人" 位于物理删除扩展内，由媒体安全范围处理
display: "人" 位于语义 suggestion 外，继续和前文合并
```

该修复不修改 `selectedRanges`、草稿 payload、MediaController keep ranges 或 compose 请求。旧 suggestion 没有 `original*` 时保持既有展示行为，避免历史任务丢失建议边界。

列表行继续用源时间 `data-display-start/end` 负责排序、原片试听和播放高亮，但 `.segment-time` 统一投影为剪后时间。部分保留行显示其首个保留片段的 edited start；完整删除行没有 retained timing 时，使用 `sourceTimeToEditedTime(sourceStart)` 显示折叠后的拼接点。这样列表可见时间单调，同时不改变任何源时间交互。

## 8. Diagnostics And Compatibility

在现有诊断基础上增加：

```text
structureValid
boundaryTrustworthy
trustReason
repeatAmbiguous
repeatOverlapText / repeatOverlapLength
forcedCandidate
pcmCorroborated
pcmValleyStart / pcmValleyEnd
pcmGapCorroborated
pcmGapStart / pcmGapEnd
retainedSpeechHardLimit
fallbackReason
```

旧 sidecar、旧草稿和旧 API 响应无需迁移。缺少新字段的历史诊断只用于展示/排查，不影响已有物理范围。新代码读取 sidecar 时仍执行结构复验；transition trust 每次草稿解析由当前语义状态派生。

## 9. Failure And Safety Matrix

| 条件 | 结果 |
| --- | --- |
| forced alignment 缺失或结构无效 | 沿用 waveform/semantic 安全降级，`boundaryTrustworthy=false` |
| 非重复转场且方向/相邻结构有效 | 保持现有 forced 主路径，避免“得/你”退化 |
| 相邻重复且有持续 PCM 谷底 | 使用佐证谷底，记录 `forced+pcm-valley` |
| 相邻重复但只有单点低能、单调斜坡或均匀低能 | 拒绝歧义 forced candidate，保护保留语音 |
| forced candidate 方向错误或越过局部硬限 | 拒绝，不扩大搜索 |
| timeline 端点命中同一状态转换 | 复用同一 transition cache 和最终点 |
| 音频解码失败 | 保留语义/手动原始边界，不猜测扩张 |
| suggestion 有 `original*` 且物理范围更宽 | 展示使用 `original*`，媒体继续使用 `start/end` |
| 历史 suggestion 缺少 `original*` | 展示兼容回退 `start/end`，不丢失旧建议 |

## 10. Verification Strategy

- Adapter/metadata：结构有效与转场可信分离；重复 sidecar 仍可缓存并复验。
- Unit：相邻完整短语、局部重叠、单字符重复、非重复大偏差、持续谷底、单点尖谷、斜坡、均匀低能和多组增益。
- Resolver：文案与 timeline 同一 boundary key、语义/物理双范围、diagnostics、cache key 和无二次推理。
- API/generation：cut-draft revision、撤销/重做、`/cuts`、`/compose` 和生成阶段零次重算。
- Frontend：物理起点提前捕获“人”、物理终点延后覆盖“你身”的两个回归；断言展示使用 `original*`、连续保留文字合并，同时 payload 与媒体范围不变。
- Real media：最新 `(7).mp4` 对应源草稿走产品 resolver 和完整 FFmpeg/AAC；对比 `142.010s` 与约 `141.880s` 的二次 ASR、被删尾音指纹、保留起音 PCM/延迟/RMS，并完成人耳试听。

## 11. Cross-Segment Full-Row Transitions

- `transcript_acoustic_character_units()` 为每个 unit 标记 segment 字符总数。只有 units 列表中相邻、左侧是前一 segment 最后一字、右侧是后一 segment 第一字且 segment index 连续时，才是 `cross_segment` transition。
- 两侧都携带各自通过读取时复验的 forced timing 且 `left._forcedEnd <= right._forcedStart` 时，删除终点使用左侧 forced end、删除起点使用右侧 forced start；另一侧 forced 边界是 retained hard limit。
- forced 缺失、方向无效或两段 timing overlap 时，不放开同段 token extension，也不运行第二套波形算法。共享 resolver 复用 sustained-valley helper，在 semantic fallback 与 retained-side forced/acoustic/semantic 安全界限间搜索；谷底后的首次持续能量回升仍是最终 hard limit。
- PCM fallback 成功必须记录 `transitionScope=cross_segment`、`boundaryTrustworthy=true`、`trustReason=cross_segment_pcm_valley`；没有持续谷底或保留语音立即起音时记录 `cross_segment_pcm_not_corroborated` 并保持 semantic fallback。
- timeline 的 `0.20s` 门槛约束用户端点到 transition semantic fallback 的距离，而不是最终声学点到用户端点的距离。只有 `boundaryTrustworthy=true` 且用户端点靠近该 transition 时才可复用较远的 final；完全位于相邻字符/segment quiet gap 的范围继续保持精确。

## 12. Rollback

变更集中在 transition trust 和测试。若真实媒体 gate 未通过，回滚新 trust helper 和诊断字段即可恢复上一版 forced 主路径；不删除 sidecar、不改写 jobs/history，也不回滚既有语义/物理双范围和 revision 契约。
