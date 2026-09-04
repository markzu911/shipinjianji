# Bug Analysis: 空白删除误伤文字、拉伸时间轴及双视图投影分叉

## 1. Root Cause Category

- **Category**: B - Cross-Layer Contract（主要） + D - Test Coverage Gap + E - Implicit Assumption
- **Specific Cause**: 前端把剪后时间上跨越既有删除洞的连续选区，有损地压成一个连续源时间区间；后端再用粗 ASR 中点推断整字删除，并允许仅有 VAD 的物理端点过度吸附。错误物理区间删掉后文后，retained projection 又把保留文字压到近乎零时长，文字适配算法因此把全局每秒像素数放大。确认弹窗显示源时间，标尺却显示剪后时间，进一步隐藏了这条错位链路。后续修复虽然引入了同 revision 服务端字符投影，但仍把“范围数值变化”误当成唯一重绘条件；retained 字符身份变化而 ranges 不变时，右侧 optimistic 文案和底部时间轴 DOM 因不同刷新路径再次分叉。

## 2. Why Fixes Failed

1. 早期修复分别针对“空白重现”、“文案被删”或“标尺变长”，没有从剪后坐标到源坐标、声学吸附、字符身份投影的完整链路验证。
2. 只要粗 ASR 中点落入选区就允许整个 run 参与吸附，忽略了 forced 真实起音仍在选区外的证据。
3. `boundaryTrustworthy` 同时包含 forced/PCM 和 VAD 证据，将它们统一放行会让 VAD 端点远离用户选区；反过来全部限制在 `0.20s` 又会破坏已有的可信尾音清理。
4. 服务未明确重启时，旧进程继续执行旧逻辑，导致“代码已改但现场仍复现”。
5. 先前测试分别验证服务端 retained 结果或单个 UI 表面，没有构造“数值范围不变但 forced 字符身份变化”，也没有在删除、撤销、重做和刷新后逐字符比较两个表面。

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | 剪后选区遍历 retained spans，保存为多个不连续源 `timelineRanges` | DONE |
| P0 | Architecture | timeline-only 字符判删要求 forced/acoustic 覆盖严格超过半字 | DONE |
| P0 | Runtime Guard | 仅 VAD 授权的物理端点距用户端点不得超过 `0.20s`；整体离开原选区则精确回退 | DONE |
| P0 | Test Coverage | 用现场 `37.810-39.930s` / `39.870-40.010s` 形状锁定 60ms 擦边不删字 | DONE |
| P0 | Browser Regression | 覆盖跨删除洞拆分、短选区确认/撤销/重做和移动端缩放 | DONE |
| P1 | UI Contract | 标尺、轨道标签、状态和确认弹窗统一显示剪后时间 | DONE |
| P1 | Layout Guard | 文案时长坍缩时全局比例封顶 `72px/s` | DONE |
| P1 | Operations | 每次服务端修复后显式重启并验证 `/api/health` | DONE |
| P0 | Architecture | retained projection 安装本身触发右侧文案与时间轴同批 replace，并只在该批失效中保留已校验投影 | DONE |
| P0 | Runtime Guard | 整体校验投影 owner、锚点和字符子序列；任一非法则拒绝整份投影并保守回退 | DONE |
| P0 | Browser Regression | 删除、undo、refresh、redo、refresh 后逐字符断言双视图一致且基础 video 零重载 | DONE |

## 4. Systematic Expansion

- **Similar Issues**: 任何在剪后时间上编辑、但最终保存源时间的艺术字、画中画和分割操作，都必须保留不连续 spans，不能用首尾两个点代表中间有洞的集合。
- **Design Improvement**: 将“文字语义删除”、“时间轴物理删除”、“剪后显示时间”和“源时间持久化”保持为独立所有者，只在显式投影函数中转换。
- **Process Improvement**: 任何时间轴修复都必须同时验证源范围、剪后范围、物理切点、retained transcript、右侧/底部逐字符一致性和真实标尺像素；派生权威对象即使不改变基础数值，也必须单独进入失效矩阵。

## 5. Knowledge Capture

- [x] 更新 `.trellis/spec/backend/media-and-timeline.md` 的多数 forced 覆盖、VAD 物理距离和整体回退契约。
- [x] 更新 `.trellis/spec/frontend/architecture-and-state.md` 和 `.trellis/spec/frontend/ui-and-interactions.md` 的剪后选区与显示时间契约。
- [x] 更新 `.trellis/spec/guides/cross-layer-thinking-guide.md` 的跨坐标链路检查项。
- [x] 增加后端、Node 契约和真实 Chromium 回归。
- [x] 补充 retained 字符身份变化独立触发双表面重绘、非法投影整体拒绝和零基础视频重载回归。
- [x] 检查模板镜像；仓库不存在 `src/templates/markdown/spec/`，无需同步。
- [ ] 规范更新随本任务代码一起提交；当前工作区包含多个未完任务的重叠修改，未经用户要求不单独拆分提交。
