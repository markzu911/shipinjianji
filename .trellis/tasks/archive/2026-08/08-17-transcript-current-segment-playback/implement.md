# 文案跟随滚动拆分与动画实施计划

1. 保存基线：确认 `develop`、`master/origin/master` 指针，记录 `web/app.js` 大小、现有跟随函数位置、开发服务健康状态和当前全量测试节点数。
2. 新建 `web/transcript-follow-scroll.js`，按全局/CommonJS 双导出模式实现纯目标计算和 `createController()`；先覆盖去重、reset/destroy、reduced-motion 与连接状态校验。
3. 把目标计算、帧状态和跟随 key 从 `web/app.js` 移出；在活动行切换后调用控制器，并在列表重渲染、无活动行和 `follow: false` 路径集中 reset。此步只建立等价模块边界，先运行聚焦契约测试。
4. 在独立模块中实现同步 `scrollTop + transform` 的可取消 RAF 动画、尾部剩余距离插值和用户滚动意图取消；在 `web/styles.css` 添加不透明的 `is-follow-animating` 提升层。
5. 更新 `web/index.html` 的新脚本加载顺序和 `app.js` 版本，更新 `server/app.py` 无缓存清单；修改静态契约测试，明确断言跟随实现不再位于 `app.js`。
6. 重写现有跟随滚动 Node 回归，使其直接加载新模块并逐帧验证中段固定、尾部下移、max clamp、重复 key、切换目标、重渲染清理、用户中断和 reduced-motion。
7. 运行聚焦前端契约测试、完整 pytest 和 `git diff --check`；确认生产分支指针与生产服务未变化。
8. 重启 `127.0.0.1:8001` 的开发服务，使用浏览器分别在桌面和 375px 播放跨多行普通/已删除文案，检查动画、尾部、手动滚动、横向溢出和控制台。
9. 将新的模块所有权、取消语义和测试入口写入前端 architecture/UI spec，派发 `trellis-check` 做独立规范与回归检查。

## Validation Commands

```powershell
node -e "const api = require('./web/transcript-follow-scroll.js'); console.log(Object.keys(api))"
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_frontend_contracts.py -k "transcript_follow_scroll or shared_frontend_assets"
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
git diff --exit-code master -- server web tests/app/test_frontend_contracts.py
```

最后一条命令仅用于展示开发分支相对生产分支的预期差异，不能据此修改、合并或推送 `master`。另行记录 `git rev-parse master origin/master`，前后必须一致。

## Risk And Rollback Points

- 第 3 步是行为保持型拆分检查点；若独立模块加载或 reset 集成失败，先修正边界，不进入动画改造。
- RAF 测试必须使用可控时间戳，不能依赖真实等待或浏览器 native smooth scroll。
- 不能让 `app.js` 保留同名 fallback 实现，否则页面表面可用但实际仍运行拆分前代码。
- 任一取消路径残留 transform/class 都应视为失败，不通过延长动画或隐藏溢出来规避。
- 不修改 `master`、`origin/master`、生产端口或生产进程；开发服务只从当前 `develop` 工作区重启。
