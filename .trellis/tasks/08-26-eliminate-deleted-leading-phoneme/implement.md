# 实施计划

## Phase 1: Lock The Regression

- [x] 在 `tests/app/test_cut_acoustic_boundaries.py` 增加有效 forced delete-start 但真实低能起音提前的合成 PCM，用失败断言证明当前只在候选前 `3ms` 吸附。
- [x] 同时覆盖无持续静音、单点尖谷、立即起音、单调缓升和多组整体增益，锁定 retained hard limit 与无固定 padding 契约。
- [x] 增加文字范围与 timeline 范围共享同一最终点/诊断的断言。

## Phase 2: Implement Shared Head Corroboration

- [x] 在 `server/app.py` 复用现有相对阈值、采样步长和 sample snap，实现 delete-start 专用的单侧持续静音/持续起音佐证。
- [x] 仅把 helper 接入同段普通可信 forced delete-start；不改变 delete-end、repeat、cross-segment、split-exact 或缺失对齐降级。
- [x] 扩充 diagnostics，记录 final、PCM 走廊、起音、hard limit、adjustment 和独立 trust reason。

## Phase 3: Verify Product Data Flow

- [x] 运行 `tests/app/test_cut_acoustic_boundaries.py`、`test_cut_draft.py`、`test_cut_rendering.py`、`test_composition.py` 定向回归。
- [x] 用 job `c55a37df-978e-486d-9c99-e0a40c1626e7` 的源片和草稿在临时目录重新解析/生成，确认第一处物理起点、成片拼接位置和短窗能量。
- [x] 人工试听“所有人 + 一起给你”，并确认没有额外“一”且保留第二遍起音完整。
- [x] 运行受影响测试集合、全量测试和 `git diff --check`。

## Implementation Evidence

- 旧实现失败回归：3 组非削波增益均返回 forced candidate `0.800s`，未清除 `0.750s` 开始的提前起音；无持续静音、短谷和单点尖谷 3 个安全回退场景通过。
- 新实现合成 PCM：3 组增益均返回 `0.750s` 前的同一低能边界，文字与 timeline 共享 boundary cache、物理起点和诊断，语义 `originalStart=0.850s` 不变。
- 单调缓升防误判：修复前 `0.200-0.820s` 线性缓升被错误佐证并把起点前移到 `0.617s`；增加相邻 `5ms` block 的相对能量跃迁要求后，专用 helper 返回不佐证，集成只保留既有 forced candidate 的 `3ms` 采样吸附到 `0.797s`。
- 质量复核发现原实现会倒序采用最后一个静音走廊；被删首字内部若再次短暂停顿，会把更早起音留在保留侧。最终实现改为按时间选择 hard limit 后第一个满足“连续两个低能 block -> 连续两个高能 block -> 相邻局部跃迁”的起音，并增加双静音走廊回归。
- 比例门槛复核发现整段下四分位 floor 会隐含要求静音占走廊约 `25%`。最终实现只要求连续两个 `5ms` 低能 block 相对随后起音显著更低；`10-250ms` 静音、多组增益、均匀低能、轻噪声、单调缓升和非整点 hard limit 性质探测均通过。
- 真实源 PCM 只读复核：`retained hard limit=28.050s`、`forced candidate=28.330s` 时返回 `28.299s`；诊断低能走廊 `28.225-28.300s`，持续起音证据从 `28.305s` 开始，`1x/2x/4x` 结果一致。人工试听仍待用户确认。
- 临时完整成片使用产品 `render_cut_video()` 和原 compose 的全部删除范围生成，仅把第一处起点改为 resolver 返回的 `28.299s`；输出位于 `C:\Users\jiadi\AppData\Local\Temp\codex-deleted-head-fixed-20260826\所有人-一起-修复试听版.mp4`，未改写 job、history 或附件。
- 成片接缝从约 `19.188s` 移到 `19.159s`。接缝前 `25ms` 的 RMS 从旧版 `0.0034486` 降到 `0.0008900`，peak 从 `0.0101318` 降到 `0.0014954`；旧版最后 `10ms` 的能量尖峰在修复版消失。
- 修复接缝局部片段二次识别为“而是你身边所有人一起给你画的那条正常的线”，证明第二遍“一起给你”仍完整进入成片；不足音节的残片仍以用户试听作为最终门槛。
- 用户完成修复版试听后确认提交，人工验收门槛通过。
- 最终声学定向测试：`90 passed`；受影响测试集合：`139 passed`，仅有既有 Starlette `httpx` deprecation warning。
- 最终全量测试：`408 passed`；`compileall` 与任务文件 `git diff --check` 均通过。项目未配置 Ruff/Mypy 等独立 lint/type-check 工具。

## Risk And Rollback Points

- `server/app.py`：任何通用 helper 改动先跑 delete-start/delete-end 双方向和重复转场定向测试；若出现误伤，先撤回 forced delete-start 接入而不是调整全局阈值。
- `tests/app/test_cut_acoustic_boundaries.py`：fixture 必须同时包含保留语音、持续静音、提前起音和 forced candidate，不能只断言硬编码秒数。
- 真实媒体只读；所有生成验证输出写入系统临时目录，不改写 `data/jobs`、`data/history` 或用户附件。
