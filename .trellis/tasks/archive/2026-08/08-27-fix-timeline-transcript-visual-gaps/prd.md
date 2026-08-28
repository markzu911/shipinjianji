# 修复时间轴文案空隙与刷新跳变

## Goal

修复公共剪辑时间轴中文案块在刷新后出现大量短空隙、且刷新首帧与稳定状态几何不一致的问题，同时保留长静音的真实可视反馈，并确保显示修复不改变任何语义或媒体时间边界。

## Background

- 时间轴文案块使用绝对定位，空隙来自相邻 retained transcript 时间戳之间的真实 ASR 静音，不是 CSS `gap` 或 margin。
- 现场数据包含 `0.140s`、`0.805s`、`0.705s` 等短间隔，也有 `2.725s` 的长静音。
- 刷新时早到的 retained projection 可能在结果时间轴视口仍为 `0px` 时渲染文案节点；轨道没有 inline width，首个可见帧会先使用 CSS `min-width: 100%`，随后正常 effect 才按文字密度写入真实宽度，形成几何跳变。
- `getEditableSegmentCoverageEnd()` 已定义最多覆盖 `1.5s` 短间隔的意图，但 `getRetainedSegmentParts()` 中的 `displayEnd` 未进入文案轨道几何，规则没有生效。
- 截图只作为问题证据，不作为产品指令。

## Requirements

- R1：`sourceStart/sourceEnd`、retained transcript、ASR 字词时间、播放高亮、seek、删除、VAD 和导出必须保持不变。
- R2：时间轴文案块使用独立的 `layoutStart/layoutEnd` 显示范围；相邻可见文案之间的剪后时间间隔不超过 `1.5s` 时，前一块的显示终点覆盖到下一块起点。
- R3：超过 `1.5s` 的真实长静音必须继续显示为空隙，不允许把整条文案轨无条件铺满。
- R4：删除导致的 source-time 折叠必须先投影到 edited time，再判断当前可见间隔；显示范围不能重新占用被删除的媒体时长。
- R5：结果面板必须在首次时间轴测量前进入可布局状态，首个可见绘制与后续服务端 retained projection、缩略帧生成和刷新后的稳定几何一致。
- R6：修复只落在浏览器显示层，不修改后端 transcript、cut draft schema、持久化数据或媒体处理。

## Acceptance Criteria

- [x] AC1：相邻可见文案剪后间隔为 `0.140s`、`0.705s` 或 `0.805s` 时，前一块 `layoutEnd` 等于下一块 `layoutStart`，像素间隙不超过舍入误差。
- [x] AC2：相邻可见文案间隔为 `2.725s` 时，前一块保持自身终点，长静音仍可见。
- [x] AC3：文案块的 `data-source-start/data-source-end` 及播放索引仍使用原范围；显示覆盖不改变 seek、活动高亮、删除 payload 和 live Store transcript。
- [x] AC4：删除区间存在时按 edited-time 相邻关系计算显示范围，不跨回已经删除的 source duration。
- [x] AC5：刷新后的首个可见布局与稳定布局一致；服务端 retained projection 到达和缩略帧生成不会重新制造短空隙或改变长静音规则。
- [x] AC6：前端定向单元/契约测试、真实浏览器工作流、`git diff --check` 通过。

## Out Of Scope

- 修改 ASR、VAD、PCM、forced alignment 或任何删除边界算法。
- 改写服务端 transcript 时间戳或历史 job/cut draft。
- 隐藏所有静音、改变时间轴点击/拖动/播放头交互或调整文案视觉样式。

## Key Decision

使用“语义/媒体范围”和“视觉布局范围”双范围契约：前者继续作为权威，后者仅在 DOM 几何中覆盖短间隔。本任务范围单一，按轻量任务执行，PRD 足以约束实现。
