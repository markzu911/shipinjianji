# 项目优化技术设计

## 1. 审计结论

项目需要重构，但不需要重写。当前功能、测试速度和最近三次独立拆分说明系统仍具备良好的渐进演进能力；真正需要处理的是权威状态不持久、跨 iframe 契约包含 DOM/私有载荷，以及单文件同时拥有过多高风险职责。

“文件很大”是维护成本信号，不是首要故障。优先级必须由用户成果是否可能丢失、预览与导出是否可能漂移、以及现有测试能否捕获回归决定。

### 当前证据

| 维度 | 当前证据 | 判断 |
| --- | --- | --- |
| 自动化基线 | 完整测试 `178 passed, 1 warning in 8.18s`；所有 JS 通过语法检查 | 后端与纯逻辑重构有较好底座 |
| 浏览器保护 | `test_frontend_contracts.py` 主要是静态契约，只有 5 组 Node 脚本；没有真实浏览器工具 | 不能先做跨 iframe 大迁移 |
| 后端集中度 | `server/app.py` 11,734 行、60 路由、261 函数；25 个函数跨度超过 100 行 | 路由、状态、I/O 与媒体领域耦合 |
| 持久化 | `server/app.py:329-330` 的 `JOBS`/`JOB_FILES` 是权威状态；`app_lifespan` 只清理、不恢复 | 服务重启后项目不可继续编辑 |
| 草稿可达性 | `server/app.py:10313-10322` 读取磁盘草稿前先要求内存 job 存在 | 已落盘数据仍受进程状态阻断 |
| 合成边界 | `create_preview_composition` 同时读取全局状态、校验时间轴、归一化 overlay、构造四类子状态并调度任务 | 适合拆成用例服务与路由适配器 |
| 前端状态 | 四个页面各自创建 timeline store；共 19 类 `editor-suite:*` 消息 | 同一编辑工程存在多份状态投影 |
| DOM 契约 | `art-text.js:2917`、`picture-in-picture.js:1155` 发布 `timelineHtml`，`editor-suite.js:900-920` 再解析 | DOM 结构变化可能破坏数据流 |
| 生成载荷 | `art-text.js:2930`、`picture-in-picture.js:1168` 发布私有载荷，顶层在 `editor-suite.js:354-364` 拼装 | 预览与导出缺少单一派生源 |
| 存储规模 | `data/jobs` 约 3.09 GB，`data/history` 约 0.239 GB | 需要项目生命周期和空间策略 |

## 2. 当前数据流与所有权

```text
上传视频
  -> FastAPI 写 data/jobs/<job_id>
  -> JOBS/JOB_FILES（服务端权威，但只在内存）
  -> ASR 结果 + cut-draft.json（局部持久化）
  -> app.js cutTimelineStore + 页面状态
  -> editor-suite.js 顶层 timelineStore/toolStates
      <- art-text.js artTimelineStore + sessionStorage + HTML/payload 快照
      <- picture-in-picture.js pipTimelineStore + sessionStorage + HTML/payload 快照
  -> /compose 路由再次归一化并写回 JOBS 子状态
  -> 后台 FFmpeg 分阶段生成
  -> composition.mp4 + data/history manifest
```

当前没有一个对象同时满足“跨重启可恢复、包含全部编辑轨道、可作为预览和导出的同一输入”。这就是结构性重构的核心理由。

## 3. 目标边界

### 3.1 ProjectRepository 与版本化 ProjectDocument

先给现有 job 字典建立仓库接口和原子 JSON 快照，保持字段形状与 API 不变；验证恢复流程后，再收敛为明确的 `ProjectDocument v1`。不要在第一步同时重新设计所有状态。

最小持久字段：

- `schemaVersion`、`projectId/jobId`、`revision`、`updatedAt`；
- 源视频相对引用、时长、转写结果和可编辑分段；
- 剪辑草稿、艺术字轨道、画中画轨道及资源稳定 ID；
- 最近一次生成请求、各子任务终态和历史版本引用。

运行中任务在重启后统一恢复为 `interrupted`，已完成/失败状态保持可解释；媒体继续保存在现有目录，不引入数据库。

### 3.2 单文档 EditorProjectStore

最终编辑器只运行在 `index.html` 这一份顶层文档中。复用 `timeline-model.js`，由 `EditorProjectStore` 唯一拥有当前 project revision、transcript、cut、art、pip、选择和工具状态；唯一 `MediaController` 拥有基础视频、播放位置和播放帧时钟；唯一 `TimelineController` 拥有全部轨道。艺术字与画中画不再是页面，而是挂载到 `InspectorHost` 的功能模块。

```text
EditorProjectStore
  -> selectors.editedTranscript
  -> selectors.timelineDocument
  -> selectors.previewLayers
  -> selectors.composePayload

MediaController -> one <video> + one playback clock
PreviewCompositor <- art/pip layer models
InspectorHost <- CutTool / ArtTool / PipTool
```

store 分为两类状态：

- 持久项目状态：`revision`、transcript、cut ranges、art overlays、pip items、源媒体信息；
- 临时 UI 状态：active tool、selection、busy/error、panel focus；播放时间仍由唯一 video/controller 拥有并投影给 store 订阅者。

所有修改以语义 action 进入同一入口。`transcriptTextChanged` 与 `timingChanged` 必须分离：前者只换文字和字符映射，既有艺术字 cue 时间不变；只有 cut/art/pip 的明确时间 action 才能改变时间结构。API 成功后应用同一 revision 的规范化 snapshot，迟到响应不得覆盖新 revision。

### 3.3 同页功能模块与公共服务

保持原生 JavaScript 和无构建步骤。新增脚本继续通过 `<script defer>` 按顺序加载并使用唯一 `window` 命名空间：

- `editor-project-store.js`：state、commands、revision guard、selectors；
- `editor-media-controller.js`：唯一 video、播放帧时钟、seek/play/pause；
- `editor-preview-compositor.js`：直接消费 overlay model，不接收 HTML；
- `editor-timeline-controller.js`：统一轨道、选择、拖动、缩放与历史；
- `cut-tool.js`、`art-tool.js`、`pip-tool.js`：只负责各自 inspector view/controller。

工具模块统一暴露 `mount(root, services)`、`activate()`、`deactivate()` 和 `destroy()`。现有 `art-text.js` 与 `picture-in-picture.js` 不能直接加载到主页面，因为它们有顶层 DOM 查询、独立初始化、独立 video/store 和 sessionStorage 副作用；迁移时先把纯逻辑、renderer 和 view controller 提取到可注入服务的模块，再由旧页面适配器和新主页面分别调用。

### 3.4 过渡期兼容边界

iframe 只在迁移期保留，不是目标架构。顺序如下：

1. 顶层先建立 `EditorProjectStore`，旧 iframe bridge 只负责把 store projection 转成旧消息；
2. 公共 preview/timeline/compose 全部改为直接消费顶层 selectors；
3. 艺术字面板迁入顶层，单独关闭 art iframe feature flag；
4. 画中画面板迁入顶层，单独关闭 pip iframe feature flag；
5. 删除 `embedded=1`、`postMessage`、`timelineHtml`、`overlayHtml`、私有 `generationPayload` 和 iframe 生命周期代码。

旧 `/art-text`、`/picture-in-picture` URL 最终改为 `/?job=<id>&tool=art|pip` 跳转，从而保留历史链接但不保留第二套编辑运行时；用户已于 2026-08-18 确认该兼容策略。

### 3.5 后端领域模块

保持 FastAPI 单体和当前部署方式。按被测试覆盖的领域逐个提取：

- `project_repository.py`：job/project 快照、revision、恢复和迁移；
- `timeline_service.py`：删除区间、源时间/剪后时间和 transcript 映射；
- `composition_service.py`：compose 用例、渲染计划和状态转换；
- `media_service.py`：FFmpeg 进程、取消、超时和临时输出；
- 后续再拆资源库与 API routes。

`server.app` 保留兼容导入或薄适配函数；每次只迁移一个领域，不同时修改 API 和用户行为。

## 4. 优先级

### P0 变更安全与成果可靠性

1. 建立真实浏览器行为基线：刷新恢复、文字剪辑后跨艺术字/画中画切换、统一生成与下载。
2. 引入 ProjectRepository/ProjectDocument 的最小持久化与启动恢复，消除“磁盘有数据但 API 不可达”。
3. 建立单文档 `EditorProjectStore` 和统一 revision/action/selectors 契约，先由 bridge 适配旧 iframe。
4. 让公共预览、统一时间轴和 compose 使用同一 selectors，随后逐个迁入艺术字与画中画面板。

### P1 可维护性与运行质量

1. 继续按 project/timeline/composition/media 拆分 `server/app.py`。
2. 统一任务状态机、并发上限、取消和超时；避免路由直接散改 `JOBS` 嵌套字段。
3. 增加结构化日志、磁盘空间预检、项目占用统计和安全清理入口。
4. 将前端状态收敛到 store、selectors、views 和 effects 边界，并最终删除编辑工具 iframe 和跨页状态协议。

### P2 整洁度、体验与性能

1. 在有浏览器回归和稳定加载顺序后拆分 `styles.css`；不以行数为单独验收指标。
2. 加入保存状态、失败重试、离开保护和可恢复错误反馈。
3. 先采集长时间轴帧耗时、DOM 数与内存，再决定虚拟化、缓存和节流范围。
4. 补齐拖动的键盘替代、焦点顺序和点击目标尺寸。

## 5. 明确不做

- 不更换前端框架或引入构建系统来掩盖状态边界问题。
- 不拆微服务，不引入云数据库、分布式队列或多人协作模型。
- 不先做全量目录重排、批量重命名或通用基类抽象。
- 不把 CSS/JS 拆文件与功能改动放在同一提交。
- 不重写已经独立且有契约测试的 `schemas.py` 和 `history_repository.py`。

## 6. 兼容与回滚

- 每个新仓库写入先保留旧读取路径，使用临时文件替换、revision 和最近一版备份。
- 旧 job 首次打开时惰性生成版本化文档；迁移失败继续只读旧数据并给出明确恢复动作。
- 前端每个工具单独 feature flag，旧 `timelineHtml`/`generationPayload`/message bridge 在对应行为测试通过前不删除；两个工具都迁入顶层后统一删除 iframe 资源。
- `/compose` 的公开 API 保持兼容，内部逐步改为消费指定 project revision。
- 每项模块提取均要求完整测试和 OpenAPI 契约不变；发生行为差异时立即回滚该单项，不连带撤销其他已验证拆分。
