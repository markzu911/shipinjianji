# 技术设计：文案艺术字轨道级设置

## Architecture And Boundaries

本次改动限制在顶层单页编辑器的 ArtTool 展示层与回归测试。`EditorProjectStore`、`EditorArtModel`、公共 PreviewCompositor、TimelineController 和 compose DTO 保持现有所有权关系。

```text
EditorProjectStore art.overlays（多个 transcript cues + manual overlays）
  -> ArtTool 列表 view model
       transcript: 按 trackId 分组为一个入口
       manual: 每个 overlay 一个入口
  -> 现有 art:<cueId> selection
  -> EditorArtModel.updateOverlay/removeOverlay
  -> 同一个 editor frame
       preview: 分段 cues
       timeline: 一轨多 clips
       compose: 分段 cues
```

UI 中的“一个轨道”只表示列表和设置的操作单位；数据、播放和合成仍以 cue 为最小单位。

## List View Model

在 `web/editor-art-tool.js` 内增加局部、无状态的列表归并 helper：

- transcript overlay 使用 `trackId` 归组，按首次出现位置插入一个轨道 entry；entry 保存排序后的 cues、`start = min(cue.start)`、`end = max(cue.end)`。
- manual overlay 直接形成单项 entry，维持当前数组顺序。
- transcript entry 标题固定为“视频文案艺术字”，副文案为“{n} 段 · {start}s - {end}s”；manual entry 继续显示自身文字和时间。
- transcript entry 的选中态由 `selected.trackId === entry.trackId` 判断，不能只比较代表 cue ID；manual entry 继续按 overlay ID 判断。

当前生成逻辑会替换旧 transcript overlays，因此常规项目只有一个 transcript entry。若兼容数据中存在多个不同 `trackId`，分别展示，避免把无共同写入契约的历史轨道静默混合。

## Representative Cue Selection

Store 继续只保存 `art:<cueId>`，不新增 `art-track:<trackId>`：

1. 如果当前 selection 指向该 `trackId` 的有效 cue，复用该 cue。
2. 否则读取 `services.media.currentEditedTime()`，选择 `start <= time < end` 的 cue；重叠时按开始时间和结束时间的稳定排序取第一项。
3. 当前时间未命中时选择轨道最早 cue。

列表按钮可继续使用 `data-art-select=<representativeCueId>`，现有 click command、seek 和 Store selection 协议不变。代表 cue 只在用户点击轨道入口时解析；普通播放帧和 render 不主动 dispatch selection，因此不会引入播放热路径 revision 或选中态跳动。

## Control Modes

`renderControls(selected)` 根据 `EditorArtModel.isTranscriptOverlay(selected)` 切换两种模式：

| 控件 | 文案轨道 | 自定义艺术字 |
| --- | --- | --- |
| 模板、字体、字号、颜色、描边、阴影、间距、对齐、X/Y、位置预设 | 显示，更新整轨 | 显示，更新当前项 |
| 文字内容、start/end、贴合文案时间 | 隐藏 | 保持现状 |
| 文字方向、每行字数 | 隐藏；全文轨道由 model 固定为横排/自动分段 | 保持现状 |
| 应用到全部自定义艺术字 | 隐藏 | 保持现状和禁用条件 |
| 删除 | “删除视频文案艺术字” | “删除当前艺术字” |

用显式 `data-art-cue-only` / `data-art-manual-only` 容器或等价语义 marker 管理可见性，避免靠标签文字或 DOM 顺序判断。详细设置 heading、empty state、fieldset legend/辅助说明随模式更新，确保屏幕阅读器获得同样语义。

## Data And Mutation Contracts

- 共享设置仍调用 `commitSelectedPatch()` 一次，由 `EditorArtModel.updateOverlay()` 过滤 `TRANSCRIPT_STYLE_FIELDS` 并按 `trackId` 更新全部 cues。
- UI 不向 transcript selection 提交 `text/start/end`，模型现有过滤仍作为防御层。
- 删除仍调用 `EditorArtModel.removeOverlay()`；transcript selection 删除同 `trackId` 全部 cues。
- `replaceArt()` 仍只发出一个语义 command。等价 patch 由 Store/model 现有 no-op 语义处理，不创建额外 transaction。
- 不变字段：`id`、`text`、`start/end`、`sourceStart/sourceEnd`、`characterTimings`、`timingRevision`。

## Compatibility

- 不修改持久化 schema，旧草稿无需迁移。
- 手动艺术字和 AI 确认后的普通 overlay 保持单项 UI 和原有功能。
- 多 `trackId` 历史数据按轨道分别归组；空/非法 transcript 身份继续按 manual overlay 处理，沿用 model 归一化结果。
- 静态资源更新只提升 `editor-art-tool.js` 的 `?v=` 版本；只有发生 CSS 改动时才提升 `styles.css` 版本。

## Risks And Mitigations

- 选择漂移：render 阶段不提交选择，只有轨道入口 click 时解析代表 cue；同轨任何 cue 都产生同一轨道选中态。
- 样式误改时间：UI 隐藏 cue-only 控件，模型继续过滤共享字段，测试对所有时间/锚点/字符 timing 做完整前后快照。
- 自定义艺术字行为回归：列表 view model 明确区分 manual entry，并通过真实浏览器覆盖 manual 与 transcript 往返选择。
- UI 溢出：轨道摘要使用现有两行按钮结构，时间摘要允许正常换行/截断；在 1280x720 和 375px 实测。

## Rollback

改动不迁移数据。若需要回滚，只需恢复 ArtTool 的列表/控件渲染、对应测试和静态资源版本；Store 中的 overlays 仍为原有格式，不需要数据修复。
