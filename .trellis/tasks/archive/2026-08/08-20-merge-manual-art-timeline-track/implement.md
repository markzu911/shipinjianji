# 实施计划：手动艺术字单轨道

## Implementation Checklist

- [x] 在 `web/editor-art-model.js` 中将所有非 transcript overlays 派生为单一 `art:manual` 轨道，保持 transcript `trackId` 分组、clip ID、payload 和顺序。
- [x] 在 `web/editor-timeline-controller.js` 增加逻辑轨道内的确定性区间分 lane，让重叠 clip 使用不同可视 lane，并让 DOM 高度、逻辑 track index 和可视 lane index 各自保持正确语义。
- [x] 更新 `web/index.html` 中 ArtModel 和 TimelineController 的静态资源版本，同步静态契约测试。
- [x] 扩展 `tests/app/test_editor_art_model.py`，覆盖多手动、AI 普通 overlay、多 cue transcript、稳定轨道身份和 overlay 保真。
- [x] 扩展 `tests/app/test_editor_timeline_controller.py`，覆盖同轨不重叠复用 lane、重叠分 lane、后续轨道偏移、高度和选择/拖动语义。
- [x] 更新 `tests/app/test_editor_project_store.py` 中依赖旧手动轨道 ID 的派生/恢复断言，保留通用 Timeline 旧 schema 兼容测试。
- [x] 扩展 `tests/app/browser/test_editor_workflows.py`：连续新增两个时间重叠手动艺术字，断言单手动逻辑轨道、分 lane 可见按钮、单 clip 选择/调时、删除后剩余 clip、文案轨道分离以及 preview/compose 不变。
- [x] 更新前端架构、UI 与测试规范，记录手动/文案轨道派生和重叠 lane 契约。
- [x] 修复公共效果片段主体点击始终跳到片段起点的问题，按完整时间轴坐标定位并保持滚动、回退、拒绝选择、手柄和拖动语义。
- [x] 扩展 TimelineController 与真实浏览器测试，覆盖单次 seek、手动/文案/PiP、横向滚动坐标、无效几何/时长回退、选择拒绝、程序化选择和拖动/缩放。

## Validation Commands

```powershell
node --check web/editor-art-model.js
node --check web/editor-timeline-controller.js
./.venv/Scripts/python.exe -m pytest -q tests/app/test_editor_art_model.py tests/app/test_editor_timeline_controller.py tests/app/test_editor_project_store.py tests/app/test_frontend_contracts.py
./.venv/Scripts/python.exe -m pytest -q tests/app/browser/test_editor_workflows.py -k "art and (manual or track or timeline)"
./.venv/Scripts/python.exe -m pytest -q tests/app/browser
./.venv/Scripts/python.exe -m pytest -q
```

## Validation Results

- `node --check web/editor-art-model.js`：通过。
- `node --check web/editor-timeline-controller.js`：通过。
- 模型、Controller、Store 与静态契约：`53 passed`。
- 艺术字相关浏览器筛选：`4 passed`。
- 完整浏览器工作流：`27 passed, 1 xfailed`。
- 全量测试：`266 passed, 1 xfailed`。
- `git diff --check`：通过，仅显示仓库行尾转换提示。

## Review Gates

- [x] Timeline document 中手动轨道数恒为 `0` 或 `1`，transcript 轨道始终单独分组。
- [x] 合并前后 overlays、preview DTO 和 compose DTO 逐字段相等，只允许 timeline 轨道分组改变。
- [x] 重叠手动 clip 的按钮不遮挡，所有 clip 可 Tab 聚焦且指向正确 source ID。
- [x] 单 clip 拖动、撤销/重做、草稿恢复和文字剪辑重对齐不产生第二个 Store 或额外 revision。
- [x] 公共效果片段主体点击在 selection 接受后只 seek 一次，滚动后仍按实际点击位置对齐；无效几何/时长、拒绝选择、resize、拖动和程序化选择均保持定义的回退语义。
- [x] 桌面和 375px 浏览器无横向溢出，无 page/console/network 错误。

## Risky Files And Rollback Points

- `web/editor-art-model.js`：轨道分组是 Art/Store/Timeline 共享契约，保持 clip ID 和 overlay payload 是主要回滚点。
- `web/editor-timeline-controller.js`：lane 只能影响 DOM 布局，不得进入提交或历史数据。
- `tests/app/browser/test_editor_workflows.py`：使用已隔离的本地 job 和网络 fixture，不读取用户数据或外部模型。
- 不修改服务端 schema 和草稿版本；出现回归时可直接回滚前端派生/布局与对应测试。
