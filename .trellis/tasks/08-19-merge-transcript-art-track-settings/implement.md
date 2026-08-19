# 实施计划：文案艺术字轨道级设置

## Implementation Checklist

- [x] 在 `web/editor-art-tool.js` 建立列表 entry view model：按 transcript `trackId` 归组、计算 cue 数和整轨范围，自定义艺术字保持逐项。
- [x] 实现代表 cue 解析和轨道级选中态，复用现有 `art:<cueId>` selection、seek 与 command，不在 render/播放帧中提交新状态。
- [x] 给单 cue/手动专属控件增加明确 DOM marker；在 `renderControls()` 中切换整轨标题、帮助文案、可见控件和删除按钮文案。
- [x] 保持 `commitSelectedPatch()`、`EditorArtModel.updateOverlay()`、`removeOverlay()` 和 Store transaction 为唯一写入路径；测试发现并修复 style-only 归一化改写 `characterTimings` 的模型缺口。
- [x] 复用现有两行列表样式完成桌面和 375px 验证，无需修改 `web/styles.css`。
- [x] 更新 `web/index.html` 中改动资源的 `?v=`，同步 `tests/app/test_frontend_contracts.py` 静态资源契约。
- [x] 扩展 `tests/app/test_editor_art_model.py`，锁定整轨共享样式更新、整轨删除、单轨多 clips 以及 cue ID/文字/时间/source anchors/characterTimings 不变。
- [x] 扩展 `tests/app/browser/test_editor_workflows.py`，覆盖列表归组、代表 cue、轨道/手动控件切换、统一样式、单 revision、删除整轨及 frame 预览/时间轴/compose 一致性。
- [x] 在桌面 1280x720 与移动 375px 验证无横向溢出、轨道按钮高度、选中态和 console/page/network 错误。

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_editor_art_model.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_frontend_contracts.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser/test_editor_workflows.py -k "art and (track or template or editor)"
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser
.\.venv\Scripts\python.exe -m pytest -q
```

## Review Gates

- [x] `git diff` 只包含本任务的 ArtTool、模型保真修复、资源版本、测试、规范和 Trellis 文件，不包含生产部署或无关重构。
- [x] transcript track 的 UI 条数减少，但 Store overlay 数、cue 文案和时间在样式操作后不变。
- [x] preview、timeline、compose 使用同一个 project/timing revision；没有第二个 Store、video、timeline 或私有 payload。
- [x] manual overlays 的添加、选择、文字/时间编辑、匹配、批量应用和删除回归通过。
- [x] 完整前端与浏览器规范的 Quality Check 已逐项核对。

## Risky Files And Rollback Points

- `web/editor-art-tool.js`：主要风险是选择语义和动态控件可见性；先保持现有 command 接口，再替换列表 view model。
- `tests/app/browser/test_editor_workflows.py`：复用隔离 job/网络 fixture，不访问真实模型或用户数据。
- `web/index.html` / `tests/app/test_frontend_contracts.py`：资源版本必须同一提交更新。
- 不改 Store schema 或服务端，出现回归时可以按文件恢复 UI 分组而无需迁移草稿。
