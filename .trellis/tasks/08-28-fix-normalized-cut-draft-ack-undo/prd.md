# 修复规范化剪辑草稿确认与撤销状态分叉

## Goal

服务端对用户时间轴删除范围执行毫秒量化和 VAD/声学安全边界规范化后，前端必须正确确认已经持久化的 revision、采用服务端物理边界，并让撤销、重做和刷新恢复始终与服务端权威草稿一致。用户不能再看到“撤销成功/已保存”，刷新后删除却重新出现，或随后重做进入 409 冲突。

## Background

- 浏览器审计已在两个独立测试 job 稳定复现：单帧语义范围 `3.153-3.191s` 被服务端保存为更宽的语音安全物理范围后，前端没有推进 `cutDraftRevision`；撤销只改变本地界面，服务端仍保留删除，刷新后删除恢复，重做报 409。
- `PUT /cut-draft` 在返回 200 前已经完成 `cut-draft.json` 持久化并把 revision 加一。前端收到 200 后若仍保留旧 revision，后续任何补偿保存都会与权威状态冲突。
- 用户语义范围 `originalStart/originalEnd` 与服务端物理删音范围 `start/end` 是两层数据；合法的物理边界变化不能被判为语义篡改，真实语义不一致也不能被静默接受。
- job/API 是权威状态；localStorage 和当前 DOM 只能作为恢复与展示副本，不能冒充服务端保存成功。

## Requirements

- R1：成功响应必须用结构命令身份验证替代所有时间数值全等：text/no-speech/timeline/split 集合的 key、数量、唯一性、文字身份、`automaticNoSpeechInitialized`、`boundaryMode` 和 `splitClipKey` 必须一致；服务端对文字语义边界、静音范围、时间轴语义/物理边界和 split time 的合法规范化应作为权威结果接收。
- R2：对当前 job 的成功 PUT 响应，前端必须先验证 revision 合法且已推进，并记录服务端已经提交的新 revision；不能因为后续语义或对齐校验失败而继续使用旧 revision。
- R3：当响应与请求结构身份兼容且该请求仍是当前期望状态时，前端必须先完整构造并原子采用服务端规范化后的 text/no-speech/timeline/split 状态，再用安装后的 payload 重建 desired signature、acknowledged snapshot、本地草稿、retained projection、EditorSuite 投影和当前撤销历史快照，然后才能显示“剪辑草稿已保存”。
- R4：请求在途期间若发生更新，旧响应只能推进权威 revision/确认旧请求，不能覆盖较新的本地期望状态；最新状态必须用新 revision 继续保存。
- R5：响应出现缺失/重复/额外 key、文字身份变化、`split_exact` 所有权变化或其他结构不一致时不得显示保存成功或把异常响应应用到当前 UI；但由于服务端已经返回 200 并持久化，下一次不同的补偿操作必须能基于响应 revision 继续保存，不能永久陷入 409。
- R6：规范化删除后的撤销必须向服务端保存空范围，重做必须重新保存删除范围；刷新后的 UI、API 草稿和持久化结果必须一致。
- R7：保留现有文字删除、自动静音、`split_exact`、保存防抖、单 in-flight、latest-state-wins、本地恢复和失败后重试行为。
- R8：不得调用真实外部模型或修改用户媒体/job；回归测试使用隔离 fixture 和可控的规范化响应。

## Acceptance Criteria

- [x] AC1：服务端把单帧时间轴请求的物理范围扩大、语义时间量化到毫秒，或把文字/静音/split 时间规范到权威边界后，前端接受结构兼容响应、完整采用规范化状态、推进到响应 revision，并显示真实的保存成功状态。
- [x] AC2：上述状态立即撤销后，下一次 PUT 使用最新 revision，服务端 `timelineRanges` 为空；刷新后页面仍没有该删除范围。
- [x] AC3：撤销后重做不会出现 409，服务端重新保存一个规范化删除范围；再次刷新后页面与服务端一致。
- [x] AC4：规范化响应到达前产生的新编辑不会被旧物理范围覆盖，保存队列最终提交最新语义状态且 revision 单调推进。
- [x] AC5：服务端返回缺失/重复/额外 key、不同文字身份、不同 split ownership 或其他结构不一致时，前端不显示“已保存”、不静默应用异常数据；随后撤销或其他不同操作仍使用已提交的最新 revision，而不是旧 revision。
- [x] AC6：现有剪辑草稿定向测试、浏览器编辑器工作流和完整测试全部通过，`git diff --check` 通过。

## Out Of Scope

- 不修改 VAD、强制对齐、PCM 谷底检测或服务端物理边界算法。
- 不在本任务建立 transcript/cut 联合 revision 契约，也不处理多标签页 local/server `updatedAt` 选择策略。
- 不给 `DELETE /cut-draft` 增加 revision 前置条件。
- 不拆分 `server/app.py`、`web/app.js` 或重写前端框架。
- 不改变用户看到的删除语义、撤销快捷键或现有剪辑工作流。
