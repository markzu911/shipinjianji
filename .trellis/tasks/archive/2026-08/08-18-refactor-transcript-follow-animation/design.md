# 文案播放中展示层重构设计

## Root Cause

上一版把一个真实列表行同时当作两种对象：它既是列表中的布局节点，又通过 `transform` 成为顶部展示层。父容器滚动时，它的布局槽位仍随列表移动，绘制层却被拉回顶部；相邻文案从该槽位和提升层下方经过，真实浏览器因此出现双圆圈、双播放按钮和内容透叠。伪 DOM 测试只验证 `visualTop` 公式，无法观察占位、绘制顺序或按钮重复。

## Ownership And DOM

```text
.text-editor-inspector (positioning context, overflow hidden)
├─ .text-editor-panel-stack
│  └─ #textCutsPanel (scroll container)
│     └─ #segmentList
│        └─ li.segment-follow-placeholder (geometry only)
└─ #transcriptNowPlayingLayer (single-row list, absolute)
   └─ li.segment-item.is-playback-active (the real row)
```

- `web/index.html` 显式提供 `#transcriptNowPlayingLayer`，初始 hidden。
- `web/transcript-follow-scroll.js` 唯一拥有 reparent、占位、展示层位置、列表 FLIP/WAAPI、用户中断和恢复顺序。
- `web/app.js` 继续拥有活动行判定、ARIA/badge 和所有行交互，只把同一个命名 click handler 同时绑定到 `segmentList` 与展示层。
- `web/styles.css` 提供固定定位上下文、单行展示层和无内容占位样式，不定义动画时序。

## Controller Contract

```javascript
const controller = TranscriptFollowScroll.createController({
  layer: transcriptNowPlayingLayer,
});

controller.follow(item, displayKey);
controller.reset();
controller.destroy();
```

控制器内部状态保存 `item`、`placeholder`、`panel`、`list`、`layer`、当前 metrics、WAAPI animation、跟随 key 和用户中断监听。`follow()` 只接收已经带 `.is-playback-active` 的有效真实行。

## Placement Algorithm

1. 在移动前读取 `item.getBoundingClientRect()`、panel、toolbar、layer offset parent 和滚动边界。
2. 在 item 前插入无内容占位，显式固定其 block size；再把 item 移入 layer。
3. layer 的 base top 为 `toolbar.bottom + 8` 相对 positioning context 的位置，left/width 来自移动前 item rect。
4. 用占位 rect 计算 `itemOffset`，再得出：

```text
scrollDelta = clamp(startScrollTop + itemOffset) - startScrollTop
tailRemainder = itemOffset - scrollDelta
```

5. 中段把 `panel.scrollTop` 一次性提交到 target；同时给 list 施加等量 inverse transform，使首帧视觉位置不变，再用 WAAPI 把 transform 补间到零。动画帧不得继续写 `scrollTop`。
6. 尾部先完成 list 的可滚动距离 FLIP；只有 list transform 归零后，layer 才从锚点补间到 `tailRemainder`。
7. 首次跟随从 item 的自然视觉位置进入；连续换段从上一展示层和 list animation 的当前视觉状态继续。距离决定时长并 clamp 到 180-360ms，避免不同高度行速度突变。

## Playback Scheduling

- 播放开始时注册唯一 `requestVideoFrameCallback` 循环；pause、ended、emptied、换源和销毁时取消。没有该 API 时使用可取消 RAF，最后才依赖 `timeupdate`。
- render 后构建排序的 playback entries，保存 start/end/key/element；连续播放使用游标前进，seek 或时间倒退使用二分查找。
- 视频帧回调只更新当前段和 compositor 播放头，不执行草稿序列化、时间轴宽度计算、全量 DOM 查询或 ARIA 文本刷新。
- `timeupdate` 继续负责低频时间文字、ARIA 和现有试听/跳过边界语义，但不再拥有活动文案跟随调度。

## Timeline Hot Path

- `edited spans`、edited total、pixels-per-second、track width 和时间轴文案节点索引建立显式缓存；只在选择、草稿、媒体、render 或 resize 后失效。
- 播放帧更新 playhead 使用 transform/CSS variable；只切换上一个和下一个 active timeline text node，不遍历全部节点。
- 结构刷新入口与播放视觉入口分名，测试锁定视频帧期间不会调用 scale/structure rebuild。

## Restore And Retarget

- `restorePinnedItem()` 把真实行插回 placeholder 前、删除 placeholder、清空 layer 尺寸/transform 并 hidden；该函数必须幂等。
- 新目标先取消旧 WAAPI/回退帧并提交当前视觉滚动位置，再恢复旧行，然后为新行创建占位；迟到 completion 通过 motion identity 检查失效。
- 正常动画完成后不恢复：真实活动行继续留在展示层，直到下一目标或退出跟随。
- 用户滚动、`reset()`、`destroy()`、目标失效和列表重渲染都恢复真实行；用户中断保留跟随 key，reset/失效释放 key。

## App Integration

- 新增 `transcriptDisplayItems()`，返回展示层真实行与 `segmentList` 普通行；活动判定和当前行查找不得假设所有真实行都在 `segmentList`。
- 把现有匿名 `segmentList` click 回调提取成一个命名 handler，并绑定两个容器；业务分支保持原样。
- `renderCutSegments()` 在替换列表前继续调用 `reset()`，保证真实行先归位。
- 不改变 `timeupdate`、`transcriptPreviewRange`、单段结束校准或删除状态。

## Accessibility And Stable Layout

- layer 是有明确标签的单行列表，承载原始 `li`，因此按钮、焦点、`aria-current` 和 data 不复制。
- placeholder 使用 `aria-hidden="true"`、`inert` 且不含可聚焦后代。
- 展示层宽度、行高和锚点在一次 motion 内固定，hover/badge 不触发列表重排。
- reduced-motion 仍使用同一 reparent 结构，但一次性写入目标 scrollTop 和 tail offset，不创建 WAAPI animation。

## Dependency Decision

不引入 Motion One。现代包与当前全局 defer 脚本模式不匹配，旧 UMD 体积相对单一动画过大；更重要的是第三方 tween 不会修复播放热路径和 DOM 所有权。使用浏览器原生 WAAPI、`requestVideoFrameCallback` 和明确 fallback。

## Rollback

没有数据迁移。单提交回滚时恢复旧控制器、删除 layer DOM/CSS 和新测试即可；播放边界、草稿和后端不需要回滚。
