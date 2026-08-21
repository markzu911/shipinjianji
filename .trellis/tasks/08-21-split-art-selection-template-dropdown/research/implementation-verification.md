# 实施与验证记录

## 已实现

- `EditorArtTool` 拆分为“选择艺术字 / 艺术字设置 / AI 推荐”三个同级 tab；实例列表、自定义新增和视频文案整轨入口只位于选择页。
- activate 根据 Store selection 选择默认页；选择、新增、全文轨和 AI 确认成功后进入设置页，删除最后 selection 后返回选择页。
- 模板网格替换为自定义 trigger + listbox；触发器和 option 只渲染模板名称及 `renderCharacters()` 样式样例。
- listbox 支持鼠标、外部点击关闭和 Enter/Space/Arrow/Home/End/Escape/Tab；切 tab、deactivate 和 selection 消失都会关闭菜单。
- 模板提交继续使用 `commitSelectedPatch()` 与 ArtModel 的 track-aware 更新；未修改 Store、媒体、时间轴、草稿或 compose schema。
- 独立检查将自动回退条件收紧为艺术字 selection 真实从有变无；主动查看空设置页不会被无关 Store revision 打断。
- 样式样例标记为 `aria-hidden`，模板触发器与 option 的无障碍名称只朗读模板名。

## 验证结果

- `node --check web/editor-art-tool.js`：通过。
- 全部 `web/*.js` `node --check`：通过。
- `python -m compileall -q server`：通过。
- `pytest -q tests/app/test_frontend_contracts.py`：`28 passed`。
- `pytest -q tests/app/browser/test_editor_workflows.py -k "art or template or tool_switch"`：`18 passed, 13 deselected, 1 xfailed`。
- `pytest -q tests/app/browser`：`31 passed, 1 xfailed`。
- 完整套件排除两个仓库已知挂起媒体端点后：`336 passed, 2 deselected, 1 xfailed`。
- `git diff --check`：通过（仅 Git 的 LF/CRLF 提示）。

## 已知测试限制

直接运行完整 `pytest -q` 在约 42% 后命中既有挂起点并连续 60 秒无输出，已中止且未留下运行会话。按前一任务既定门禁排除以下两项后，其余完整套件通过：

- `tests/app/test_cut_rendering.py::test_cut_endpoint_renders_preview_video`
- `tests/app/test_transcription_suggestions.py::test_upload_extracts_audio_and_returns_transcript`

本次新增的模板下拉真实浏览器测试分别锁定 manual 单项和 transcript 整轨的单 revision、timing/range 不变，以及键盘、鼠标、外部关闭和 375px 无溢出；额外回归锁定空设置页不受无关 project revision 影响。
