# 实施计划：修复单段试听越界

- [x] 1. 在 `web/app.js` 提取幂等的单段试听结束 helper，沿用当前 pause、范围清理、精确终点 seek 和反馈语义。
- [x] 2. 在 `handleCutPlaybackMediaFrame()` 最前调用终点 helper；命中后立即返回，确保删除区间跳转和视觉更新均不执行。
- [x] 3. 让 `setupCutPreviewControls().updateTime()` 复用同一 helper，保留 `timeupdate` 降级并消除重复结束逻辑。
- [x] 4. 扩展 `tests/app/test_frontend_contracts.py` 的播放帧行为测试，覆盖终点与物理删除范围重叠、幂等重入、公共播放删除跳过和事件顺序。
- [x] 5. 在 `tests/app/browser/` 增加短媒体三段 fixture/工作流，真实点击单段按钮并测最大播放时间、最终终点、暂停状态、下一段未进入及基础媒体无 reload。
- [x] 6. 运行 JavaScript 语法检查和聚焦测试：
  - `node --check web/app.js`
  - `.\.venv\Scripts\python.exe -m pytest -q tests/app/test_frontend_contracts.py -k "playback_frame or segment_preview"`
  - `.\.venv\Scripts\python.exe -m pytest -q tests/app/browser/test_editor_workflows.py -k "segment_preview"`
- [ ] 7. 运行完整质量门：
  - `.\.venv\Scripts\python.exe -m pytest -q tests/app/browser`
  - `.\.venv\Scripts\python.exe -m pytest -q tests/app`
- [x] 8. 核对 diff 只包含任务文档、规范、`web/app.js` 和目标测试，不覆盖工作区既有未提交改动；完成 Trellis check、规范更新判断和收尾。
- [x] 9. 将文案轨标签从末行两端对齐改为自然居中，并在删除片段的真实浏览器流程与静态 CSS 契约中锁定排版结果。

质量门记录：完整非浏览器 `tests/app` 为 `445 passed`；完整浏览器为 `55 passed, 2 failed`，其中长列表交互性能单独复跑通过，既有连续播放性能 gate 单独复跑仍为 P95 `16.73ms > 16ms`。新增段落试听 Chromium 回归稳定通过，未降低既有性能阈值。

文案轨排版验证：完整 `tests/app/test_frontend_contracts.py` 为 `41 passed`；`test_server_retained_projection_keeps_editable_timeline_paragraphs` 为 `1 passed`。删除后文本、居中计算样式、末行非两端对齐和基础媒体零 reload 均通过。
