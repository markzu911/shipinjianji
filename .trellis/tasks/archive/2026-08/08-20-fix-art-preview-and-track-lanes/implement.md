# 实施计划：统一艺术字预览画布与分类单行轨道

## Implementation Checklist

- [x] 在 `web/editor-preview-compositor.js` 创建唯一内容 canvas，将 art/pip layer 移入其中，并实现共享的 contain/cover 几何同步。
- [x] 将艺术字样式、安全边距、位置和 PiP 尺寸统一改为源视频画布坐标；更新 resize、metadata/state 和预览模式切换后的同步路径。
- [x] 将 art/pip 拖动与 PiP 缩放的指针换算改为内容 canvas rect，保留取消、阈值、selection 和单 revision 语义。
- [x] 在 `web/editor-timeline-controller.js` 让每条 art 逻辑轨固定一个可视行，保持 `art:manual` 与 `art:transcript:<trackId>` 分行，并为 selection/focus/drag 提供确定性置顶。
- [x] 在 `server/app.py` 收敛 transcript cue 与 `characterTimings` 的最终边界归一化，在逐字时间写回后再次保证同轨不重叠并由 compose 复用。
- [x] 提升 `web/index.html` 中变更脚本的缓存版本，并同步静态契约。
- [x] 扩展 `tests/app/test_editor_preview_compositor.py`，覆盖竖屏 contain、横屏/设备 cover、metadata 延迟、resize、art/pip 几何和指针坐标。
- [x] 更新 `tests/app/test_editor_timeline_controller.py`、`test_editor_art_model.py` 和 `test_editor_project_store.py`，覆盖两个分类轨各固定一行、完全重叠手动 clip、稳定 ID、selection 和草稿恢复。
- [x] 扩展 `tests/app/test_art_text_track.py` 与相关 API/compose 测试，覆盖逐字时间重新引入重叠、最终 cue/字符 timing 不变量、下一 cue 和源锚点保真。
- [x] 扩展 `tests/app/browser/test_editor_workflows.py`，用竖屏媒体比较预览内容矩形与艺术字几何，并验证手动/文案各一行、单项编辑、compose DTO 和桌面/375px。
- [x] 完成质量检查后更新前端 UI/架构、后端媒体时间和测试规格，替换旧“重叠艺术字自动分 lane”契约。

## Validation Commands

```powershell
node --check web/editor-preview-compositor.js
node --check web/editor-timeline-controller.js
node --check web/editor-art-model.js
./.venv/Scripts/python.exe -m pytest -q tests/app/test_editor_preview_compositor.py tests/app/test_editor_timeline_controller.py tests/app/test_editor_art_model.py tests/app/test_editor_project_store.py tests/app/test_art_text_track.py tests/app/test_art_text_api.py tests/app/test_composition.py tests/app/test_frontend_contracts.py
./.venv/Scripts/python.exe -m pytest -q tests/app/browser/test_editor_workflows.py -k "art or preview or timeline"
./.venv/Scripts/python.exe -m pytest -q tests/app/browser
./.venv/Scripts/python.exe -m pytest -q
git diff --check
```

## Review Gates

- [x] 竖屏普通预览的内容 canvas 与 `object-fit: contain` 视频矩形重合，字体与坐标不再按外层黑边舞台缩放。
- [x] 设备预览 video/art/pip 使用同一个 cover transform，设备 chrome 不受影响。
- [x] 手动艺术字恒为一条逻辑轨和一条可视行，视频文案恒为另一条逻辑轨和一条可视行。
- [x] 重叠手动 clip 不产生新行、不丢数据；当前 selection/focus 可操作，列表可选择每个 overlay。
- [x] transcript cue 和逐字 timing 在 API、Store、preview、timeline 与 compose 中完全一致且不重叠；下一 cue 和媒体音频不变。
- [x] 旧草稿无需迁移，selection、撤销/重做、拖动/缩放和 compose payload 保持兼容。
- [x] 桌面和 375px 浏览器无横向溢出、页面错误和控制台错误。

## Validation Results

- JavaScript syntax：4 个相关脚本通过 `node --check`。
- Python syntax：`compileall` 通过；项目未配置独立类型检查器。
- Focused backend：`42 passed`。
- Focused browser：`2 passed`；完整浏览器 `28 passed, 1 xfailed`。
- Full suite：`270 passed, 1 xfailed`。
- `git diff --check`：通过。
- 唯一 xfail 是既有服务重启恢复缺口，与本任务无关。

## Risky Files And Rollback Points

- `web/editor-preview-compositor.js`：画布层级和指针换算同时变化，应以独立 geometry helper 和浏览器矩形断言作为回滚边界。
- `web/editor-timeline-controller.js`：只改变 art 的派生布局，不改 Store transaction 或 Timeline schema。
- `server/app.py`：只规范 transcript overlay 可见时间，严禁进入媒体删除或音频处理路径。
- 浏览器测试使用隔离的竖屏临时媒体和本地资源，不读取 `data/jobs`、`data/history` 或调用外部模型。
