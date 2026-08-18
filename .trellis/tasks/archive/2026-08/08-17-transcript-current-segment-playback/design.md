# 文案跟随滚动模块与动画设计

## Boundaries And Ownership

- `web/transcript-follow-scroll.js` 唯一拥有跟随滚动的目标计算、展示 key 去重、RAF 调度、动画进度、用户中断监听和临时样式清理。
- `web/app.js` 继续拥有当前播放时间、活动文案判定、`aria-current`、播放中 badge 和 `transcriptPreviewRange`；它只在活动行确定后调用控制器，在列表重渲染或停止跟随时调用 `reset()`。
- `web/styles.css` 只提供活动行动画期间的不透明提升层样式，不拥有动画时序。
- `web/index.html`、`server/app.py` 和 `tests/app/test_frontend_contracts.py` 共同维护新静态脚本的加载、版本和无缓存契约。

```text
timeupdate / 单段播放
        |
        v
app.js: 选出活动行 + 更新 ARIA/badge
        |
        v
TranscriptFollowScroll controller
  |- 计算 toolbar.bottom + 8 锚点
  |- clamp 目标 scrollTop
  |- 同步 scrollTop + row transform
  `- 取消、去重与清理
```

## Public Contract

模块沿用项目已有的浏览器全局/CommonJS 双导出模式：

```javascript
const controller = window.TranscriptFollowScroll.createController();
controller.follow(item, displayKey);
controller.reset();
controller.destroy();
```

- `follow(item, displayKey)`：同 key 已跟随后直接返回；新 key 会取消旧动画，读取 item 所属 `.text-editor-panel` 和 `.cut-toolbar`，然后调度新定位。
- `reset()`：取消 RAF、清除 key、transform、动画 class 和当前面板上的用户中断监听，供重渲染及非跟随更新调用。
- `destroy()`：与 `reset()` 同样清理资源，保留独立生命周期语义供页面卸载或未来消费者使用。
- 模块额外导出纯目标计算函数供 Node 精确测试；`app.js` 不包装或复制该算法。

## Motion Model

设活动行初始相对锚点偏移为 `itemOffset`，可滚动距离为 `scrollDelta = targetScrollTop - startScrollTop`，缓动进度为 `p`：

```text
scrollTop(p) = startScrollTop + scrollDelta * p
transformY(p) = -itemOffset * (1 - p)
visualTop(p) = anchorTop + p * (itemOffset - scrollDelta)
```

- 中段 `itemOffset == scrollDelta`，所以 `visualTop` 始终等于锚点，绿色框不动，内容从后方上滚。
- 尾部目标被 `maxScrollTop` 截断，`itemOffset - scrollDelta > 0`，所以绿色框只在列表不能继续上滚时从锚点连续向下移动。
- 动画开始前为活动行添加 `is-follow-animating` 并设置初始 transform；该 class 使用不透明背景和较高层级，避免下面的文案透叠。
- 完成或取消时统一移除内联 transform、`will-change` 和动画 class。
- `prefers-reduced-motion: reduce` 直接写入目标 `scrollTop`，不创建运动帧或 transform。

## Cancellation And Retargeting

- 控制器同时只允许一个排队帧或运动帧；新目标先执行集中 cleanup，再建立新动画。
- `wheel`、`touchstart`、`pointerdown`、滚动相关 `keydown` 表示用户要接管面板，立即取消自动动画，监听器使用可移除的稳定引用。
- `app.js` 在 `renderCutSegments()` 开头和 `updateActiveTranscriptSegment(..., { follow: false })` 路径调用 `reset()`，确保已脱离 DOM 的旧行不会被后续帧写入。
- 每帧继续验证 item 已连接、仍为 `.is-playback-active` 且 panel 未隐藏；任一条件失效即清理退出。

## Loading And Compatibility

1. `web/index.html` 在 `app.js` 前加载 `/transcript-follow-scroll.js?v=<version>`。
2. `server.app.disable_frontend_cache` 加入 `/transcript-follow-scroll.js`。
3. 静态资源测试请求新脚本，断言 `cache-control: no-store, max-age=0`、全局 API 和加载顺序。
4. `app.js` 版本同步递增，避免开发服务和用户浏览器混用新旧入口。
5. 不引入 ES module、npm、构建步骤或外部动画库。

## Test Strategy

- Node 直接 `require('./web/transcript-follow-scroll.js')`，使用可控 RAF 时间戳和伪 DOM 测试纯目标计算与完整控制器行为。
- 中段断言每个采样帧的视觉 top 固定，尾部断言视觉 top 单调向下且最终清除 transform。
- 重定向和手动中断断言旧回调即使被调用也不能继续写 scrollTop；相同 key 不增加帧。
- reduced-motion 断言只执行即时定位，不进入动画 class。
- Python 静态契约断言实现已从 `app.js` 移除、新脚本顺序和版本正确。
- 浏览器在桌面和 375px 验证真实 sticky toolbar 尺寸、跨多行播放、尾部行为、手动滚动接管和控制台错误。

## Rollback

本任务不迁移持久数据。回滚时可恢复旧的三个跟随函数与两个状态变量、移除新脚本引用和样式；单段播放及时间戳逻辑不受影响。结构拆分和动画行为应在同一任务内提交，避免入口引用与模块文件版本不匹配。
