# 修复文案艺术字每段首字缺失

## Goal

修复用户修改文案、点击“拆分”并删除拆出段落后，已有“视频文案艺术字”轨道丢失保留段落首字的问题。艺术字的完整字符序列必须始终与当前剪后保留文案一致，声学/物理时间锚点只能改变字符出现时间，不能决定字符是否存在。

## Background

- 用户提供的截图显示，剪后文案包含“人生是”“但后来我才发现”“你能看到的选项”“该有的想法”“其实早就被你身边……”和“人这辈子……”，对应艺术字却变成“是”“后来我才发现”“能看到的选项”“有的想法”“早就被你身边……”和“这辈子……”。
- 用户确认触发顺序是：修改一次文案 -> 点击文案“拆分” -> 删除拆出的文案。
- 真实本地快照中，服务端声学校准锚点与拆分后的前端临时语义锚点存在合法偏移。例如“但后来我才发现”分别从 `14.13s` 与 `13.90s` 开始；当前按旧 cue source 区间筛选新字符中点，会错误排除首字“但”。“你”“该”“人”等可由同一机制稳定复现。
- 后端 `retainedTranscript` 和初次全文艺术字生成均通过全文字符守恒校验；缺字发生在已有艺术字轨道随 cut timing 变化进行前端重映射时，不是 ASR、VAD、删除范围或后端初次分段丢字。

## Requirements

1. 当前 `cut.transcript` 的可见字符序列是艺术字字符身份的唯一权威；`sourceStart/sourceEnd` 和 edited timing 只负责确定 cue 边界与逐字时间。
2. 同一全文艺术字轨道必须整体、单调地重映射字符，确保每个当前保留字符恰好进入一个 active cue；不得由各 cue 独立的 source midpoint 包含判断产生空洞、重复或错序。
3. 文案修改同步艺术字文本时，必须同步维护用于撤销/后续 cut reconciliation 的隐藏基线；不能让可见 cue 与 `_cutReconciliation` 基线使用不同版本的文字。
4. 保持已有 cue 的 track identity、样式、选择和可复用 ID；没有分配到保留字符的 cue 可以进入 suppressed 状态，恢复删除时仍能按同一轨道顺序恢复。
5. 手动艺术字、文案删除范围、VAD/PCM 边界、基础视频、画中画和后端稳定 cue 时间更新规则不得被此次修复改变。
6. 本地临时投影与服务端声学校准投影可以具有不同物理锚点；两种方向的锚点漂移都必须保持相同语义字符，不能要求二者时间完全相等。
7. 公共时间轴、统一预览和 compose 必须从同一个修复后的 Store snapshot 消费艺术字，不能各自保留不同文本。
8. 文案修改使既有艺术字成片失效时，后端必须把艺术字子任务写成可持久化、非运行且可重试的合法状态；不得写入 `status: null` 使下一次拆分/删除保存返回 500。
9. 文字保存后的源 transcript 分段与字符 timing 必须立即替换前端选择模型并使字符缓存失效；后续拆分/删除不得继续按修改前文字的字符位置扩大范围。

## Acceptance Criteria

- [ ] 以真实故障时间对构造回归：canonical cue 从 `14.13s/15.81s/17.39s/22.19s` 开始，而临时 transcript 从 `13.90s/15.55s/17.19s/21.90s` 开始时，艺术字仍完整包含“但/你/该/人”，且顺序不变。
- [ ] 自动化执行“修改文案 -> 文案拆分 -> 删除拆出段落”后，忽略标点与空白的 `art transcript cue text` 拼接值严格等于当前 `cut.transcript` 拼接值；删除段文字不存在，所有保留段首字存在。
- [ ] 每个当前保留字符只出现一次；跨 cue 边界不重复、不丢失、不倒序，`characterTimings` 数量与对应 cue 可见字符数量一致并保持有限、正时长、单调。
- [ ] 删除整 cue 时该 cue 被 suppressed；撤销/恢复后全文字符和 cue 顺序恢复，不受之前临时/服务端锚点切换影响。
- [ ] 时间轴艺术字轨道、统一预览和 compose 的 cue 文本完全一致；手动艺术字内容、ID、时间和选择不变。
- [ ] 已生成全文艺术字后连续执行“修改文案 -> 拆分 -> 删除”时，每次 `editable-segments` 保存均成功；中间工程快照可通过 repository shape/source 校验并可继续覆盖。
- [ ] 保存长度或内容发生变化的文案后立即拆分并删除中间拆出段，只删除该段对应范围，左右保留文字均存在且 source/edited 展示边界保持单调。
- [ ] 既有 ArtModel、ProjectStore、全文艺术字 API/轨道、cut draft、浏览器工作流和完整应用测试通过，`git diff --check` 通过。

## Out Of Scope

- 不调整 ASR、VAD、PCM、forced alignment 或任何物理删除边界。
- 不改变全文艺术字的 AI/本地语义分段策略、字体宽度限制或视觉样式。
- 不重新生成或改写用户媒体、历史项目和现有 `cut-draft.json`。
- 不把本次修复扩展为艺术字编辑器架构重写或新增服务端项目 revision。

## Technical Notes

- 主要故障点位于 `web/editor-art-model.js` 的 `reconcileTranscriptOverlay()`：它以旧 cue source range 独立过滤 `nextCut.transcript` 字符中点。
- `web/editor-project-store.js` 的 `mergeArtText()` 目前只更新可见 `overlay.text`，需要同时审计隐藏 reconciliation base；`cutTimingSignature()` 刻意忽略 transcript-only 变化，不能依赖后续服务端响应自动修复已损坏 cue。
- 修复应保留 `server/app.py:update_transcript_track_text_for_segment()` 的“文字更新但 cue 时间不漂移”契约。
