# 后端规范索引

后端是 FastAPI 单体，核心实现位于 `server/app.py`，通过 FFmpeg/FFprobe 和在线 AI 服务完成媒体链路。

| 文档 | 适用范围 |
| --- | --- |
| [后端架构与目录](./directory-structure.md) | 当前模块边界、放置规则和渐进拆分原则 |
| [持久化与任务状态](./persistence-and-jobs.md) | 内存 job、JSON manifest、锁、清理和历史文件 |
| [媒体与时间轴](./media-and-timeline.md) | FFmpeg、源时间/剪后时间、临时输出和取消 |
| [错误处理](./error-handling.md) | HTTP、后台任务、外部服务与清理失败 |
| [日志与诊断](./logging-guidelines.md) | 当前诊断能力和安全日志约束 |
| [后端质量规则](./quality-guidelines.md) | 不变量、API 兼容与验证命令 |

开始后端修改前，同时阅读 `../guides/project-overview.md` 和 `../guides/cross-layer-thinking-guide.md`。
