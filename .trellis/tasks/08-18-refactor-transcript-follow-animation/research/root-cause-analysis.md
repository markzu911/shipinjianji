# Bug Analysis: 文案换段跟随动画叠层

## Evidence

- 用户录屏：`20260818133633_rec_.mp4`，12.4 秒、30fps。
- 5.12–5.52 秒逐帧：活动行移动期间同时可见两组圆圈和播放按钮，可靠性高于主观“卡顿”描述。
- 生产实现：`advanceMotion()` 同帧写 `panel.scrollTop` 和真实 `item.style.transform`。
- CSS：`is-follow-animating` 只提升真实行层级，没有把它从列表布局职责中分离。
- 旧测试：伪 DOM 用 transform 数学修正 `getBoundingClientRect()`，但不模拟真实 grid 占位、绘制、按钮和层叠上下文。
- 结构重构后的桌面与 375px 浏览器连续换段采样中，活动行、展示层和占位最多各一份，按钮总数恒定且中段锚点误差为 0；说明重复 DOM 已闭环，但“不卡顿”仍未闭环。
- 当前播放链路为 `timeupdate -> updateTime -> updateCutTimelinePlayhead -> updateActiveTranscriptSegment`。同一次回调重复计算 edited spans/scale、写时间轴属性、遍历全部时间轴文案和 display items，并在换段时启动动画。
- 当前动画 RAF 每帧写 `panel.scrollTop`；sticky toolbar 使用 blur/box-shadow，活动行还有 background/box-shadow/text-shadow transition，导致主线程滚动布局与绘制竞争。
- 普通、删除和空白行高度不一致，但动画固定 240ms；相同 duration 对不同距离产生明显速度变化，短空白边界还会触发展示层 reset/recreate。

## 1. Root Cause Category

- **Category D - Test Coverage Gap**：测试证明公式成立，但没有证明真实 DOM 中不重叠。
- **Category E - Implicit Assumption**：设计假设不透明高层等于独立展示层，忽略真实行仍同时承担列表布局和顶部展示两种职责。
- **Category B - Hot Path Coupling**：播放帧、低频时间文字、时间轴结构重算和活动文案查找共用一个 `timeupdate` 链路，结构工作阻塞换段首帧。
- **Category C - Main-thread Animation**：JavaScript 每帧写 `scrollTop`，使长列表、sticky blur 和阴影持续参与布局/绘制；overlay transform 虽可合成，但不能抵消父滚动的主线程成本。
- **Category F - Timing Model**：固定 240ms 时长忽略实际滚动距离，`timeupdate` 又不是稳定逐帧时钟，造成启动时机和视觉速度都不均匀。

## 2. Why The Previous Fix Failed

1. **Surface fix**：增加不透明背景和 z-index 只隐藏部分透叠，没有消除双重所有权。
2. **Mental model**：只验证活动行视觉 top 的数学轨迹，没有验证其占位和相邻行的绘制轨迹。
3. **Incomplete browser evidence**：验收描述写了真实浏览器，但没有把中间帧“按钮数量恒定、行只存在一次”变成可重复断言。

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | 固定展示层和列表布局节点分离，真实行只存在一次 | Planned |
| P0 | Test | 中间帧断言按钮唯一、占位无交互、原索引可恢复 | Planned |
| P0 | Spec | 删除同步补间父 scrollTop 与列表内真实行 transform 的正向示例 | Planned |
| P1 | Browser | 桌面/375px 连续换段并检查中间帧和 DOM 计数 | Planned |
| P0 | Scheduling | `requestVideoFrameCallback` 只推进缓存的活动段游标，低频 UI 与结构刷新分离 | Planned |
| P0 | Animation | 面板 scrollTop 每次 motion 只提交一次，列表用 FLIP/WAAPI compositor transform | Planned |
| P0 | Cache | spans、total、scale 和 timeline node index 只在结构变化时失效重算 | Planned |
| P1 | Timing | 按距离限制动画时长，尾部严格在列表 FLIP 完成后再移动展示层 | Planned |

## 4. Systematic Expansion

- **Similar Issues**：艺术字和画中画的拖动预览也同时涉及布局与 transform，后续审查应确认每个元素只有一个权威定位坐标系。
- **Design Improvement**：动画对象必须明确是 layout node、overlay node 或 placeholder，不能让一个节点同时承担互相矛盾的坐标职责。
- **Process Improvement**：motion 验收除最终位置外，必须覆盖中间帧、DOM 唯一性、取消和 reduced-motion。
- **Performance Improvement**：播放热路径验收必须证明没有 scale/spans/全量 selector 重算，并锁定单次 scroll 提交、视频帧回调唯一注册和 fallback 生命周期。

## 5. Knowledge Capture

- 实施完成后更新 `.trellis/spec/frontend/architecture-and-state.md`、`ui-and-interactions.md` 与测试规范。
- 在独立 check 中确认旧契约和旧生产模式均已删除。
