# 优化编辑器文案交互与播放性能

## Goal

消除长文案工程中点击删除/恢复后的明显停顿，以及播放切段时绿色活动文案跟随造成的间歇掉帧；保持剪辑语义、草稿保存、撤销/重做、公共预览、时间轴和最终生成结果不变。

## Background

- 当前真实工程加载后约有 2707 个 DOM 节点、273 个按钮；空闲 3 秒内主线程最大延迟仅 5ms，说明持续空载和服务端不是主要瓶颈。
- 播放 0-13 秒期间，文案切换到“说实话”“以前我也这么想”等活动段时出现 22-33ms 延迟；峰值与 `web/app.js:2471` 的活动行切换及 `web/transcript-follow-scroll.js:479` 的真实行 reparent/列表 FLIP 同时发生。
- 长文案浏览器回归 `test_cut_interaction_long_fixture_performance_and_work_counts` 稳定超出既有预算：最新实测 P50 77.6ms、P95 108.8ms、最大 109.7ms，并记录 66-136ms long task。
- 点击 handler 的同步部分仅 0.7-3.9ms；主要耗时发生在 `web/app.js:3926` 的后置 effect，它调用 `renderCutSegments()`、EditorSuite 同步、时间轴文字/片段/范围重建和缩略图调度。
- 现有缩略图使用 source-time 内存/IndexedDB 缓存；删除、恢复和拆分不得重新抽帧或改变基础视频 source。
- 既有文案跟随契约要求绿色活动行唯一、播放按钮唯一、三行下移锚点、底部 clamp、用户滚动中断、reduced-motion 和迟到动画隔离。

## Requirements

- R1：文案删除、恢复、空白切换、撤销/重做和时间轴提交的可见反馈不得等待服务端保存、缩略图生成或整棵文案/时间轴 DOM 重建。
- R2：单项文字选择变化优先增量更新受影响的文案行、汇总和时间轴投影；只有结构变化、服务端规范化改变结构或明确失效时才允许完整重建。
- R3：一次稳定 cut 命令仍只产生一个 `CUT_TIMING_CHANGED`，保留每个命令独立的撤销边界、latest-state-wins 草稿队列、服务端规范化响应和生成前 flush 契约。
- R4：删除/恢复只重投影已有 source-time 缩略帧，extractor 创建、基础 video `src/load()`、逐帧 seek 和 JPEG 编码次数保持为 0。
- R5：播放帧热路径继续只消费缓存索引；同一活动 key 不做布局读取、滚动提交或动画重建。换段时的布局与动画工作必须受控，不能产生超过预算的主线程长任务。
- R6：保留绿色活动文案、三行下移锚点、底部完整可见、真实按钮唯一、占位无交互、用户滚动中断和 reduced-motion 结果一致。
- R7：不以降低文字边界精度、跳过服务端 VAD/声学校准、减少撤销可靠性或延迟本地恢复快照换取速度。
- R8：性能修复必须同时覆盖真实工程浏览器操作和隔离长 fixture；不能只优化测试 mock 或用放宽阈值通过。

## Acceptance Criteria

- [x] AC1：至少 600 个可见字符、30 个既有删除范围的浏览器 fixture 连续 10 次删除/恢复，input 到 post-commit 第二个 rAF 的 P95 不高于 80ms，最大不高于 120ms，且没有超过 100ms 的新增 long task。
- [x] AC2：同一 fixture 中点击同步阶段 P95 不高于 10ms；一次命令最多一次 Store `CUT_TIMING_CHANGED`、一次 history 持久化和一次防抖后的 PUT，PUT 最大并发为 1。
- [x] AC3：单项选择变化不会调用完整 `renderCutSegments()`，不会替换未受影响的文案行，不会重建全部时间轴文字节点；结构变化和服务端权威规范化路径仍能按需完整重建。
- [x] AC4：连续播放至少 15 秒并跨越 8 个文案/空白边界，切段 P95 主线程延迟不高于 16ms、单次最大不高于 32ms，且不存在超过 50ms 的 long task。
- [x] AC5：播放跟随保持绿色活动行三行下移、底部 clamp、按钮唯一、占位无交互、用户中断、同 key 去重、迟到动画隔离和 reduced-motion 契约。
- [x] AC6：删除/恢复/撤销/重做/时间轴提交期间新增 extractor、thumbnail seek、基础 video `src/load()` 均为 0；缩略帧仍连续覆盖剪后时间轴。
- [x] AC7：草稿 revision、服务端规范化、刷新恢复、生成前 flush、工具切换、艺术字/画中画 selection 和公共媒体 identity 回归通过。
- [x] AC8：相关 Node/静态契约、真实浏览器测试、完整前端测试、JavaScript 语法和 `git diff --check` 通过；无新增 console error、pageerror 或 failed request。

## Out of Scope

- 不修改 VAD、强制对齐、文字语义边界和最终 FFmpeg 生成算法。
- 不引入 React/Vue、Web Worker 媒体副本、第二套 Store/时间轴或后端 API。
- 本轮不做完整文案列表虚拟化；只有增量渲染和跟随优化后仍无法达标时另建任务。
- 不删除用户草稿、历史版本、媒体、艺术字或画中画素材。

## Key Decisions

- 优先保证播放顺滑：保留绿色活动行、三行锚点、底部 clamp 和真实按钮唯一，但取消换段时的整列表 FLIP；活动行直接进入最终展示位置。
- 普通选择变化走稳定 key 的局部 DOM 对账；文案拆分/合并、权威文案替换、任务切换和结构校验失败继续走完整重建。
- 文案列表虚拟化不与本次修复绑定；只有局部对账和跟随简化后仍无法达到性能门槛时另行规划。
