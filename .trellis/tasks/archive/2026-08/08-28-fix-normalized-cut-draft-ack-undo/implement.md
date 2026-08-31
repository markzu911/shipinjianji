# 规范化剪辑草稿确认与撤销修复计划

## Execution

- [x] 在浏览器测试中加入可持久化的规范化 cut-draft 响应 fixture，先稳定复现 revision 未推进、undo 未清服务端和 redo 409。
- [x] 增加结构命令身份校验，覆盖 text/no-speech/timeline/split 的 key、唯一性、文字、初始化标记、boundary mode 和 split ownership，不再用时间数值全等拒绝合法规范化。
- [x] 扩展既有服务端对齐入口：先完整构造 text/no-speech/timeline/split 权威 snapshot，通过校验后再原子安装，并生成 post-normalization payload/signature。
- [x] 调整 `persistCutDraft()` 成功响应顺序：先验证并记录权威 revision，再判断结构兼容、安装权威 snapshot、更新 post-normalization desired/ack。
- [x] 保持 latest-state-wins：旧响应不覆盖在途新编辑，下一请求使用刚推进的 revision。
- [x] 保持协议异常可见且可恢复：不假报保存成功，不无限重试，同一 job 的下一不同签名能用最新 revision 保存。
- [x] 验证服务端物理范围正确进入当前 history `after`，undo/redo/refresh 与 API 草稿一致。
- [x] 更新 `web/index.html` 的 `app.js` 资源版本和 `tests/app/test_frontend_contracts.py` 对应断言。

## Validation

1. 定向浏览器回归：
   `\.venv\Scripts\python.exe -m pytest -q tests/app/browser/test_editor_workflows.py -k "cut_draft or timeline_range"`
2. 剪辑草稿与边界回归：
   `\.venv\Scripts\python.exe -m pytest -q tests/app/test_cut_draft.py tests/app/test_cut_acoustic_boundaries.py tests/app/test_frontend_contracts.py`
3. 完整浏览器工作流：
   `\.venv\Scripts\python.exe -m pytest -q tests/app/browser`
4. 完整测试：
   `\.venv\Scripts\python.exe -m pytest -q`
5. 语法与补丁检查：
   `\.venv\Scripts\python.exe -m compileall -q server tests`
   `git diff --check`

## Validation Evidence

- `tests/app/test_frontend_contracts.py`: 36 passed.
- `tests/app/test_cut_draft.py tests/app/test_cut_acoustic_boundaries.py`: 156 passed.
- 新增 Chromium 规范化删除、撤销、刷新、重做回归：passed.
- `tests/app/browser`: 54 passed.
- 完整测试：491 passed, 1 warning.
- `node --check web/app.js`: passed.
- `\.venv\Scripts\python.exe -m compileall -q server tests`: passed.
- `git diff --check`: passed；仅有工作区既有 LF/CRLF 提示。
- 首轮完整浏览器检查曾在未修改的 1 秒样片播放保持用例上出现播放自然结束的时序失败；未扩展本任务范围修改该用例，最终最新代码的完整浏览器复跑 54 条全部通过。
- 独立 reviewer 补强结构拒绝、完整原子安装、post-normalization retained projection 和规范化旧响应 rebase 断言；定向 frontend + cut 为 192 passed，完整浏览器再次复跑为 54 passed。
- reviewer 的两次完整 pytest 分别为 `490 passed, 1 failed` 与 `489 passed, 2 failed`；残余均为既有时序门槛（1 秒样片自然结束、101.4ms/100ms 性能阈值和单次 208ms long task），对应测试独立复跑通过，且本任务完整浏览器 54/54 通过。实现阶段曾有一次完整 pytest 491 passed 的干净结果。

## Review Findings Resolved

- 200 响应 revision 必须是正安全整数且严格递增；小数、字符串和非有限值均不能推进本地权威 revision。
- 未知 `boundaryMode` 必须作为结构不一致拒绝，不能静默降级为 `speech_safe`。
- 规范化响应到达时保留用户当前未提交的时间轴拖选，只替换已提交且 key 匹配的范围。
- 结构拒绝覆盖缺失/重复/额外 key、文字变化、未知 `boundaryMode` 和 split ownership 变化；完整安装覆盖 text/no-speech/timeline/split，retained projection 使用 post-normalization signature/revision。

## Review Gates

- “已保存”只能在当前 canonical signature 被当前 revision acknowledged 后显示。
- 200 响应一旦确认 revision 已推进，任何后续错误分支都不能继续发送旧 revision。
- 物理 `start/end` 可以变化；用户语义 identity 不得被 VAD 反写或放宽比较。
- undo 后必须查询服务端状态，不能只断言 DOM；refresh 后必须再次核对服务端和页面。
- 新 fixture 不访问真实模型、用户 job、`data/jobs` 或网络。

## Risk And Rollback Points

- 数值全等会继续拒绝合法自然字符/VAD 规范化，完全放弃身份校验又会吞掉协议错误：必须校验结构命令身份并把全部时间数值交给服务端权威 snapshot。
- 过早设置 acknowledged 会产生新的假保存：revision 推进与 signature ack 分开维护。
- 对齐旧响应会覆盖新编辑：只在 `stillDesired` 为真时应用 snapshot。
- history 对齐错误会让 redo 漂移：保留既有 history reconcile owner，不创建第二套撤销栈。
