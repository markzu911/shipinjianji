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

### 3.2 EditorProjectStore 与结构化消息

复用 `timeline-model.js`，让顶层 store 逐步拥有项目轨道、选择和播放状态。iframe 暂时保留，但只交换结构化 projection 和语义 action。

迁移顺序：

1. 先用已有 `timeline` 数据替换 `timelineHtml`；
2. 再把私有 `generationPayload` 替换为由顶层 selector 派生的 compose payload；
3. 最后统一 selection、playback 和 persistence adapter。

每种工具独立切换，保留旧消息适配器；不一次性替换四个 store。

### 3.3 后端领域模块

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
3. 用结构化 timeline projection 替换 HTML 快照，保证预览和 compose 使用同一数据模型。

### P1 可维护性与运行质量

1. 继续按 project/timeline/composition/media 拆分 `server/app.py`。
2. 统一任务状态机、并发上限、取消和超时；避免路由直接散改 `JOBS` 嵌套字段。
3. 增加结构化日志、磁盘空间预检、项目占用统计和安全清理入口。
4. 将前端页面内部状态逐步收敛到 store、selectors、views 和 effects 边界。

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
- 前端每个工具单独 feature flag，旧 `timelineHtml`/`generationPayload` 适配器在对应行为测试通过前不删除。
- `/compose` 的公开 API 保持兼容，内部逐步改为消费指定 project revision。
- 每项模块提取均要求完整测试和 OpenAPI 契约不变；发生行为差异时立即回滚该单项，不连带撤销其他已验证拆分。
