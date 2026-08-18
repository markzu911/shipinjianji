# 项目优化实施计划

## Phase A：可靠性底座（推荐首先实施）

- [ ] 定义 `ProjectDocument v1`、clip/track 类型、revision 规则和迁移契约。
- [ ] 建立原子项目仓库，支持 create/load/save/list/recover 和损坏备份。
- [ ] 服务启动时恢复可继续编辑项目；运行中任务恢复为可解释的 interrupted 状态。
- [ ] 把剪辑草稿、文本修改、艺术字和画中画状态统一写入项目文档。
- [ ] 增加刷新、服务重启、旧项目迁移和 revision 冲突测试。
- [ ] 回滚点：保留现有 `JOBS` 读取适配器和 cut-draft 文件，不删除旧数据。

## Phase B：前端单一状态源

- [ ] 定义 `EditorProjectStore` state、actions、selectors 和 persistence adapter。
- [ ] 先迁移选择、拖动、缩放和播放位置，保持现有 UI 不变。
- [ ] 艺术字 iframe 改为 action producer/state projection consumer。
- [ ] 画中画 iframe 改为 action producer/state projection consumer。
- [ ] 删除 `timelineHtml` 和子页面私有 `generationPayload` 契约。
- [ ] 统一预览、时间轴、保存和 `/compose` payload selectors。
- [ ] 回滚点：每个工具单独 feature flag，逐一切换。

## Phase C：真实工作流测试

- [ ] 增加浏览器测试夹具，可快速恢复一个短视频项目，避免调用外部 AI。
- [ ] 用例 1：删除片段 -> 刷新 -> 剪辑范围和时间戳不变。
- [ ] 用例 2：添加并拖动艺术字/画中画 -> 切换工具 -> 图层和预览不变。
- [ ] 用例 3：统一生成 -> 捕获请求 revision -> 校验输出可下载且历史可恢复。
- [ ] 用例 4：服务重启 -> 项目可重新打开，运行中任务显示 interrupted 与重试操作。
- [ ] 将关键源码字符串断言替换成行为断言；只保留资源版本和静态安全约束检查。

## Phase D：渐进式拆分与运行质量

- [ ] 先提取 project repository，再提取 timeline/composition/media 服务。
- [ ] API 路由只保留请求校验、权限边界和响应映射。
- [ ] 增加单机渲染队列、并发上限、取消和超时状态机。
- [ ] 增加 JSON 结构化日志和诊断导出，禁止记录 API key 与完整用户文案。
- [ ] 将 CSS 按 tokens/base/workspace/art/pip/responsive 拆分，保持现有加载顺序。
- [ ] 前端脚本按 store、selectors、views、effects 和 API client 拆分。

## Phase E：产品化 UX 与性能

- [ ] 更新首页定位和导航信息架构，移除过时 MVP 标签。
- [ ] 增加全局保存状态、失败重试和离开保护。
- [ ] 统一错误反馈为“发生了什么、哪些内容保留、下一步怎么做”。
- [ ] 修正小于 44px 的导航点击目标，补齐拖动的键盘操作和焦点状态。
- [ ] 采集时间轴长项目的帧耗时、DOM 数和内存基线，再决定虚拟化与缩略图缓存范围。
- [ ] 增加磁盘占用、预计导出空间和安全清理入口。

## Validation Gates

- 基线：`pytest tests/test_app.py tests/test_build_mac_package.py -q`。
- 每阶段执行完整 Python 测试、JS 语法检查和 `git diff --check`。
- ProjectDocument 必须通过保存、加载、迁移、损坏恢复和 revision 冲突测试。
- 浏览器在桌面和 375px 窄屏验证，无横向溢出、遮挡或不可达操作。
- 一条包含剪辑、艺术字和画中画的短视频真实生成，预览与成品逐项对照。
- 任何拆分提交不得同时改变用户可见行为；行为改动必须独立提交和验收。

## Estimated Effort

| 阶段 | 预计工作量 | 风险 |
| --- | --- | --- |
| A 项目持久化 | 4-6 天 | 高，涉及数据迁移与恢复 |
| B 单一状态源 | 5-8 天 | 高，需逐工具切换 |
| C 端到端测试 | 2-4 天 | 中，需要稳定媒体夹具 |
| D 模块拆分/队列/日志 | 5-8 天 | 中，必须行为不变 |
| E UX/性能 | 3-5 天 | 低到中，取决于性能实测 |

建议拆为独立子任务逐阶段实施，不在一个分支完成全部工作。
