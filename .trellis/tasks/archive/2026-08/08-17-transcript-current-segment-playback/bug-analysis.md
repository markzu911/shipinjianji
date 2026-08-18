# Bug Analysis: 播放中绿色框先跳后滚

## 1. Root Cause Category

- **Category**: E - Implicit Assumption，兼有 D - Test Coverage Gap。
- **Specific Cause**: 活动行样式立即切换，但原生 smooth scroll 使用浏览器独立时间线；代码假设“目标位置正确”就等同于“运动过程连续”。旧测试只检查最终 `scrollTop`、顶部锚点和尾部 clamp，没有逐帧约束绿色框与列表内容的相对运动。

## 2. Why Fixes Failed

1. 顶部锚点与尾部 clamp 修复解决了最终位置，但仍让活动行 class 和 native smooth scroll 分别更新，因此绿色框会先出现在下一行自然位置，再随列表上移。
2. 重复 key 去重只覆盖正常可见目标；首次目标隐藏或运动中目标失效时若提前保留 key，会让同一行恢复可见后无法重试。

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | 由 `transcript-follow-scroll.js` 单一控制器同步管理 `scrollTop`、transform、RAF、key 和清理 | DONE |
| P0 | Test Coverage | Node 逐帧验证中段固定、尾部下移、迟到帧、隐藏重试、用户中断和 reduced-motion | DONE |
| P1 | Browser Verification | 桌面与 375px 采样真实跨行运动、尾部 max clamp、横向溢出和控制台 | DONE |
| P1 | Documentation | 在前端 architecture/UI spec 固化模块所有权、取消和 key 生命周期 | DONE |

## 4. Systematic Expansion

- **Similar Issues**: 任何“先切换 active DOM，再调用原生 smooth scroll”的列表都可能出现同类跳动；后续新增跟随视图应复用可取消控制器模式。
- **Design Improvement**: 动画最终位置与动画过程必须属于同一所有者，不能让 CSS 状态、浏览器滚动和业务 key 各自维护独立生命周期。
- **Process Improvement**: 动画缺陷验收必须包含过程采样、取消/重定向和 reduced-motion，不能只断言终点截图。

## 5. Knowledge Capture

- [x] 更新 `.trellis/spec/frontend/architecture-and-state.md`。
- [x] 更新 `.trellis/spec/frontend/ui-and-interactions.md`。
- [x] 增加独立模块和 Node 行为回归。
- [x] 项目不存在 `src/templates/markdown/spec/` 或 `.trellis/templates/markdown/spec/`，无需同步模板副本。
