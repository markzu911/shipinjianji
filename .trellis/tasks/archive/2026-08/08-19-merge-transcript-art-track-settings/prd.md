# 合并文案艺术字轨道并统一设置

## Goal

把“一键添加视频文案”生成的多段艺术字在艺术字设置面板中收拢为一个“视频文案艺术字”轨道入口，让用户一次选择、一次修改即可统一调整整轨样式，同时继续按各段原有文案和时间在预览、时间轴与最终合成中播放。

## Background

- `web/editor-art-tool.js:154` 通过公共时间轴的 `art:<cueId>` 选择定位一个具体 overlay；`web/editor-art-tool.js:283` 当前又逐个遍历 `art().overlays`，因此全文文案的每个 cue 都显示成一条可选艺术字。
- `web/editor-art-model.js:673` 已经把 transcript cue 的样式字段按同一 `trackId` 批量更新，并且只允许 cue 自身接收文案/时间字段。
- `web/editor-art-model.js:732` 已经按 `trackId` 删除整条 transcript track；`web/editor-art-model.js:745` 已经在公共效果时间轴中把同一 `trackId` 的 cue 组织为一条轨道。
- `web/editor-art-tool.js:650` 生成新全文轨道时会替换现有 transcript overlays，同时保留自定义艺术字；正常项目因此只有一条当前视频文案艺术字轨道。
- 这次问题属于艺术字 inspector 的展示和选择语义不一致，不需要新增 Store schema、后端接口或第二套轨道状态。

## Requirements

- R1. 艺术字列表必须按语义轨道展示：同一 `trackId` 的 transcript cues 只显示一个“视频文案艺术字”入口；每个自定义/AI 艺术字仍各自显示一条。轨道入口显示 cue 数量和整轨最早开始至最晚结束时间。
- R2. 点击文案艺术字轨道时继续使用现有 `art:<cueId>` 选择协议选择一个代表 cue，不新增 track-selection schema。代表 cue 优先级为：已选且仍属于该轨道的 cue、当前播放时间命中的 cue、按时间排序后的首个 cue。Store 重绘和播放推进不得无故更换选择或造成列表选中态闪动。
- R3. 选中文案艺术字轨道时，详细设置标题和帮助文案必须明确说明当前编辑的是整轨；仅展示能够统一生效的模板、字体、字号、颜色、描边、阴影、字/行间距、对齐、位置和位置预设。隐藏单 cue 才有意义的文字内容、开始/结束时间、“贴合匹配文案时间”、固定为横排/自动分段的无效字段，以及“应用当前设置到全部自定义艺术字”。
- R4. 在轨道模式修改任一共享样式必须通过现有单次 Store command 更新同一 `trackId` 的全部 cue，最多增加一个 project revision；不得修改 cue 的 `id`、`text`、`start/end`、`sourceStart/sourceEnd`、`characterTimings` 或 `timingRevision`。
- R5. 轨道模式的删除按钮必须使用“删除视频文案艺术字”语义并经过现有确认流程；确认后删除该 `trackId` 的全部 cue。自定义艺术字的选择、编辑、匹配时间、批量应用和单项删除行为保持不变。
- R6. UI 合并不得把底层 cue 压成一个 overlay。公共预览、公共时间轴、草稿恢复和 compose 继续消费同一 Store frame 中的分段 cue 文案与时间；公共时间轴仍是一条 transcript track、内部包含多个 cue clips。
- R7. 分组入口必须保留按钮语义、可见选中态和至少 44px 操作高度；桌面和 375px 下不得产生横向溢出。修改的静态资源必须更新 `index.html` 资源版本及相应静态契约测试。

## Acceptance Criteria

- [x] AC1 (R1)：给定同一 `trackId` 的至少两个 transcript cues 和两个自定义艺术字，艺术字列表只显示一个“视频文案艺术字”轨道入口和两个独立自定义入口；轨道入口显示正确的段数与时间范围。
- [x] AC2 (R2)：首次点击轨道时按“当前时间命中，否则首 cue”选择代表 cue；已有同轨选择在 Store 重绘或播放推进后保持；列表始终只有一个轨道级选中态。
- [x] AC3 (R3)：选中文案轨道后只显示整轨共享设置，标题/帮助文案与删除按钮均使用整轨语义；文字、起止时间、匹配时间、固定无效字段和自定义艺术字批量按钮不可见。重新选择自定义艺术字后这些单项控件恢复。
- [x] AC4 (R4)：从 UI 修改模板、字体/字号、颜色/描边、间距/对齐和位置后，同轨所有 cue 的对应样式一致；一次交互最多增加一个 revision，`timingRevision` 以及每个 cue 的 ID、文案、编辑/源时间和字符时间完全不变。
- [x] AC5 (R5)：删除文案轨道经过确认后移除同轨全部 cue、清空无效 selection，并同步从预览、公共时间轴和 compose DTO 消失；删除自定义艺术字仍只影响目标项。
- [x] AC6 (R6)：整轨样式修改前后，公共效果时间轴仍只有一条 transcript art track 且包含原有多个 clips；播放预览和 compose 仍按 cue 独立文本与时间输出。
- [x] AC7 (R7)：相关 Node/静态测试和真实 Chromium 编辑器工作流通过；1280x720 与 375px 下无横向溢出，轨道入口操作目标不少于 44px，无未处理 console/page/network 错误。

## Out Of Scope

- 不把自定义或 AI 推荐添加的普通艺术字并入视频文案轨道。
- 不合并、重写或迁移底层 transcript cue 数据，不改变全文艺术字生成、文字剪辑重对齐、ASR 时间戳或服务端 API。
- 不新增第二套选择状态、私有时间轴、视频节点、预览状态或跨页通信。
- 不改变公共时间轴的轨道/clip 结构，也不新增前端框架或构建系统。

## Technical Notes

- 以 `trackType === "transcript" && trackId` 作为文案艺术字轨道身份；列表分组只改变 inspector 的 view model。
- 共享样式继续以 `EditorArtModel.TRANSCRIPT_STYLE_FIELDS` 和 `updateOverlay()` 为唯一写入契约，删除继续复用 `removeOverlay()`。
- 手动艺术字上限计数继续只统计非 transcript overlays；文案轨道入口不占用 `MANUAL_OVERLAY_LIMIT`。
