# 项目优化实施计划

父任务只拥有路线、跨阶段契约和最终集成检查。用户批准后，每个阶段创建独立子任务；一次只启动一个可验收交付，不启动父任务做全量实现。

## Phase 0：真实浏览器行为基线

- [ ] 选择并接入稳定浏览器测试工具，使用本地短视频 fixture，不调用外部 AI。
- [ ] 用例 1：删除文字片段 -> 刷新 -> 删除范围、文案和时间戳不变。
- [ ] 用例 2：添加并拖动艺术字与画中画 -> 跨工具切换 -> 图层、选择和公共预览不变。
- [ ] 用例 3：统一生成 -> 校验 compose 请求、生成终态、下载和历史恢复。
- [ ] 用例 4：模拟服务重启 -> 当前行为明确失败；为后续恢复改动保留红灯用例或可切换期望。
- [ ] 保留必要的资源版本和消息安全静态断言；逐步用行为断言替换关键工作流源码字符串断言。
- [ ] 回滚点：测试基础设施与业务代码分开提交，可独立移除。

## Phase A：可恢复项目状态

- [ ] 冻结现有 job 字典的公开投影与 OpenAPI 契约，定义 `ProjectDocument v1`、revision 和 `interrupted` 语义。
- [ ] 提取 `ProjectRepository`，先原样持久化现有 job 快照，支持 create/load/save/list/recover 和损坏备份。
- [ ] 应用启动恢复可继续编辑的项目，验证磁盘草稿不再依赖预先存在的内存 job。
- [ ] 将剪辑草稿、文本修改、艺术字、画中画和最近生成请求纳入版本文档。
- [ ] 增加保存/加载、服务重启、旧 job 迁移、损坏恢复和 revision 冲突测试。
- [ ] 回滚点：保留 `JOBS`/`JOB_FILES` 兼容适配器、原目录和 `cut-draft.json`，不删除旧数据。

## Phase B：结构化前端状态

- [ ] 为顶层 `EditorProjectStore` 定义 state、actions、selectors 和 persistence adapter，复用 `EditorTimeline` 归一化。
- [ ] 先让艺术字和画中画发布结构化 timeline projection，顶层不再解析 `timelineHtml`。
- [ ] 再迁移 selection、move、resize 和 playback action，保持现有 DOM 与 UI 不变。
- [ ] 让预览和 compose payload 由同一 selector 派生，逐步删除子页面私有 `generationPayload`。
- [ ] 按艺术字、画中画两个独立子任务切换，分别运行跨工具浏览器回归。
- [ ] 回滚点：每个工具独立 feature flag 和旧消息适配器，禁止同时切换全部 store。

## Phase C：后端按领域拆分

- [ ] 在 ProjectRepository 稳定后提取 `timeline_service`，迁移删除区间、时间映射和 transcript 纯逻辑。
- [ ] 提取 `composition_service`，让 compose 路由只做请求/响应映射和用例调度。
- [ ] 提取 `media_service`，集中 FFmpeg 进程、临时文件、取消与超时。
- [ ] 统一 job 子状态更新入口，移除路由对 `JOBS[job_id][...]` 的直接散写。
- [ ] 保留 `server.app` 兼容导入；每个模块单独提交、单独跑完整回归和 OpenAPI 稳定检查。
- [ ] 回滚点：旧函数薄适配器保持到所有消费者迁移并通过测试。

## Phase D：运行质量与资源生命周期

- [ ] 建立单机渲染队列、并发上限、取消和超时状态机。
- [ ] 增加 JSON 结构化日志与诊断导出，禁止记录 API key 和完整用户文案。
- [ ] 增加磁盘空间预检、项目/历史占用统计和 dry-run 安全清理入口。
- [ ] 明确项目、临时渲染、最终历史和用户资产的保留策略。

## Phase E：前端文件边界、UX 与性能

- [ ] 在浏览器回归稳定后，按 tokens/base/workspace/art/pip/responsive 拆分 CSS，严格保持加载顺序和层叠结果。
- [ ] 页面脚本按 store/selectors/views/effects/API client 逐页提取，不跨页面一次性改造。
- [ ] 增加全局保存状态、失败重试、离开保护和可恢复错误反馈。
- [ ] 采集长时间轴的帧耗时、DOM 数和内存基线，再决定虚拟化、缩略图缓存与节流范围。
- [ ] 补齐拖动键盘操作、焦点状态和点击目标尺寸。

## Validation Gates

- 完整基线：`.\.venv\Scripts\python.exe -m pytest -q`。
- 前端脚本：对全部 `web/*.js` 执行 `node --check`，再运行桌面与 375px 浏览器工作流。
- ProjectDocument：保存、加载、原子替换、迁移、损坏恢复、revision 冲突和重启恢复全部通过。
- 生成链路：一条包含剪辑、艺术字和画中画的短视频，预览、compose 请求和最终成品逐项一致。
- 结构拆分：OpenAPI path/schema、公开导入、错误状态和历史兼容保持不变。
- 仓库检查：`git diff --check`，不得提交真实 `data/jobs`、`data/history`、缓存或秘密。
- 任何结构拆分不得同时改变用户可见行为；行为变化必须独立规划和验收。

## Estimated Effort

| 阶段 | 预计工作量 | 风险 |
| --- | --- | --- |
| 0 浏览器行为基线 | 2-4 工程日 | 中，需稳定 fixture 与进程控制 |
| A 可恢复项目状态 | 4-7 工程日 | 高，涉及迁移、原子写入与恢复 |
| B 结构化前端状态 | 5-8 工程日 | 高，需逐工具兼容切换 |
| C 后端领域拆分 | 5-9 工程日 | 中，行为保持型分批迁移 |
| D 运行质量与资源 | 3-5 工程日 | 中，涉及队列和清理安全 |
| E 前端边界/UX/性能 | 4-7 工程日 | 低到中，范围由实测决定 |

总路线约 23-40 工程日，应按独立子任务分批交付。第一轮只批准 Phase 0，不应一次批准整条路线的实现。
