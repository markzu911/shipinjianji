# 时间轴文案与实际保留文案不一致：诊断记录

## 结论

问题不是 CSS 截断或时间轴组件单独渲染错误。剪后文字在进入时间轴前就已经丢字，后端生成的剪后 transcript 也有同样问题。

首个错误层是“语义删除状态 -> 物理剪切后时间”的文字投影层：代码先正确判断某个字在语义上应保留，又要求它的粗粒度 ASR 时间与物理保留区间相交。重复口播附近的 ASR 时间明显偏移，导致语义上保留的“一起”和下一句首字“你”落在物理删除区间内，最终被丢弃。

## 现场数据

- Job：`99c068e5-7442-482f-84d0-5b36ab8a39e5`
- Project state 中 `cutDraft.present=true`，`cutDraft.revision=1`
- 第一处重复：语义删除 `28.454-29.171s`，物理删除 `28.299-29.807s`
- 第二处重复：语义删除 `33.160-37.120s`，物理删除 `32.730-37.790s`
- 强制字级对齐显示，实际保留的第二个“一起”从约 `29.810s` 开始；下一个保留的“你”从约 `39.850s` 开始。
- 粗粒度 ASR 却把应保留的“一起”标在 `29.171-29.649s`，把应保留的“你”标在 `37.120-37.480s`；两者都完全落在对应的物理删除区间内。
- 该段 acoustic alignment 的 coarse-token 最大边界偏差达 `2.730s`，足以证明不能用粗粒度 token 时间决定保留字符的生死。

## 数据流对照

| 层 | 结果 | 判定 |
| --- | --- | --- |
| 原始 editable transcript | `所有人一起给一起给你画...` / `你身边你身边人人都觉得你身边人人都觉得...` | 原始 ASR 包含重复，符合现场 |
| 文字剪辑列表 | `所有人` / `一起给你画...` / `你身边人人都觉得...` | 正确；删除态使用 `originalStart/originalEnd` 语义范围 |
| `getRetainedSegmentParts()` | `所有人给你画...` / `身边人人都觉得...` | 首次出错；语义保留的 token 被物理 span 相交条件丢弃 |
| TimelineController / Store frame / 公共时间轴 | 沿用上述错误 parts | 下游展示错误，不是首个错误层 |
| `build_retained_transcript()` | 同样丢失“一起”和“你” | 后端权威剪后 transcript 也错，与前端缺陷同源 |

## 代码因果链

1. `web/app.js` 的 `renderCutSegments()` / `buildSegmentTextRuns()` 使用语义删除范围，因此左侧文字列表保留字符正确。
2. `web/app.js` 的 `getRetainedSegmentParts()` 在语义删除判定之外，还在 `2183-2184` 行要求 token 时间与物理保留 span 相交。语义上保留但粗时间完全在物理 cut 内的字符会被 `continue`。
3. `renderCutTimelineTextSegments()` 直接用 `getRetainedSegmentParts()` 的 `part.text`，因此时间轴如实显示了已经错误的上游数据。
4. `server/app.py` 的 `build_retained_transcript()` 先用语义 `delete_ranges` 保留单元，再用物理 `timeline_ranges` 映射时间；当粗时间完全落在物理 cut 中，`mapped_end <= mapped_start` 后在 `5722-5723` 或 `5744-5745` 行被丢弃。
5. 因此错误同时污染 live Store transcript、`/cuts`、`/compose` 以及下游生成 transcript，不能只修时间轴 DOM 文字。

## 回归判定

- 最近的首字残音修复 `f033bd7` 不是根因。修复前的物理边界约为 `29.789s`，仍然完全覆盖粗粒度 ASR 中应保留的“一起”的 `29.171-29.649s`，所以丢字在该修复前就会发生。
- `4c1724d` 修正了左侧文字列表的语义删除展示，但没有统一时间轴和后端 retained transcript 的投影契约。
- 现有 `tests/app/test_frontend_contracts.py::test_frontend_live_transcript_uses_semantic_range_and_physical_retiming` 只覆盖“保留字符的粗时间与保留 span 部分相交”，没覆盖“粗时间完全落在物理 cut 中”。

## 建议的最小修复范围

保留文字只由语义删除状态决定；字符确定保留后，再用权威强制字级对齐和过渡边界将其投影到物理剪后时间。前端 `getRetainedSegmentParts()` 与后端 `build_retained_transcript()` 必须共享同一套投影契约。

必需的回归覆盖：

1. 粗粒度时间完全落在物理 cut 内时，语义保留的“一起”仍存在。
2. 第二处重复后的保留句仍以“你身边人人都觉得”开头。
3. 文字列表、时间轴、live Store transcript、`/cuts`、`/compose` 和最终 transcript 的文字一致，且与可听内容一致。
4. 不回退已有首字残音修复，不改写用户 job/cut draft，不把问题缩减为纯前端展示修补。
