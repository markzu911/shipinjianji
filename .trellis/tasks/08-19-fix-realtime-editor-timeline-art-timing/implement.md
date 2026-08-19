# 实施计划

## 1. 锁定回归

- 在 `tests/app/test_art_text_track.py` 增加 quiet range 与有效 word 重叠时不重排字符时间的用例，锁定“我也这么想”约 `3.21s`。
- 在前端 model/浏览器测试中增加段内短语、重复短语最近匹配、单文案轨、艺术字仅两个顶层 tab 且设置面板只有“一键添加视频文案”，以及面板滚动状态用例。
- 在 Store/model/浏览器测试中覆盖全文艺术字删除单字、删除整 cue、跨 cue 删除、撤销恢复、有锚点普通艺术字隐藏/恢复，以及无关联自定义艺术字保持不变。
- 在 AI 建议 API 测试中捕获实时 draft、原片取帧时间和剪后标签。

## 2. 修复艺术字时间与匹配

- 调整后端全文艺术字字符时间生成，可靠 word/character timing 不再经过 quiet-range 全段投影。
- 在 `EditorArtModel` 实现字符级短语匹配纯函数，ArtTool 复用该函数提交精确 range/source anchors。
- 验证手动 range 更新仍等比映射 character timings，预览和 compose 保持同一 frame。

## 3. 接通实时 AI 草稿

- 扩展 `ArtTextSuggestionRequest` 可选草稿字段及公开 schema 契约。
- 前端 AI 请求提交当前 draft transcript/duration。
- 后端校验草稿，分离 frame `mediaTime/displayTime`，建议继续返回剪后时间。
- 确认 AI overlay 时通过 MediaController 补齐 source anchors；旧请求保持兼容。

## 4. 修复时间轴和面板

- TimelineController 支持可见 kind，EditorSuite 的效果层仅渲染 art/pip。
- ArtTool 恢复“艺术字设置/AI 推荐”两个顶层 tab，设置面板只保留默认热血立体的“一键添加视频文案”入口，移除重复的文案编辑、保存、分段和选段添加 UI，并保持切换滚动归位和无 selection 空状态。
- PipTool 重绘后仅在列表容器内部保证 selection 可见。
- 更新前端静态资源版本和契约测试。

## 5. 恢复 cut-to-art 实时同步

- 在 `EditorArtModel` 增加基于当前剪后 transcript、字符 timing 和 source anchors 的纯 reconciliation；全文轨道删减/重建，普通关联 overlay 重映射或进入可逆 suppressed 集合，无关联自定义 overlay 保持不变。
- `EditorProjectStore` 的 `CUT_TIMING_CHANGED` 在一个 reducer 事务中同步 cut、art、selection 和 timeline；草稿 schema 向后兼容并保留撤销恢复所需数据。
- 确认 preview、公共效果时间轴与 composition DTO 只读取同步后的同一 Store frame，不在 ArtTool 或 selector 中重复修正。

## 6. 验证

```powershell
Get-ChildItem web -Filter *.js | ForEach-Object { node --check $_.FullName }
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_art_text_track.py tests/app/test_art_text_api.py tests/app/test_editor_art_model.py tests/app/test_editor_project_store.py tests/app/test_frontend_contracts.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser/test_editor_workflows.py
.\.venv\Scripts\python.exe -m pytest -q tests/app
git diff --check
py -3 .\.trellis\scripts\task.py list-context .trellis/tasks/08-19-fix-realtime-editor-timeline-art-timing
```

浏览器额外验证 1280x720 与 375px：三工具保持同 document/video、文案轨唯一、艺术字只有两个顶层 tab、设置面板只有“一键添加视频文案”、空状态不显示空表单、画中画 selection 可见且无横向溢出；添加全文艺术字后删除/撤销文案，预览、时间轴和 compose 同步删减/恢复。

## Rollback Points

- timing 与 AI 字段均保留旧数据兼容；若 AI frame sample 失败，可单独回退到无草稿的旧采样分支，不影响全文轨道修复。
- visible kinds 缺省渲染全部，移除 EditorSuite 配置即可恢复旧 controller 行为。
