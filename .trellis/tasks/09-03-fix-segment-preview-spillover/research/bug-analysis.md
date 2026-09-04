## Bug Analysis: 单段试听先跳过删除范围导致越界

### 1. Root Cause Category

- **Category**: C - Change Propagation Failure（主要） + D - Test Coverage Gap
- **Specific Cause**: 提交 `7f0aa1f` 将删除区间跳转迁入高频媒体帧入口，但单段试听结束仍仅由低频 `timeupdate` 处理。展示段尾落入相邻文字的物理删除范围时，帧入口会先 seek 到删除尾，随后 `timeupdate` 才暂停并回写展示段尾，因此最终 UI 看似正确但下一段已经出声。原行为测试只覆盖无活动单段范围的公共跳过，没有覆盖有限试听终点与物理删除范围重叠。

### 2. Why Fixes Failed

1. 本次没有先前产品修复尝试；根因定位后直接统一结束动作并调整帧内优先级。
2. 既有测试只观察最终播放头或公共跳过顺序，无法识别“中途先跳到删除尾、随后又校准回来”的瞬时泄露。

### 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | 单段终点、删除跳过、视觉更新固定为有序状态机，结束动作由一个幂等 helper 拥有 | DONE |
| P0 | Test Coverage | Node 行为测试覆盖重叠边界、段内保护、公共跳过、事件顺序和重复回调 | DONE |
| P0 | Browser Regression | 真实 30fps 媒体逐帧记录最大播放时间，并检查最终终点和基础媒体零重载 | DONE |
| P1 | Documentation | 在前端播放帧热路径规范中记录有限预览优先级和重入规则 | DONE |

### 4. Systematic Expansion

- **Similar Issues**: 其他有限预览状态若未来迁入逐帧路径，也必须先明确其终点相对删除跳转的优先级；本任务不改变无文字试听或裁剪衔接试听语义。
- **Design Improvement**: 所有单段结束入口复用同一 helper，避免 rVFC/RAF 与 `timeupdate` 各自维护状态转换。
- **Process Improvement**: 播放热路径重排时，测试必须观察中途最大 source time 和副作用顺序，不能只断言最终 UI 时间。

### 5. Knowledge Capture

- [x] 更新 `.trellis/spec/frontend/architecture-and-state.md` 的播放帧热路径契约。
- [x] 增加 Node 行为回归和真实 Chromium 回归。
- [x] 检查模板镜像；仓库不存在 `src/templates/markdown/spec/`，无需同步。
- [ ] 随本任务代码一起提交规范更新；当前会话不在未获用户要求时自动提交。
