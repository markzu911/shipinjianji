# Journal - 541 (Part 1)

> AI development session journal
> Started: 2026-08-12

---


## Session 1: 合并 auto-subtitle 到 master

**Date**: 2026-08-17
**Task**: 合并 auto-subtitle 到 master
**Branch**: `master`

### Summary

审计并提交当前分支完整项目代码，修复文字语义范围与物理剪切范围混用问题，合并到 master，并通过 139 项完整回归与 JavaScript 语法检查。

### Git Commits

| Hash | Message |
|------|---------|
| `90fb1ff` | (see git log) |
| `5ddbd89` | (see git log) |

### Status

[OK] **Completed**


## Session 2: 文案剪辑边界与段落播放修复

**Date**: 2026-08-18
**Task**: 文案剪辑边界与段落播放修复
**Branch**: `develop`

### Summary

完成字符级语义删除、共享声学边界、保留下一字符保护、连续删除文案合并显示、当前段落播放与滚动跟随；全量 168 tests passed，并发布到 origin/master。

### Git Commits

| Hash | Message |
|------|---------|
| `7337413` | (see git log) |

### Status

[OK] **Completed**


## Session 3: 拆分应用测试边界

**Date**: 2026-08-18
**Task**: 拆分应用测试边界
**Branch**: `develop`

### Summary

将单体应用测试按功能拆分为 tests/app 下 13 个模块，保留 fixture 隔离和全部断言，完整回归 176 passed。

### Git Commits

| Hash | Message |
|------|---------|
| `10dea5b` | (see git log) |

### Status

[OK] **Completed**


## Session 4: 拆分后端请求模型

**Date**: 2026-08-18
**Task**: 拆分后端请求模型
**Branch**: `develop`

### Summary

将 server/app.py 中 29 个 Pydantic 模型迁移到 server/schemas.py，保留旧导入路径和 OpenAPI 全量兼容，完整回归 177 passed。

### Git Commits

| Hash | Message |
|------|---------|
| `c0a890e` | (see git log) |

### Status

[OK] **Completed**


## Session 5: 拆分并修复文案播放跟随动画

**Date**: 2026-08-18
**Task**: 拆分并修复文案播放跟随动画
**Branch**: `develop`

### Summary

将文字播放跟随滚动从 app.js 拆为独立控制器，使用可取消 RAF 同步滚动与活动行运动，补齐隐藏目标重试、尾部、用户中断和 reduced-motion 回归，并完成桌面与 375px 浏览器验收。

### Git Commits

| Hash | Message |
|------|---------|
| `f1f943c` | (see git log) |

### Status

[OK] **Completed**


## Session 6: 拆分历史版本仓库

**Date**: 2026-08-18
**Task**: 拆分历史版本仓库
**Branch**: `develop`

### Summary

将历史版本持久化从 server.app 提取为独立 HistoryRepository，保留 14 个动态配置兼容入口；新增聚焦测试并通过 178 项完整回归与 OpenAPI 基线检查。

### Git Commits

| Hash | Message |
|------|---------|
| `ca0dded` | (see git log) |

### Status

[OK] **Completed**


## Session 7: 优化文案播放跟随动画

**Date**: 2026-08-18
**Task**: 优化文案播放跟随动画
**Branch**: `develop`

### Summary

将文案跟随改为单次滚动提交与 FLIP/WAAPI，拆分视频帧热路径并加入可取消帧时钟；修复连续尾段上弹与重叠游标问题，完成桌面及 375px 浏览器验证。

### Git Commits

| Hash | Message |
|------|---------|
| `22c0e56` | (see git log) |

### Status

[OK] **Completed**


## Session 8: 建立单页编辑器迁移方案与浏览器行为基线

**Date**: 2026-08-18
**Task**: 建立单页编辑器迁移方案与浏览器行为基线
**Branch**: `develop`

### Summary

完成单页编辑器目标架构与分阶段迁移规划；新增隔离的真实 Chromium 工作流，覆盖草稿刷新、三工具切换、compose 载荷和服务重启预期失败；完整回归 185 passed, 1 xfailed。

### Git Commits

| Hash | Message |
|------|---------|
| `2790864` | (see git log) |
| `fb1447d` | (see git log) |

### Status

[OK] **Completed**


## Session 9: 完成单页编辑器状态核心 B0

**Date**: 2026-08-18
**Task**: 完成单页编辑器状态核心 B0
**Branch**: `develop`

### Summary

建立唯一 EditorProjectStore、revision guard、无刷新文字同步及 iframe 兼容桥，并通过完整浏览器和应用回归。

### Git Commits

| Hash | Message |
|------|---------|
| `fa36fa0` | (see git log) |
| `671a712` | (see git log) |
| `4a83df8` | (see git log) |

### Status

[OK] **Completed**


## Session 10: 完成 B1 单页统一媒体预览与时间轴

**Date**: 2026-08-18
**Task**: 完成 B1 单页统一媒体预览与时间轴
**Branch**: `develop`

### Summary

完成唯一 MediaController、语义 PreviewCompositor 与统一 TimelineController，确保预览、时间轴和 compose 消费同一原子 frame/revision；补齐媒体保持、事务回滚、iframe 回声和浏览器回归契约。完整 tests/app 209 passed、1 xfailed。

### Git Commits

| Hash | Message |
|------|---------|
| `97a1397` | (see git log) |
| `cf42ae2` | (see git log) |
| `bf0054a` | (see git log) |

### Status

[OK] **Completed**


## Session 11: 完成单页编辑器艺术字面板 B2

**Date**: 2026-08-19
**Task**: 完成单页编辑器艺术字面板 B2
**Branch**: `develop`

### Summary

将艺术字 inspector 迁入顶层 ArtTool，共享 Store、媒体、预览、时间轴与 compose；补齐版本化草稿恢复、请求取消和 legacy fallback，并通过 221 项应用测试与 14 项浏览器工作流。

### Git Commits

| Hash | Message |
|------|---------|
| `3b39872` | (see git log) |
| `63683a8` | (see git log) |
| `46dddd0` | (see git log) |

### Status

[OK] **Completed**


## Session 12: 完成单页编辑器画中画面板迁移

**Date**: 2026-08-19
**Task**: 完成单页编辑器画中画面板迁移
**Branch**: `develop`

### Summary

完成 B3 顶层 PipTool、共享项目状态与草稿 v2、画中画无最大缩放和中心裁切一致性；保留 B3 fallback/standalone，新增完整前端、后端和浏览器回归。

### Git Commits

| Hash | Message |
|------|---------|
| `700495e` | (see git log) |
| `3655684` | (see git log) |
| `93d6fba` | (see git log) |

### Status

[OK] **Completed**


## Session 13: 完成单页编辑器旧运行时清理

**Date**: 2026-08-19
**Task**: 完成单页编辑器旧运行时清理
**Branch**: `develop`

### Summary

完成 B4：统一文字剪辑、艺术字和画中画为唯一顶层运行时，删除 iframe/message bridge 与四个旧页面资源；保留历史 URL 307 重定向和模板库深链兼容，补齐桌面/375px、媒体 identity、文字同步、模板交接与 compose 回归。最终 tests/app 238 passed, 1 xfailed，browser 24 passed, 1 xfailed，唯一 xfail 为 Phase A 服务重启恢复。

### Git Commits

| Hash | Message |
|------|---------|
| `14ee2f0` | (see git log) |
| `365640a` | (see git log) |
| `0d68bdc` | (see git log) |

### Status

[OK] **Completed**


## Session 14: 修复转写后预览加载

**Date**: 2026-08-19
**Task**: 修复转写后预览加载
**Branch**: `develop`

### Summary

修复转写任务完成后原视频不自动加载的问题，补充同页状态迁移、失败重试和健康媒体去重回归。

### Git Commits

| Hash | Message |
|------|---------|
| `5d20067` | (see git log) |

### Status

[OK] **Completed**


## Session 15: 修复实时艺术字同步与面板回归

**Date**: 2026-08-19
**Task**: 修复实时艺术字同步与面板回归
**Branch**: `develop`

### Summary

恢复艺术字最终版双页签与一键视频文案入口；在 CUT_TIMING_CHANGED 中原子同步全文及锚点艺术字，支持删除、隐藏、撤销和陈旧草稿恢复；补齐双时间坐标、AI 取帧和完整回归规范。

### Git Commits

| Hash | Message |
|------|---------|
| `5e1a593` | (see git log) |
| `4c27fca` | (see git log) |

### Status

[OK] **Completed**


## Session 16: 合并文案艺术字轨道设置

**Date**: 2026-08-19
**Task**: 合并文案艺术字轨道设置
**Branch**: `develop`

### Summary

将同一文案艺术字轨道在 ArtTool 中合并为一个入口并统一修改共享样式，保留分段 cue 时间与渲染；补齐删除空状态、字段保真、静态与真实浏览器回归及 Trellis 契约。

### Git Commits

| Hash | Message |
|------|---------|
| `67a06e5` | (see git log) |
| `a46d68c` | (see git log) |

### Status

[OK] **Completed**


## Session 17: 修复文案删除声学边界

**Date**: 2026-08-20
**Task**: 修复文案删除声学边界
**Branch**: `develop`

### Summary

用增益稳定的相对能量与持续谷底约束统一文字删除边界，完整去除被删文案尾音，并保护相邻保留语音；补齐跨增益、双向端点、token 扩展和跨入口一致性测试。

### Git Commits

| Hash | Message |
|------|---------|
| `7807717` | (see git log) |
| `373042c` | (see git log) |

### Status

[OK] **Completed**


## Session 18: 合并艺术字轨道并修复点击定位

**Date**: 2026-08-20
**Task**: 合并艺术字轨道并修复点击定位
**Branch**: `develop`

### Summary

将非文案艺术字合并到独立手动轨道，以可视 lane 展示重叠片段；修复公共效果片段点击时播放头固定跳到片段起点的问题，并补齐滚动、拒绝选择、几何回退、拖拽及真实浏览器回归。

### Git Commits

| Hash | Message |
|------|---------|
| `38a302a` | (see git log) |
| `76e2773` | (see git log) |

### Status

[OK] **Completed**


## Session 19: 修复艺术字预览与轨道布局

**Date**: 2026-08-20
**Task**: 修复艺术字预览与轨道布局
**Branch**: `develop`

### Summary

统一艺术字与画中画的源视频预览画布，固定手动和文案艺术字各占独立单行，并严格消除文案 cue 时间重叠；新增竖屏浏览器、时间边界和轨道回归。

### Git Commits

| Hash | Message |
|------|---------|
| `97eddff` | (see git log) |
| `ea5e72a` | (see git log) |

### Status

[OK] **Completed**


## Session 20: 消除裁剪尾音并保护下一段语音

**Date**: 2026-08-20
**Task**: 消除裁剪尾音并保护下一段语音
**Branch**: `develop`

### Summary

接入完整句段 FunASR 强制对齐与缓存，统一文案/时间轴双范围和草稿 revision 权威生成；完成跨层回归、Chromium、真实媒体 ASR/PCM gate，并固化防复发规范。

### Git Commits

| Hash | Message |
|------|---------|
| `7305368` | (see git log) |
| `37b383a` | (see git log) |
| `ab81735` | (see git log) |

### Status

[OK] **Completed**


## Session 21: 修复重复文案裁剪尾音与时间显示

**Date**: 2026-08-21
**Task**: 修复重复文案裁剪尾音与时间显示
**Branch**: `develop`

### Summary

通过保留侧持续起音门控精确收紧重复文案删除边界，避免尾音残留且不误删下一段开头；统一删除后文案与时间轴的剪后时间展示，并补齐回归测试与跨层契约。

### Git Commits

| Hash | Message |
|------|---------|
| `b923a81` | (see git log) |
| `30225d0` | (see git log) |

### Status

[OK] **Completed**


## Session 22: 拆分艺术字选择页面并准备生产发布

**Date**: 2026-08-21
**Task**: 拆分艺术字选择页面并准备生产发布
**Branch**: `develop`

### Summary

完成艺术字选择、设置与 AI 推荐三页签拆分，将模板改为可访问的下拉列表，补齐桌面/移动端与浏览器回归并更新资源缓存版本；同步固化交互规范，保留剪辑性能优化任务为 planning。

### Git Commits

| Hash | Message |
|------|---------|
| `2fa6995` | (see git log) |
| `770452a` | (see git log) |
| `6aa692e` | (see git log) |

### Status

[OK] **Completed**


## Session 23: 优化剪辑交互卡顿

**Date**: 2026-08-21
**Task**: 优化剪辑交互卡顿
**Branch**: `develop`

### Summary

完成剪辑高频交互按帧提交、source-time 缩略图复用、300ms latest-state 草稿队列、idle 历史持久化和指纹 PCM LRU；补齐并发、revision、声学等价与全量浏览器回归，P95 从 1960.5ms 降至 61.7ms。

### Git Commits

| Hash | Message |
|------|---------|
| `9021a18` | (see git log) |
| `5160e4c` | (see git log) |
| `a104a5f` | (see git log) |

### Status

[OK] **Completed**


## Session 24: 实现时间轴分割与精确片段删除

**Date**: 2026-08-23
**Task**: 实现时间轴分割与精确片段删除
**Branch**: `develop`

### Summary

新增播放头分割、分割片段独立删除/恢复/撤销重做与持久化；后端引入经锚点验证的 split_exact 精确边界，保留普通选区声学对齐；补齐响应式、键盘交互、Store 投影、浏览器回归和 Trellis 契约。

### Git Commits

| Hash | Message |
|------|---------|
| `184b080` | (see git log) |
| `ee90b83` | (see git log) |
| `74e166c` | (see git log) |

### Status

[OK] **Completed**


## Session 25: 任务重启恢复与失败重试

**Date**: 2026-08-24
**Task**: 任务重启恢复与失败重试
**Branch**: `develop`

### Summary

新增版本化任务快照和启动恢复，将运行中任务恢复为可重试的 interrupted；加入 attempt 隔离、并发与清理竞态保护、同任务重试和前端中断交互，并完成 391 项全量回归与规范同步。

### Git Commits

| Hash | Message |
|------|---------|
| `9da6b7c` | (see git log) |
| `554d46c` | (see git log) |
| `3f611f9` | (see git log) |
| `218c4c6` | (see git log) |

### Status

[OK] **Completed**


## Session 26: 紧凑编辑布局与时间轴帧预览修复

**Date**: 2026-08-25
**Task**: 紧凑编辑布局与时间轴帧预览修复
**Branch**: `develop`

### Summary

移除时间轴恢复按钮，压缩文案与画中画 UI，并修复绝对定位缩略帧高度为零的问题。

### Main Changes

- 文字剪辑行和画中画设置按 50% 紧凑显示
- 时间轴帧缩略图纵向铺满并保留剪后时间映射

### Git Commits

| Hash | Message |
|------|---------|
| `cc24366` | (see git log) |
| `b9ef052` | (see git log) |
| `d6c3d99` | (see git log) |

### Testing

- [OK] 相关静态与浏览器检查 29 项通过
- [OK] 完整套件 391/392；剩余为无关的艺术字模板初始化 revision 时序断言

### Status

[OK] **Completed**


## Session 27: 消除删除文案首字残音

**Date**: 2026-08-26
**Task**: 消除删除文案首字残音
**Branch**: `develop`

### Summary

修正同段 delete-start 对 forced start 的直接信任，使用首个持续低能到起音跃升的 PCM 证据清除被删首字残音；补齐增益、失败形态、双走廊和真实媒体回归，并同步媒体时间轴规范。

### Git Commits

| Hash | Message |
|------|---------|
| `f033bd7` | (see git log) |
| `42e0ded` | (see git log) |
| `4cf9e72` | (see git log) |

### Status

[OK] **Completed**


## Session 28: 修复时间轴文案投影丢字

**Date**: 2026-08-26
**Task**: 修复时间轴文案投影丢字
**Branch**: `develop`

### Summary

统一语义保留字符到物理剪后时间的前后端投影；cut-draft 返回受 revision 守卫的派生 transcript；修复文字保存 timingRevision 与显式空范围兼容；45 个浏览器和 372 个非浏览器测试通过。

### Git Commits

| Hash | Message |
|------|---------|
| `dbe03a1` | (see git log) |

### Status

[OK] **Completed**


## Session 29: ASR VAD 联合声学边界与分段投影

**Date**: 2026-08-27
**Task**: ASR VAD 联合声学边界与分段投影
**Branch**: `master`

### Summary

引入 ASR、FSMN-VAD 与 PCM 联合剪切边界，统一 AI 删除和用户文案拆分的方向性物理切点；修复 retained transcript 忽略 editableSegmentId 导致时间轴文案合并成 ASR 大段的问题，并通过 457 项全量及 48 项浏览器回归。

### Git Commits

| Hash | Message |
|------|---------|
| `7f0aa1f` | (see git log) |
| `34dd8fd` | (see git log) |
| `ea592cf` | (see git log) |

### Status

[OK] **Completed**


## Session 30: 修复被删首字跨候选点残音

**Date**: 2026-08-27
**Task**: 修复被删首字跨候选点残音
**Branch**: `develop`

### Summary

通用修复同段 delete-start 需要候选点后 PCM block 才能确认起音时的首字残音；限定 lookahead、保持失败 trust 与 hard limit，覆盖文字、时间轴和用户文案拆分；真实源片返回 118.995s，完整测试 462 项通过。

### Git Commits

| Hash | Message |
|------|---------|
| `5a515ec` | (see git log) |
| `e4109cc` | (see git log) |
| `a61d3af` | (see git log) |

### Status

[OK] **Completed**


## Session 31: 修复文案艺术字首字缺失

**Date**: 2026-08-27
**Task**: 修复文案艺术字首字缺失
**Branch**: `master`

### Summary

将全文艺术字改为全轨字符守恒重映射，修复文字保存后的前端状态同步与艺术字快照状态，并补齐模型、Store、持久化和浏览器回归。

### Git Commits

| Hash | Message |
|------|---------|
| `251d2ef` | (see git log) |
| `a0fa3f0` | (see git log) |
| `0af1d07` | (see git log) |

### Status

[OK] **Completed**


## Session 32: 修复艺术字语义词拆分

**Date**: 2026-08-27
**Task**: 修复艺术字语义词拆分
**Branch**: `master`

### Summary

统一后端文字保存与前端全文艺术字重投影的语义边界契约，修复修改文案后拆分删除导致词内切分，并补齐全链路回归与规范。

### Git Commits

| Hash | Message |
|------|---------|
| `7328c92` | (see git log) |
| `dca50b4` | (see git log) |
| `bc4a38a` | (see git log) |

### Status

[OK] **Completed**


## Session 33: 修复时间轴文案空隙与刷新跳变

**Date**: 2026-08-28
**Task**: 修复时间轴文案空隙与刷新跳变
**Branch**: `master`

### Summary

为时间轴文案增加独立 layout 范围，短间隔按剪后时间覆盖、长静音保留；阻止零宽度提前渲染并稳定刷新首帧，补齐阈值、删除折叠和浏览器刷新回归。

### Git Commits

| Hash | Message |
|------|---------|
| `67742a0` | (see git log) |
| `b8a9545` | (see git log) |
| `950a0dc` | (see git log) |

### Status

[OK] **Completed**
