# 修复单段试听越界播放下一段

## Goal

点击任一文案行的“播放当前段落”后，只播放该展示段落，并在段尾及时暂停；即使段尾与已删除文字的物理范围重叠，也不得跳过删除范围后继续泄露下一条保留文案。

## Background

- `web/app.js:4922` 的 `previewTextSegment()` 使用展示行 `data-display-start/end` 设置 `transcriptPreviewRange`，入口范围正确。
- `web/app.js:6811` 的 `updateTime()` 仅由 `timeupdate` 等低频媒体事件调用，并在这里负责单段暂停、清理范围和校准播放头。
- `web/app.js:6771` 的逐帧入口先调用 `skipSelectedRangeDuringPlayback()`，但不检查单段试听终点；`web/editor-media-controller.js:40` 按 `requestVideoFrameCallback -> requestAnimationFrame -> timeupdate` 提供更高频的唯一帧时钟。
- 提交 `7f0aa1f` 把删除区间跳过从 `updateTime()` 移到逐帧入口，却把单段停止留在原处，形成“先跳过删除、后处理段尾”的竞态。
- 用户截图对应的真实工程中，目标行“而是你身边所有人”范围为 `26.534-28.454s`，紧随其后的已删除“一起给”物理范围合并为 `28.225-29.810s`。逐帧时间到 `28.452s` 后试听保护失效，现有代码会先 seek 到 `29.810s`，随后 `timeupdate` 才暂停并把播放头写回 `28.454s`；最终 UI 位置正确，但下一段开头已经出声。
- `tests/app/test_frontend_contracts.py:2288` 只验证无单段试听时“先跳过删除、再更新视觉”；静态契约只检查入口和状态变量存在。`tests/app/browser/test_editor_workflows.py:557` 的真实媒体测试覆盖公共连续播放性能，没有覆盖点击单段按钮后的段尾泄露。

## Requirements

- R1：逐帧播放处理必须在任何删除区间跳转或视觉更新之前检查活动 `transcriptPreviewRange` 是否到达终点。
- R2：到达单段终点时必须暂停、清除当前试听范围、把媒体与播放头校准到该段 `displayEnd`，并只产生一次“当前段落播放结束”反馈。
- R3：逐帧路径与 `timeupdate` 降级路径必须复用同一个幂等结束动作；迟到的 frame、`timeupdate`、`seeking` 或 `seeked` 不得重复结束、跳到删除范围尾部或覆盖后续用户操作。
- R4：活动单段范围内继续允许试听已删除文字；活动范围结束后恢复公共播放的删除区间自动跳过语义。
- R5：公共播放、普通 seek、点击另一段、暂停、结束、项目重置和播放高亮/跟随行为保持兼容，不新增第二个帧循环或媒体控制器。
- R6：增加行为测试和真实 Chromium 回归，直接覆盖“段尾落在物理删除范围内”的竞态，并验证基础媒体 `src/load()` 不变。
- R7：删除文案片段并重绘时间轴后，保留文案使用自然居中排版，不得通过末行两端对齐把中文字符强制铺满片段宽度。

## Acceptance Criteria

- [x] AC1（R1、R2）：正常倍速点击单段播放后，媒体在 `displayEnd` 一个 30fps 帧预算内暂停，最大观察时间不进入下一保留段。
- [x] AC2（R1、R3）：当试听终点位于合并删除范围内部时，事件顺序为“结束单段试听”，不得先 seek 到删除范围尾部；结束反馈、暂停和终点校准各执行一次。
- [x] AC3（R3、R4）：逐帧入口和 `timeupdate` 对同一终点重复调用保持幂等；单段范围内不跳过目标内容，结束后公共播放仍自动跳过已删除区间。
- [x] AC4（R5）：主动 seek 或点击另一段会清理旧范围，迟到回调不会把媒体写回旧终点；播放行高亮、跟随和公共播放状态无回归。
- [ ] AC5（R6）：聚焦 Node/前端契约测试、目标真实浏览器用例、完整 `tests/app/browser` 与完整 `tests/app` 回归通过，且浏览器用例中基础 video `srcWrites/loadCalls` 均为零。
- [x] AC6（R7）：删除首个文案片段后，保留标签文本不变，计算样式为居中且 `text-align-last` 不为 `justify`；刷新后仍保持相同文本投影。

## Out of Scope

- 不修改 ASR、VAD、PCM、`mediaStart/mediaEnd`、文字语义范围或物理删除边界算法。
- 不改变公共连续播放、删除区间内容、视频导出、时间轴映射或文案列表视觉。
- 不重构 `EditorMediaController`、新增播放器、Web Audio 管线或第二套定时器/帧循环。
