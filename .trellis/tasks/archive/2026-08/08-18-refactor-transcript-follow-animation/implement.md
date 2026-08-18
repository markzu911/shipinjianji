# 文案播放跟随动画重构实施计划

1. 记录基线：develop/生产引用、开发服务健康、脚本版本、178 项完整测试和 15 项前端契约。
2. 在 `web/index.html` 增加单行 now-playing layer，在 CSS 建立检查器定位上下文、固定展示层和纯几何占位；不改现有视觉主题。
3. 重写 `web/transcript-follow-scroll.js` 的 controller：保留真实行 reparent、等高占位和 layer metrics，把逐帧 `scrollTop` RAF 改为一次目标 scroll 提交加 list FLIP/WAAPI；尾部严格在 list animation 完成后移动 layer，并实现 retarget/中断的当前视觉位置提交。
4. 在 `web/app.js` 建立缓存的 playback entries 和可取消视频帧时钟：优先 `requestVideoFrameCallback`、其次 RAF、最后 `timeupdate`；连续播放 O(1) 前进，seek/倒退二分定位，保持试听和删除边界语义。
5. 拆分时间轴结构刷新、低频时间/ARIA 更新与高频视觉更新；缓存 spans/total/scale/节点索引，播放帧只更新 playhead transform 和相邻活动节点。
6. 更新脚本资源版本和无缓存/加载契约；用 `node --check` 和静态测试先排除入口错误。
7. 扩展聚焦 Node DOM 测试，验证按钮唯一、placeholder、FLIP 单次 scroll、距离时长、中段固定、尾部顺序、retarget、中断、迟到 completion、reset/destroy、reduced-motion、视频帧生命周期和 fallback。
8. 运行前端契约和完整 pytest，执行 `git diff --check`、作用域和生产引用检查。
9. 在开发服务桌面和 375px 浏览器连续播放多行文案，检查至少 6 次换段、中间帧 DOM 唯一性、锚点、尾部 clamp、横向溢出、控制台，以及播放期间结构重算计数为零。
10. 更新 frontend architecture/UI/testing 规范，删除旧的逐帧 `scrollTop` 和 `timeupdate` 全量热路径正向契约；派发独立 `trellis-check`。
11. 只提交到 `develop`；归档子任务并记录日志，不推送、不修改生产。

## Validation Commands

```powershell
node --check web/transcript-follow-scroll.js
node --check web/app.js
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_frontend_contracts.py -k "transcript_follow_scroll or shared_frontend_assets"
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
git diff --exit-code -- data
git rev-parse master origin/master
```

## Risk And Rollback Points

- 第 3 步先完成控制器纯 DOM/运动测试；若无法保证单一真实行、单次 scroll 提交、FLIP 无末帧跳动和原索引恢复，不进入 app 集成。
- reparent 后任何只查询 `segmentList` 的调用都可能漏掉活动行；必须集中到统一 helper，不散落 layer 特判。
- layer click handler 必须复用同一函数，禁止复制 90 行事件分支。
- 浏览器中只要出现双按钮、透叠、placeholder 残留或手动滚动被抢回，即视为结构失败，不能用不透明背景或缩短 duration 遮盖。
- 视频帧回调不得调用现有完整 `updateTime()`；如果帧回调中出现 spans/scale/全量 selector 查询，即视为热路径拆分失败。
