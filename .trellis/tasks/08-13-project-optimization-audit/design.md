# 项目优化技术设计

## 1. 审计结论

项目当前功能覆盖已经较完整，133 个测试均通过，因此不建议重写技术栈。主要风险来自状态和职责分散，而不是缺少功能。

### 证据摘要

| 证据 | 影响 |
| --- | --- |
| `server/app.py:290-292` 以 `JOBS`、`JOB_FILES` 进程内字典保存任务主体 | 服务重启后无法完整恢复编辑任务 |
| `server/app.py:9735-9739` 等大量接口明确返回“任务不存在或服务已重启” | 用户刷新或重启服务后可能失去继续编辑上下文 |
| `server/app.py:636` 仅剪辑草稿独立原子持久化 | 艺术字、画中画、当前选择和生成请求没有同等级持久化契约 |
| `web/editor-suite.js:356-364` 从子页面 `generationPayload` 拼装最终生成载荷 | 顶层不是所有编辑状态的唯一所有者 |
| `web/art-text.js:2893`、`web/picture-in-picture.js:1168` 各自发布图层快照 | 刷新、异步回填或消息顺序变化容易覆盖新状态 |
| `web/art-text.js:2880`、`web/picture-in-picture.js:1155` 发布时间轴 HTML，顶层在 `web/editor-suite.js:899-920` 再解析 | DOM 被当作数据契约，难以验证且容易漂移 |
| `tests/test_app.py:678` 起存在大量源码字符串断言 | 能证明代码文本存在，不能证明真实页面交互和状态回放正确 |
| `tests/test_app.py:4914` 已覆盖统一合成后端 | 后端合成基线较好，缺口主要在浏览器工作流和重启恢复 |
| `server/app.py` 约 10,302 行，`web/styles.css` 约 12,181 行 | 改动影响面难判断，局部修复容易触发跨功能回归 |
| `data/jobs` 当前约 0.452 GB，历史约 0.081 GB | 媒体资源需要明确的生命周期、空间提示和恢复策略 |

## 2. 当前数据流

```text
上传视频
  -> FastAPI JOBS/JOB_FILES
  -> 识别结果与剪辑草稿
  -> app.js 文字剪辑状态
  -> EditorSuite 顶层聚合
      <- art-text iframe 图层/时间轴 HTML/生成载荷
      <- picture-in-picture iframe 图层/时间轴 HTML/生成载荷
  -> /compose 统一请求
  -> FFmpeg 分阶段渲染
  -> composition.mp4 + history manifest
```

问题不在 `/compose` 是否统一，而在统一请求之前存在多个状态所有者，且完整项目状态没有稳定持久化。

## 3. 目标边界

### 3.1 ProjectDocument 成为唯一持久化项目状态

新增版本化项目文档，最小字段包括：

- `schemaVersion`、`projectId`、`revision`、`updatedAt`
- 源视频标识、时长和识别结果版本
- 剪辑删除区间与文本修改
- 艺术字轨道和每个 clip 的完整参数
- 画中画轨道、素材引用和每个 clip 的完整参数
- 当前选择、播放位置等可选工作区状态
- 最近一次统一生成请求和输出历史引用

单机 MVP 推荐先使用原子 JSON 文档加 revision 并发控制，沿用现有 cut draft 的临时文件替换模式；不引入数据库和分布式队列。媒体文件仍按目录保存，项目文档只保存稳定 ID 和相对引用。

### 3.2 EditorProjectStore 成为前端唯一状态源

扩展现有 `timeline-model.js` 的 store 思路，由顶层持有剪辑、艺术字、画中画和选择状态。子页面短期可保留 iframe，但只接收 state projection 并发送语义 action，例如：

- `clip/add`
- `clip/move`
- `clip/resize`
- `clip/update-style`
- `selection/change`
- `playback/seek`

不再把 `innerHTML` 或整份私有 generation payload 作为跨页面数据契约。预览和 `/compose` 载荷都由同一 store 派生。

### 3.3 后端按职责拆分但保持单体部署

保持 FastAPI 和本地部署，不做微服务化。逐步提取：

- `project_repository`：项目文档、revision、迁移和原子保存
- `timeline_service`：源时间与剪后时间映射、clip 归一化
- `composition_service`：统一渲染计划和输出状态
- `media_service`：FFmpeg 执行、取消、超时和资源清理
- `api/routes`：请求校验与响应映射

迁移期旧函数保留薄适配层，每次只移动一个领域并运行现有测试。

## 4. 优先级路线

### P0 可靠性底座

1. 完整 ProjectDocument 持久化和服务启动恢复。
2. 顶层 EditorProjectStore 与 action 协议，消除 HTML 快照作为状态契约。
3. 三条真实浏览器回归：刷新恢复、跨工具编辑、统一生成与下载。

### P1 可维护性与运行质量

1. 按项目仓库、时间轴、合成、媒体和 API 逐步拆分 `server/app.py`。
2. 按基础 tokens、编辑工作台、艺术字、画中画和响应式拆分 `styles.css` 与前端脚本。
3. 建立本地渲染队列和并发上限，统一 queued/running/cancelled/failed/completed 状态机。
4. 增加结构化日志：projectId、jobId、阶段、耗时、FFmpeg 返回码和可恢复建议。
5. 增加磁盘空间预检、项目占用统计和可理解的清理界面。

### P2 产品化体验

1. 去掉首页 `MVP · 文字粗剪`，统一定位为完整视频编辑工作台。
2. 在工作台持续显示“已保存/保存中/保存失败”，离开前处理未保存修改。
3. 把图层、时间轴、生成错误改成包含原因和恢复动作的就地反馈。
4. 补齐拖动操作的键盘替代、焦点顺序和不小于 44px 的点击区域。
5. 对长时间轴缩略图和图层列表做缓存、节流和按需渲染，性能指标确认后再优化。

## 5. 兼容与迁移

- 首次打开旧任务时，从现有 job、cut draft、art 和 picture-in-picture 字段构造 `schemaVersion: 1` 项目文档。
- 每次迁移先备份原文档，迁移失败继续使用旧读取路径并给出可恢复错误。
- `/compose` 保持现有 API 兼容，内部逐步改为只消费 ProjectDocument 的确定 revision。
- 历史成品保持只读，不随项目状态迁移而重写。

## 6. 回滚策略

- 每一阶段都通过 feature flag 或旧适配器保留原读取路径。
- ProjectDocument 写入使用 revision 和原子替换，保存前保留最近一版备份。
- 前端 store 迁移按剪辑、艺术字、画中画依次切换，禁止一次性替换三条链路。
- 文件拆分只在对应领域行为测试齐全后进行，不与功能改动混在同一提交。

## 7. 暂缓项

- 不更换前端框架。
- 不拆微服务。
- 不引入云端数据库或多人协作。
- 不在可靠性底座完成前继续扩展更多预览平台或 AI 编辑功能。
