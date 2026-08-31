# 编辑器文案交互与播放性能设计

## 1. Design Goal

把高频文案选择的关键路径从“全量重建多个 DOM 层”改为“提交语义状态并局部对账”，同时把播放换段从“真实行搬移 + 整列表 FLIP + 尾部动画”简化为“读完几何后一次写入最终状态”。剪辑语义、Store、草稿 revision、VAD 边界、撤销/重做和媒体 owner 不变。

## 2. Ownership And Boundaries

- `web/app.js` 继续拥有选择集合、cut commit scheduler、文案 DOM、时间轴文字/范围/片段投影和性能 probe。
- `web/transcript-follow-scroll.js` 继续唯一拥有活动真实行 reparent、占位、三行锚点、底部 clamp、用户中断和恢复顺序，但不再拥有整列表 FLIP 动画。
- `web/editor-suite.js`、`EditorProjectStore` 和服务端 API/schema 不新增 owner；一次 cut 命令仍最多一个 `CUT_TIMING_CHANGED`。
- `web/timeline-thumbnail-cache.js` 不修改持久记录；普通选择只重投影现有 source-time frame。

## 3. Cut Commit Render Plan

### 3.1 Explicit invalidation mode

`updateSelectionSummary()` 增加明确的 render intent，并合并同一帧的最高失效级别：

```javascript
updateSelectionSummary({
  transcript: "skip" | "reconcile" | "replace",
  timelineText: "skip" | "reconcile" | "replace",
})
```

- `skip` 表示该表面无需重绘；普通调用默认请求 `reconcile`。
- 普通文字/空白删除恢复、撤销/重做和已提交时间轴范围默认 `reconcile`。
- 文案拆分/合并、权威文案替换、任务切换、初始加载及 identity 校验失败使用 `replace`。
- 同一帧收到多个请求时 `replace` 优先，不能因后一个普通选择把结构失效降级。
- 取消尚未完成的 effect 时，只把未执行阶段的 intent 放回队列；`flushPendingCutCommitEffects()` 按当前阶段同步排空 render plan，保证生成读取最新状态。

### 3.2 Transcript keyed reconciliation

从现有 `currentEditableSegments`、no-speech 和删除语义构造纯 descriptor；descriptor 使用当前 `data-display-key` 身份并包含展示 kind、范围、文字、range keys 和 selected/disabled 状态。

`reconcileCutSegments()`：

1. 先让跟随控制器恢复正在展示的真实行，保证列表拥有完整顺序。
2. 比较现有 key 序列与目标 key 序列，保留公共前缀/后缀，只替换中间差异窗口。
3. 相同 key 的节点只更新发生变化的 class、ARIA、时间和 data；不重新创建按钮或文字 DOM。
4. 结构 identity 异常、重复 key 或无法安全对账时回退 `renderCutSegments()`，不能留下部分 DOM。
5. 对账完成后从真实节点重建播放 entry 索引；不在每一视频帧查询全量 DOM。

普通整段选择通常只改变一个局部窗口；部分 AI 范围导致的 run 拆分/合并也只替换所属 segment 的连续窗口。剪后时间变化会更新后续时间标签，但仅在格式化结果实际变化时写 DOM。

### 3.3 Timeline reconciliation

- 时间轴文字 descriptor 使用稳定的 source identity；相同 key 节点只更新 `left/width/text/ARIA`，新增或消失的连续窗口局部插入/移除。
- ruler 只在 scale signature 变化时重建；split clip 和 delete range 使用现有语义 key 对账并更新几何，不再无条件 `replaceChildren()`。
- 缩略图仍调用 source-frame 投影，但签名命中时只更新已有节点几何；不得创建 extractor、seek、编码或重写基础媒体。
- 首个可见 commit 只写删除/恢复状态、控件状态和保守的生成禁用态；精确 merged range、删除时长和统计文案延迟计算，并在后置阶段再次校正生成状态。
- 后置 effect 分为 `transcript -> Store -> timeline -> timelineAux` 四个独立任务：`timeline` 处理时间轴文字/ruler，`timelineAux` 处理 split/range/thumbnail/draft。显式 flush 必须从当前阶段同步补齐所有剩余工作。
- `runCutCommitEffects()` 记录 summary、transcript、Store、timeline text、clip/range 和 thumbnail projection 的独立耗时，便于证明 long task 已移除。

## 4. Playback Follow Fast Path

`follow(item, key)` 保留同 key 立即返回。换 key 时严格分为读阶段和写阶段：

1. 取消旧状态并恢复旧真实行；不读取写入后的几何。
2. 一次读取 item、panel、toolbar 和定位 context 几何，计算目标 `scrollTop`、三行锚点及 bottom clamp。
3. 插入等高 inert placeholder，把真实行移入展示层。
4. 一次写入 panel `scrollTop`、展示层尺寸/位置和最终 tail offset。

不再对整个列表写 `transform/will-change`，不建立 list/tail WAAPI 阶段，也不读取 `previousVisualTop` 做跨段路径动画。用户 `wheel/touchstart/pointerdown/scroll key` 仍立即恢复真实行；reset、重渲染和销毁继续清理 placeholder、展示层样式与监听器。`prefers-reduced-motion` 与普通模式拥有相同最终结果，因为两者都不执行整列表动画。

## 5. Data And Compatibility

- 不修改 cut-draft request/response、localStorage schema、history snapshot、Store action 或后端持久化。
- 不修改 `originalStart/originalEnd`、物理边界、split ownership 和 retained projection 身份。
- 更新 `app.js` 与 `transcript-follow-scroll.js` 静态资源版本，避免浏览器混用旧控制器和新消费者。
- 若局部对账发现 identity 不可信，单次回退完整重建；这是兼容保护，不得成为普通点击常态。

## 6. Performance Validation

- 扩展现有长 fixture，记录同步点击、第二个 rAF、各 effect 分项、long task、节点 identity、Store/history/PUT/extractor/media 计数。
- 新增真实播放 fixture，跨至少 8 个文案/空白边界，记录每次 key 变化附近的 event-loop/rAF 延迟、活动按钮唯一性、锚点和 bottom clamp。
- 浏览器测试必须验证普通选择保留未受影响节点 identity，结构变化走完整替换且功能正确。
- 在当前真实 2:23 工程复测空闲、播放 15 秒和多次删除/恢复；不对用户历史版本执行不可恢复操作。

## 7. Risks And Rollback

- 风险：局部 key 对账漏掉结构变化。控制措施是失效等级、重复 key 检查、公共前后缀之外整窗替换和单次 full-render fallback。
- 风险：活动行 reparent 时恰逢剪辑重渲染。对账前统一 reset，完成后由当前播放时间重新选择活动行。
- 风险：减少动画后视觉跳转更直接。这是用户已接受的性能优先取舍，最终锚点和绿色活动状态不变。
- 回滚：保留完整 `renderCutSegments()`/完整时间轴渲染入口；局部对账可独立撤回，不影响 schema 或用户数据。
