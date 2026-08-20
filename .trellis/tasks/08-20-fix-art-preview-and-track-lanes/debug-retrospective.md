# Bug Analysis: 艺术字预览漂移与分类轨道额外换行

## 1. Root Cause Category

- **Category**: B - Cross-Layer Contract；E - Implicit Assumption；D - Test Coverage Gap
- **Specific Cause**: 基础视频按内容矩形 contain/cover，艺术字却按外层舞台缩放，形成两套坐标权威；文案 cue 先规范边界后又由逐字时间重写起止点，后置派生步骤重新破坏非重叠不变量；旧时间轴测试把“重叠自动换 lane”当成正确行为，没有覆盖产品要求的一类一行。

## 2. Why Fixes Failed

1. 前一任务只合并了逻辑轨 ID，并用临时 lane 保证重叠 clip 可见，解决了“一项一轨”的数据症状，却没有确认用户看到的可视行仍会增加。
2. 旧预览实现用舞台宽度缩放字号，在横屏素材上不易暴露；缺少 `720x1280` 素材与横向舞台的真实浏览器几何比较。
3. 文案 cue 在第一次裁边后继续写回 `characterTimings`，旧测试只检查 compose 前归一化，没有检查最终 API 返回的严格边界和下一 cue 原值。
4. 质量检查发现旧设备预览 CSS 仍禁用 overlay 指针，说明只验证几何公式不足以证明真实交互可用。

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | art/pip 只在源视频尺寸 canvas 中计算，contain/cover 只作为一次外层显示变换 | DONE |
| P0 | Runtime invariant | 在逐字时间回写后复用同一 transcript timing helper，严格消除任何正值重叠 | DONE |
| P0 | Browser tests | 使用真实 `720x1280` 媒体验证 contain、cover、拖动、PiP 缩放与设备 UI 分层 | DONE |
| P1 | Timeline contract | 手动与文案使用不同逻辑轨且每条艺术字逻辑轨固定一行，重叠项由 selection/focus/list 保持可操作 | DONE |
| P1 | Review checklist | 跨层指南增加“单一内容画布”和“后置派生后最终归一化”检查项 | DONE |

## 4. Systematic Expansion

- **Similar Issues**: PiP 与其他 overlay 若直接按舞台坐标计算，也会在 contain/cover 或黑边下漂移；任何先 normalize 后再写回派生边界的流程都可能重新破坏不变量。
- **Design Improvement**: 展示 viewport、内容 canvas 和业务 overlay 必须分层，Store 永远只保存内容坐标；最终边界 helper 同时服务 API 与 compose。
- **Process Improvement**: 几何修改必须加入非方形真实媒体浏览器回归；时间修改必须断言相邻后一对象的文字、起点和源锚点完全不变。

## 5. Knowledge Capture

- [x] 更新前端 UI 与架构规格，记录共享内容画布和艺术字分类单行契约。
- [x] 更新后端媒体规格，记录亚毫秒严格边界与下一 cue 保真。
- [x] 更新测试规格和跨层思考指南。
- [x] 检查模板镜像；仓库不存在 `src/templates/markdown/spec/`，无需同步。
