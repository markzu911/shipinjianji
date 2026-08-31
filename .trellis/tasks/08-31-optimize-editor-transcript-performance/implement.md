# 编辑器文案交互与播放性能实施计划

## 1. Baseline And Probes

- [x] 固化当前长 fixture 的 P50/P95/max、long task 和 effect 分项，增加播放跨段延迟 probe。
- [x] 为文案节点、时间轴文字、split clip、range、thumbnail、Store/history/PUT/media 建立确定性工作计数。
- [x] 保留真实工程只读基线：DOM 数量、空闲延迟、15 秒播放切段峰值和控制台状态。

## 2. Incremental Transcript Commit

- [x] 把文案展示数据提取为稳定 descriptor，复用现有 display key 和语义范围 helper。
- [x] 实现带重复 key/identity 防护的局部窗口对账；相同节点只更新变化属性。
- [x] 为 cut commit 增加 `reconcile/replace` 失效等级，覆盖普通选择、历史回放、服务端规范化、文案结构修改和初始加载。
- [x] 重建缓存播放 entry，但保证逐帧热路径不新增全量 selector 或结构派生。

## 3. Incremental Timeline Effects

- [x] 对时间轴文字、split clip 和删除范围执行稳定 key 对账；ruler 只在 scale 变化时重建。
- [x] 缩略图缓存命中只重投影现有 frame，不创建 extractor、seek、编码或改写基础 video。
- [x] 给 `runCutCommitEffects()` 增加分项性能 probe，确认 Store 与各 DOM effect 没有隐藏长任务。

## 4. Playback Follow Simplification

- [x] 移除整列表 FLIP、tail phase 和跨段 `previousVisualTop` 动画路径。
- [x] 按“全部读取后集中写入”重排换段逻辑，直接提交最终 scrollTop、三行锚点和 bottom clamp。
- [x] 保留真实行唯一、inert placeholder、用户中断、同 key 去重、目标失效恢复、reset/destroy 和 reduced-motion 终态。

## 5. Regression And Spec Sync

- [x] 更新 Node 行为测试：局部节点 identity、结构 fallback、无列表动画、唯一按钮、锚点/clamp/中断。
- [x] 更新真实 Chromium 性能与工作流测试，达到 PRD AC1-AC8 的预算和计数。
- [x] 回归草稿规范化、undo/redo/refresh、生成前 flush、工具切换、艺术字/画中画和公共媒体 identity。
- [x] 更新 frontend architecture/UI/testing 规范和静态资源版本。

## 6. Quality Gate

- [x] `node --check` 覆盖所有修改的 JavaScript。
- [x] 运行相关前端契约、Store、时间轴与真实浏览器测试。
- [x] 运行完整 `tests/app/browser` 和完整 pytest；记录与本任务无关的既有环境失败。
- [x] 真实应用复测 15 秒播放和可恢复的删除/恢复操作，无 console/page/request error。
- [x] `git diff --check`，复核未纳入其他未提交任务文件。

## Verification Results

- 长 fixture 修改后多轮独立结果均通过 80ms 门槛；最终两轮 P95 为 `65.5ms`、`52.2ms`，最大为 `66.7ms`、`55.0ms`，同步 P95 不高于 `2.1ms`。
- 真实本地 16 秒媒体正常倍速连续播放到 15 秒，跨 30 个文字/空白边界；切段延迟 P95 `0.233ms`、最大 `0.433ms`，无 long task，活动行/播放按钮唯一。
- 节点 identity、一次 `CUT_TIMING_CHANGED`、单 history/PUT、零 extractor/seek/base video `src/load()` 均由浏览器 probe 锁定。
- `tests/app/test_frontend_contracts.py`：`40 passed`；完整 `tests/app/browser`：`55 passed`。
- 完整 pytest：`496 passed, 1 failed`。唯一失败是未修改的竖屏预览 cover/拖动时序；同一代码的独立完整浏览器套件通过，单独重跑又在不同阶段超时，按无关环境波动记录，未放宽断言。

## Rollback Points

- 局部对账若不能证明 identity 安全，先保留 follow 简化并回滚到完整结构渲染。
- 跟随简化若破坏锚点或用户中断，回滚该模块，不连带撤销已验证的 cut commit 增量更新。
- 不通过性能门槛时不得通过放宽阈值交付；记录剩余热点后重新规划虚拟化或 Store 领域渲染。
