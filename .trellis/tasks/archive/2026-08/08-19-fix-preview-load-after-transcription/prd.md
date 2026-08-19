# 修复转写完成后视频预览不加载

## Goal

转写任务从处理中切换为完成后，当前页面无需刷新即可显示并播放原视频；同时保留统一编辑器只有一个视频元素和一个媒体控制器的架构约束。

## Background

- 上传成功后，`rememberJob()` 会触发 EditorSuite 刷新，随后 `renderJob()` 也会把 `queued` 任务写入项目 store。
- 项目 selector 只要存在 `jobId` 就生成 `/api/transcriptions/<job_id>/original-video`，因此媒体控制器会在任务完成前请求视频。
- 原视频接口在任务不是 `completed` 时按契约返回 `409`。
- 媒体控制器在调用 `video.load()` 前保存 `sourceKey`；任务完成后 URL 和 key 不变，后续 frame 被相同 key 的提前返回拦截，浏览器不会重试。
- 同一任务在完成后刷新页面可以正常加载和播放，已验证视频时长为 184 秒、`readyState=4`、无媒体错误，排除文件丢失、编码不兼容和后端完成态接口故障。

## Requirements

- R1：处理中任务不得把尚不可读取的原视频标记为已成功加载。
- R2：任务进入 `completed` 后，统一媒体控制器必须发起有效的视频加载；用户不需要刷新页面。
- R3：相同 source key 在媒体处于无可用源或错误状态时必须允许恢复性重试，避免一次瞬时失败永久锁死该任务。
- R4：正常已加载的相同 source key 仍不得重复调用 `load()`，避免工具切换、草稿保存或普通 store 更新重置播放位置。
- R5：保持后端原视频接口“仅 completed 可读”的现有契约，不放宽处理中媒体访问。
- R6：增加自动化回归，覆盖 `queued/transcribing -> completed` 的同页迁移以及已加载媒体不重复重载。

## Acceptance Criteria

- [x] 任务处于 `queued` 或 `transcribing` 时，预览可以保持未就绪状态，但不会形成阻止完成态加载的永久 source key。
- [x] 同一个页面收到该任务的 `completed` 状态后，视频元数据可用、时长大于 0，点击播放后 `currentTime` 前进。
- [x] 首次媒体请求失败或 video 处于 `NETWORK_NO_SOURCE`/错误状态时，再次应用相同 source key 会重新加载。
- [x] 视频已经正常加载时，再次应用相同 source key 不调用 `load()`，播放位置和播放/暂停状态保持不变。
- [x] 现有前端脚本语法检查、媒体控制器单元测试和相关真实浏览器工作流通过。

## Out of Scope

- 不修改视频编码、转写模型、DNS 或媒体文件生成逻辑。
- 不改变原视频接口的 HTTP 状态契约。
- 不新增第二个视频元素、播放器库或独立页面运行时。
- 不顺带重构 EditorProjectStore、公共时间轴或其他 B4 模块。

## Key Decisions

- 采用双重保护：selector/应用层仅在任务完成后提供媒体 URL，媒体控制器同时允许失败状态下的同 key 重试。
- 以 video 实际可用状态而不是“曾设置过 URL”判断是否可以跳过加载。
- 本缺陷范围明确且单一，按轻量任务执行，仅需要 `prd.md`。

## Validation

- 全部 17 个 `web/*.js` 通过 `node --check`。
- 聚焦前端测试：38 passed。
- 完整浏览器测试：25 passed，1 个既有预期 xfail。
- 完整测试：242 passed，1 个既有预期 xfail，1 个既有弃用警告。
- `git diff --check` 与 Trellis context validation 通过。
