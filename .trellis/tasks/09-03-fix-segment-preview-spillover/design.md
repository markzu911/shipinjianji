# 技术设计：单段试听终点优先于删除区间跳转

## Architecture

保持现有唯一媒体所有者和帧时钟：`EditorMediaController` 继续产生 source-time frame，`web/app.js` 继续拥有文案试听瞬时状态。变更只收敛 `web/app.js` 的单段结束状态机，不新增模块、媒体实例或循环。

新增一个单段结束 helper，接收本次观察到的 source time：

```text
finishTranscriptPreviewIfNeeded(sourceTime) -> boolean
```

- 无活动范围或尚未到终点时返回 `false`，不产生副作用。
- 到达 `end - CUT_SPEECH_BOUNDARY_EPSILON` 时先快照终点并立即清空 `transcriptPreviewRange`，再暂停、校准到终点、更新反馈，最后返回 `true`。
- 先清空状态保证暂停、seek 和 frame-clock 同步引发的嵌套/迟到回调均为 no-op。

## Frame Data Flow

```text
MediaController frame(sourceTime)
  -> finishTranscriptPreviewIfNeeded(sourceTime)
       -> true: pause + clear + seek exact end + feedback; stop this frame
       -> false: skipSelectedRangeDuringPlayback(sourceTime)
            -> skipped: reset cursors; stop this frame
            -> not skipped: update visual frame
```

`updateTime()` 不再复制单段结束逻辑，只调用同一 helper。现代浏览器由 rVFC/RAF 在一个帧预算内处理；无帧 API 的环境仍由现有 `timeupdate` 模式降级。不得让 `updateTime()` 成为第二个循环。

## Ordering And Idempotence

- 段尾 gate 必须排在删除跳过之前，因为物理删除范围允许向相邻保留语音方向扩展并与语义段尾重叠。
- helper 必须在 pause/seek 前清空活动范围。`seekSource(previewEnd)` 可能同步发出 frame，清空后的重入不得再次结束。
- frame 路径命中终点后直接返回，不更新旧 source time 对应的高亮，也不执行删除区间 seek。
- `seekCutPreview()` 现有的主动清理语义保持不变；旧范围已经被主动清除时，任何迟到回调均不能恢复它。

## Compatibility

- `skipSelectedRangeDuringPlayback()` 的公共连续播放语义和“单段范围内允许试听删除内容”条件保持不变。
- 终点仍使用展示行 `displayEnd`，不切换到 semantic 或 physical delete end。
- 终点仍精确校准，保留现有播放头与状态反馈。
- 不修改 Store、cut draft、后端 API 或持久化格式，无迁移需求。

## Timeline Label Typography

文案轨片段继续使用现有绝对定位、宽度投影、换行与裁切规则，只把标签的两端对齐改为居中。删除后的 reconcile 仍复用原节点和文本内容，不引入新的渲染分支；真实浏览器回归直接检查删除后标签的计算样式，防止末行两端对齐重新拉开中文字符。

## Verification Design

1. Node 行为测试构造活动单段终点与删除范围重叠的状态，调用逐帧入口并断言只发生 pause/终点 seek/反馈，不发生删除尾 seek或视觉更新。
2. 同一测试重复调用 frame/timeupdate 等价入口，证明结束动作幂等；无活动范围时仍验证删除跳过先于视觉更新。
3. 真实 Chromium fixture 使用本地短媒体和三段文案：当前段、紧邻删除段、下一保留段。物理删除范围向左覆盖当前段尾，复现现场竞态。
4. 点击真实“播放当前段落”按钮，逐帧记录最大 `currentTime`，断言在一个 30fps 帧预算内暂停、未跳到删除范围尾部、最终回到 `displayEnd`，并核对无 `src/load()`。
5. 在现有 retained projection 浏览器流程删除首个文案片段，断言剩余标签文本不变、计算样式为居中且末行不使用两端对齐。

## Risks And Rollback

- 风险：pause/seek 触发同步 frame 导致重入。通过“先清空状态”和行为测试防护。
- 风险：过早阈值截掉段尾。沿用现有 2ms epsilon，并以单帧预算验收，不扩大提前量。
- 风险：改变公共播放删除跳过。保留现有无活动范围测试并跑完整浏览器回归。
- 回滚点：产品改动限定在 `web/app.js`、`web/styles.css` 与对应测试；若回归失败可恢复原调用顺序和标签对齐规则，不涉及数据迁移。
