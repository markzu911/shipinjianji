# 设计：文案字号与播放跟随锚点

## Boundaries

- `web/styles.css` 只调整 `.segment-*` 文案文字层级，不缩放控件几何。
- `web/transcript-follow-scroll.js` 继续作为播放跟随唯一 owner；`app.js` 不新增滚动计算。
- `web/index.html` 只提升 CSS 与跟随脚本资源版本。

## Typography Projection

| 元素 | 当前 | 目标 |
| --- | ---: | ---: |
| `.segment-text` | `10px` | `12px` |
| `.segment-time` | `9px` | `10.8px` |
| `.segment-current-badge` | `7px` | `8.4px` |
| `.segment-no-speech-copy strong` | `9px` | `10.8px` |
| `.segment-no-speech-meta` | `8px` | `9.6px` |

保留现有相对行高，依赖 grid/flex 和内容自然高度扩展；按钮、icon 和勾选伪元素不缩放。

## Follow Anchor

在 `getTranscriptFollowScrollMetrics()` 中以已经过 sticky-resting 修正的工具栏底部计算基础锚点：

```javascript
const baseAnchorTop = toolbarBottom + ANCHOR_GAP;
const desiredAnchorTop = baseAnchorTop + itemRect.height * 3;
const maximumAnchorTop = Math.max(
  baseAnchorTop,
  panelRect.bottom - itemRect.height,
);
const anchorTop = Math.min(desiredAnchorTop, maximumAnchorTop);
```

后续 `itemOffset`、`targetScrollTop`、`tailRemainder`、layer placement 和动画继续消费同一个 `anchorTop`，因此中段、首部、尾部和 reduced-motion 不建立第二套位置逻辑。

## Compatibility And Risk

- 动态换行行以自身高度下移三个位置，符合“位置”语义但像素距离会大于短行；这是有意行为。
- 面板高度不足时优先保证活动行完整可见，允许实际下移少于三行。
- 不改变 placeholder 高度、DOM reparent、动画时长、滚动中断和 follow key 去重。

## Validation

- Node 行为测试锁定动态行高、底部 clamp、中段/尾部/reduced-motion。
- Chromium 检查实际计算字号、活动行相对工具栏位置、唯一按钮、无裁切和 `375px` 无横向溢出。
