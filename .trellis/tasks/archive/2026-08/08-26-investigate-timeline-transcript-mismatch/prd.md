# 修复时间轴文案与实际保留文案不一致

## Goal

修复文字列表、公共时间轴、live Store transcript 和后端剪后 transcript 的丢字问题。保留文字必须只由用户的语义删除选择决定，再使用权威声学时间投影到物理剪后时间，且不回退已验证的首字残音修复。

## Background

- 现场 job `99c068e5-7442-482f-84d0-5b36ab8a39e5` 的列表正确保留“所有人 / 一起给你画...”，但时间轴和后端 transcript 错误变成“所有人给你画...”。
- 下一处保留句应以“你身边人人都觉得...”开头，当前时间轴和后端 transcript 丢失首字“你”。
- 第一处语义/物理删除为 `28.454-29.171s` / `28.299-29.807s`；应保留“一起”的粗 ASR 时间为 `29.171-29.649s`，强制对齐起音约 `29.810s`。
- 第二处语义/物理删除为 `33.160-37.120s` / `32.730-37.790s`；应保留“你”的粗 ASR 时间为 `37.120-37.480s`，强制对齐起音约 `39.850s`。
- `web/app.js:2157` 在语义判定外又要求粗 token 与物理 keep span 相交；`server/app.py:5688` 在物理映射时长坍缩时直接丢弃语义保留单元。
- 完整证据见 `research/semantic-physical-projection.md`。首字残音修复 `f033bd7` 不是根因。

## Requirements

- R1：字符是否保留只使用语义 `originalStart/originalEnd` 和手动时间轴语义选择；物理 `start/end`、粗 ASR 时间和 quiet range 不得二次删字。
- R2：语义保留字符优先使用校验通过的强制字级时间，再映射到物理剪后时间；对齐不可用时保守降级，但仍不得丢字。
- R3：后端 `build_retained_transcript()`、`/cuts`、`/compose`、project-state/edit 恢复和 history 链路复用同一投影实现；输出时间 finite、严格正时长、单调且不越出剪后时长。
- R4：cut-draft GET/PUT 返回与当前 revision 对应的派生 retained transcript。它不接受浏览器写入，不进入 `cut-draft.json`，不形成第二持久化权威。
- R5：浏览器仅在 job id、cut-draft signature 和 revision 全部匹配时接受服务端投影；过期响应不得覆盖新编辑。等待响应的本地投影也不得闪现丢字。
- R6：时间轴文案、`buildLiveCutDraftState()`、EditorProjectStore frame 和 compose DTO 消费同一份当前 retained projection，不在 DOM、Store 或 TimelineController 中再删字。
- R7：修复不改变物理删除范围、声学 transition resolver、FFmpeg 裁切和已验证首字残音边界。
- R8：旧 job、旧 cut draft、缺少 acoustic sidecar 和旧客户端请求继续兼容；不主动改写用户数据。

## Acceptance Criteria

- [x] AC1（R1-R2、R5-R6）：现场同构用例中，文字列表、时间轴和 live Store transcript 都保留“所有人一起给你画...”，下一句以“你身边人人都觉得...”开头。
- [x] AC2（R1-R3）：粗 ASR 时间完全落在物理 cut 内时，`build_retained_transcript()` 仍输出完整文字；强制对齐可用时使用真实起音，时间严格正值且单调。
- [x] AC3（R3-R4、R8）：cut-draft GET/PUT 返回当前 revision 的派生 transcript；它不进入 CutDraftRequest 或 `cut-draft.json`，刷新后可从权威草稿重建。
- [x] AC4（R3、R6）：`/cuts`、`/compose`、预览、edit transcript 和 history 恢复的文字一致。
- [x] AC5（R5-R6）：过期草稿响应不改变当前时间轴/Store；服务端响应前的本地投影也保留语义字符。
- [x] AC6（R7）：现场物理范围仍为约 `28.299-29.807s` 和 `32.730-37.790s`；既有“一起给”残音、“得/你”和重复边界声学测试继续通过。
- [x] AC7（R2、R8）：缺少/无效强制对齐时不调用新模型、不丢字；旧草稿和旧 API 请求继续可用。
- [x] AC8（R1-R8）：后端单元/API、前端 Node、Store/TimelineController、浏览器工作流和定向声学回归通过，随后通过相关全量测试、`compileall` 和 `git diff --check`。

## Out Of Scope

- 不更换 ASR/FunASR 模型，不新增模型请求或在生成阶段重做声学对齐。
- 不修改 AI 重复文案检测、文字选择 UX、时间轴布局或视频编码参数。
- 不用固定毫秒补偿、人工拼字、DOM 专用补丁或收回正确物理边界掩盖问题。
- 不主动迁移或改写历史 job/cut draft；真实媒体只读验证。

## Key Decisions And Risks

- 这是一套跨层投影契约，不拆成可独立上线的前端/后端子任务，避免产生新的双权威。
- 强制对齐只决定已保留字符的时间，不决定字符身份。
- 无强制对齐的降级时间精度较低，但优先保证文字不丢失、时间单调且不越界。
