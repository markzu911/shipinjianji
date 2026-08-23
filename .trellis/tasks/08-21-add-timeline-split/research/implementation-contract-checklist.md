# 时间轴分割实施契约检查清单

本清单用于避免完整规范超过 Trellis 自动注入上限。它不替代规范原文；实施和检查阶段必须先从 `.trellis/spec/frontend/index.md`、`.trellis/spec/backend/index.md` 和 `.trellis/spec/testing/index.md` 定位并读取相关完整章节。

## 权威规格

- `.trellis/spec/guides/project-overview.md`：单页中文口播编辑器、原生前端与 source/edited 时间基本约束。
- `.trellis/spec/guides/cross-layer-thinking-guide.md`：Store/cut draft/preview/compose 权威关系、双时间与语义/物理范围检查项。
- `.trellis/spec/frontend/architecture-and-state.md`：单一 Store/media/timeline owner、cut history、save queue、revision 和性能契约。
- `.trellis/spec/frontend/ui-and-interactions.md`：时间轴二次确认、44px、键盘历史、点击/拖动语义和 375px。
- `.trellis/spec/frontend/api-and-media.md`：source/edited 映射、基础 video source key、`src/load()` 与生成前 flush。
- `.trellis/spec/backend/persistence-and-jobs.md`：cut-draft 原子写入、revision、schemaVersion 1 增量迁移和 PCM cache 边界。
- `.trellis/spec/backend/media-and-timeline.md`：timeline `original*`/物理边界、声学吸附、retained speech hard limit 与生成复用权威草稿。
- `.trellis/spec/testing/browser-workflows.md`：真实浏览器 identity、revision、响应式、计数和跨工具工作流。

## 本任务不可破坏的不变量

1. split point 持久化 source time；edited time 只用于当前帧显示。删除范围变化后重新投影，不能回写锚点。
2. 分割只改变结构：project revision `+1`，`timingRevision +0`，duration/currentTime/play state 不变，Art/PiP 不 reconcile。
3. split/delete/restore 各是一个历史事务；rAF 只合并渲染/effect，不能合并命令。selection 自身不创建历史。
4. `splitPoints`、`boundaryMode`、`splitClipKey` 是用户语义，进入 draft semantic signature；服务端物理 `start/end`、diagnostics、revision 和时间戳不进入。
5. `split_exact` 只接受相邻 split anchors 形成的完整 clip，服务端重复验证后跳过 acoustic/PCM 移动。缺字段的普通 timeline range 继续 `speech_safe`，原 fixture 输出不变。
6. split clip 删除仍写唯一 `timelineRanges` owner；preview、retained transcript、compose 与最终 FFmpeg 继续消费草稿中同一物理范围，不创建 UI 私有删除集合。
7. cut-draft `schemaVersion` 继续为 `1`；历史草稿、localStorage 和 history 缺少新字段时按空 split state / speech-safe 恢复。
8. 保存队列保持单 in-flight、latest-state-wins 和 acknowledged revision rebase；生成必须等待当前 split/delete 语义已由服务端确认。
9. 基础 video、document、Store、timeline、preview 和 tool roots identity 不变；纯 split 的 `srcWrites/loadCalls/extractorCreates` 都为 0，iframe 保持 0。
10. clip/marker pointer 必须阻止自由拖选 handler；普通拖选仍使用位移阈值、二次确认和现有语音安全提示。
11. deleted marker 不把删除时长加入 edited timeline；连续 marker 即使映射到同一拼接点也必须逐项可聚焦、恢复和撤销。
12. 所有变更静态资产更新 cache-buster；真实浏览器覆盖桌面、375px、键盘、刷新、连续 split 和三工具切换。

## 最小验证矩阵

| 场景 | 必须结果 |
| --- | --- |
| 播放头在有效 clip 内 split | 两个相邻 clip；时长、播放头、声音、画面不变 |
| 起点/终点/已有点/删除区/空媒体 split | disabled 或稳定拒绝；无 revision、history、PUT 意图 |
| split save + refresh | 同一 source anchor 与 clip boundary 恢复 |
| split undo/redo | 各一次 revision；`timingRevision` 不变；selection 按事务恢复 |
| 删除 split clip | exact range 等于相邻 anchors；服务端 final 不移动 |
| 恢复 deleted marker | 只移除目标 exact range；其他 split/deletion 不变 |
| 普通手动 timeline 删除 | 继续二次确认并走 speech-safe acoustic alignment |
| 保存期间再次 split/delete | 旧响应不覆盖新状态，随后发送 latest payload |
| 生成前仍有 split PUT | flush 至当前签名/revision 后再 compose |
| 工具切换和窄屏 | identity/iframe/媒体计数不变，44px 且无重叠 |
