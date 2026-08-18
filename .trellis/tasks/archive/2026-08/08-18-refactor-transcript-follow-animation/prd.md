# 重构文案播放跟随动画

## Goal

消除文案播放换段时的按钮重影、行内容叠层和跳动，使“播放中”文案在列表仍可滚动时稳定停在工具栏下方，普通文案连续向上滚动；只有到达列表尾部、无法继续滚动时，绿色框才连续向下移动。

## Background

- 用户录屏 `C:/Users/jiadi/AppData/Roaming/LarkShell/screenshot/20260818133633_rec_.mp4` 为 508×830、30fps、12.4 秒；约 5.12–5.52 秒的逐帧画面可见两个圆圈和两个播放按钮同时出现，证明问题包含真实 DOM 叠层，不只是录像或缓动帧率。
- 当前 `web/transcript-follow-scroll.js:175-177` 在同一 RAF 中写入父面板 `scrollTop` 和真实活动行 `transform`；`web/styles.css:2317` 只把该行提升为不透明高层，但没有移除其列表占位或建立独立展示层。
- 已归档任务 `08-17-transcript-current-segment-playback` 把上述同步动画写成正式设计并用几何伪 DOM 测试验证，但测试没有覆盖真实 DOM 的占位、层叠、按钮唯一性和中间帧绘制，因此错误机制被误判为完成。
- 项目是无 npm、无 bundler 的原生脚本应用。现代 `motion@13.1.0` 主要提供 ESM；可直接加载的 `@motionone/dom@10.18.0` UMD 开发包约 95 KB。动画结构可以用现有 RAF/Web Animations 能力完成，引入依赖不能解决真实行叠层。
- 当前基线为 `develop@5653323`、完整 pytest 178 项、前端契约 15 项；`master == origin/master == 7337413`。
- 结构修复后的桌面与 375px 浏览器采样已证明活动行、播放按钮、占位和锚点均保持唯一且稳定；剩余卡顿来自播放热路径：`timeupdate` 同步执行时间轴结构计算和全量状态扫描，跟随动画又在每个 RAF 写 `scrollTop`，并与 sticky blur、行阴影和换段 reparent 的重排叠加。

## Requirements

- R1：`web/transcript-follow-scroll.js` 继续作为唯一跟随动画模块，但必须新增独立 now-playing 展示层所有权；不得再对仍位于 `segmentList` 的真实活动行执行跟随 transform。
- R2：跟随开始时把真实活动 `li.segment-item` 移入专用单行列表展示层，并在原位置插入不含按钮、data 时间或可交互内容的等高占位；同一 `data-display-key` 的真实文案行和播放按钮在 DOM 中始终只存在一份。
- R3：展示层位于文字检查器的固定定位上下文内，使用当前工具栏底部加 8px 作为锚点；移动真实行后，选择、恢复、编辑和播放按钮仍走现有处理函数，键盘/ARIA 语义不降级。
- R4：中段不得在 JavaScript 动画帧中持续写面板 `scrollTop`；目标滚动位置只提交一次，列表用 FLIP/WAAPI compositor `transform` 从旧视觉位置过渡到新位置，展示层保持在锚点。尾部目标被 `maxScrollTop` 截断后，必须先完成列表上移，再让展示层按未消耗距离向下移动。
- R5：占位高度必须来自移动前真实行的布局盒，并保持列表 `scrollHeight`、后续行位置和滚动目标稳定；状态 badge、按钮 hover 或不同高度文案不得在换段时改变占位尺寸。
- R6：切换活动行时先把旧行恢复到其占位位置，再移动新行；展示层视觉位置从上一帧连续过渡到新目标，不允许闪回自然位置、同时保留两行或丢失原始顺序。
- R7：完成动画后真实活动行继续驻留展示层，直到换段、停止跟随、列表重渲染、用户滚动接管或控制器销毁；所有退出路径必须恢复真实行、删除占位、隐藏展示层并清理帧、transform、尺寸和监听器。
- R8：`wheel`、`touchstart`、`pointerdown` 和滚动键继续立即交还滚动控制；用户中断后不得被同一 display key 的后续 `timeupdate` 抢回。`prefers-reduced-motion: reduce` 使用即时滚动和即时定位，但保持同样的唯一 DOM/占位契约。
- R9：不改变当前段落播放起止、已删除文案试听、空白试听、seek、删除选择、草稿、撤销/重做或时间轴语义；活动段判定改用 `requestVideoFrameCallback` 驱动的轻量游标，浏览器不支持时回退 RAF/`timeupdate`，pause、ended、seek、换源和 destroy 必须正确取消或重置回调。
- R10：不引入 Motion One、GSAP、Lenis、虚拟列表、npm、ES module 或构建步骤；动画使用原生 WAAPI/FLIP，播放同步使用原生 `requestVideoFrameCallback` 与明确回退。
- R11：更新 `index.html` 资源版本、前端无缓存契约和前端架构/UI 规范；旧的“同步 `scrollTop + row transform`”规范必须删除，防止以后恢复错误方案。
- R12：只在 `develop` 修改前端、聚焦测试、任务和规范；不得修改后端 API/媒体逻辑、`data/`、生产引用或生产服务。
- R13：时间轴结构计算必须退出播放热路径。edited spans、总时长、轨道宽度和文案坐标只在数据、选择、容器尺寸或来源变化时失效重算；播放帧只更新 compositor 播放头和当前段游标，时间文本/ARIA 可以低频更新。
- R14：文案展示项在 render 后建立稳定的排序索引与元素引用；连续播放按当前游标 O(1) 前进，seek/回退使用二分定位，不得在每个视频帧查询全部 `.segment-item`、重建 spans 或遍历全部时间轴文案节点。
- R15：动画时长按实际移动距离限制在稳定区间，retarget 从当前 FLIP/展示层视觉位置继续；用户中断必须把当前视觉位移提交为等价滚动位置后清理动画，不能闪回目标或旧位置。

## Acceptance Criteria

- [ ] AC1（R1-R3）：动画任意时刻每个 display key 只有一个真实 `.segment-item`，播放按钮总数与展示行数一致；展示层承载真实行，占位不含按钮、时间 data 或可聚焦元素。
- [ ] AC2（R3、R9）：展示层中的删除、恢复、编辑和播放操作与列表内行为一致；活动行继续具有 `aria-current` 和“播放中”状态，点击播放不会打开编辑弹窗或改变删除状态。
- [ ] AC3（R4-R5、R15）：中段展示层顶部与工具栏锚点误差不超过 1px；一次 motion 内面板 `scrollTop` 最多提交一次目标值，列表 FLIP transform 单调归零，`scrollHeight` 在移动前后误差不超过 1px。
- [ ] AC4（R4）：尾部 `scrollTop` 停在 `scrollHeight-clientHeight`；列表 FLIP 归零前展示层不向下，随后展示层顶部只按剩余距离单调下移，结束位置与占位自然位置误差不超过 1px。
- [ ] AC5（R6-R7）：跨多个普通/删除/空白行连续播放时，旧行严格恢复原索引，新行严格占据唯一展示层；换段、重渲染、reset、destroy 和迟到旧帧均不留下占位、transform、监听器或脱离列表的行。
- [ ] AC6（R8）：用户滚轮、触摸、指针和键盘滚动可立即中断；同 key 不重新抢占，下一 display key 仍可恢复自动跟随；reduced-motion 不产生运动帧。
- [ ] AC7（R1-R10、R13-R15）：Node DOM 行为测试直接验证 reparent、占位、按钮唯一性、FLIP 单次 scroll 提交、中段、尾部时序、重定向、中断、reduced-motion、视频帧回调生命周期和 fallback；聚焦前端及完整 pytest 全部通过。
- [ ] AC8（R11）：资源版本、加载顺序、无缓存路径和前端规范已同步，仓库中不存在把真实活动行和父滚动容器同时补间的生产实现或正向规范。
- [ ] AC9（R3-R9、R13-R15）：开发服务桌面和 375px 浏览器连续播放至少 6 次换段，中间帧无双圆圈、双播放按钮、文字透叠或横向溢出；帧时钟不重复注册，播放热路径不重算时间轴结构，尾部行为符合录屏目标，控制台无新增错误。
- [ ] AC10（R12）：`web/` 以外仅测试、规范和 Trellis 任务文件变化；生产引用保持 `7337413`，生产服务不重启、不修改。

## Out Of Scope

- 不修改文字/空白删除边界、ASR 时间戳、剪辑生成或音频吸附。
- 不重写文案列表、引入虚拟化或改变视觉配色、字号和行布局。
- 不重写完整播放器状态机；只拆分与播放进度、文案换段和时间轴视觉同步直接相关的热路径。
- 不把第三方动画库作为结构问题的遮盖层。

## Key Decisions

- 用“真实行 reparent + 等高占位 + 固定展示层”代替 clone；这样按钮和 data 只有一份，现有交互可以复用。
- 展示层是内部原生组件，不引入外部动画包；列表滚动采用“一次 scroll 提交 + FLIP/WAAPI”，避免 JavaScript 每帧触发布局与整列重绘。
- 播放帧时钟、低频时间文本更新和结构性时间轴重算分离；帧时钟只消费预计算索引，不能把现有全量 `updateTime()` 搬到每个视频帧。

## Risks And Deferred Items

- reparent 会让现有仅查询 `segmentList` 的活动行逻辑暂时看不到当前行；实现必须通过统一 display-item 查询同时读取列表和展示层，并在重渲染前 reset。
- 事件委托当前绑定 `segmentList`；展示层必须绑定同一个命名处理器，不能复制业务分支。
- WAAPI 在 Node 伪 DOM 中需要可控替身；测试必须同时覆盖动画完成、取消、迟到回调和不支持 `requestVideoFrameCallback` / `Element.animate` 的回退路径。
