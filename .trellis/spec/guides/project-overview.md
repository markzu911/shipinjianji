# 项目总览

## 产品

这是面向中文口播视频的本地 Web 编辑器，核心流程是上传视频、在线语音识别、按文字删减、艺术字、AI 画中画、统一预览、生成与历史复用。当前产品事实以 `README.md` 和实际代码/测试为准；`01-产品需求文档-PRD.md`、`02-技术开发文档.md`、`03-功能完善建议.md` 包含愿景和历史设计，不能替代现状核对。

## 技术栈

- Python 3.11/3.12、FastAPI、Uvicorn、Pydantic；
- 原生 HTML/CSS/JavaScript，无 npm、打包器或前端框架；
- FFmpeg/FFprobe、Pillow；
- DashScope ASR/文本/多模态，火山方舟 Seedream/Seedance；
- pytest + FastAPI `TestClient`，真实 FFmpeg 样片与外部服务 monkeypatch。

## 目录

- `server/app.py`：API、后台任务、持久化、AI 和媒体处理。
- `web/`：主页面、编辑器协调层、艺术字/画中画 iframe、设置和素材库。
- `tests/app/`：按功能拆分的主要行为回归；`tests/test_build_mac_package.py`：打包数据隔离。
- `tools/build_mac_package.py`：Mac 可分发压缩包和启动脚本。
- `data/jobs/`：临时任务；`data/history/`：最终历史；其他 `data/*`：字体、模板和预设 manifest。
- `.env`：本机秘密和模型配置；`.env.example`：无秘密的配置契约。

## 运行

Windows 开发使用 `start.ps1`，默认 `http://127.0.0.1:8001`，热重载。Mac 包默认端口 8003 且不启用 reload。健康检查是 `GET /api/health`。

## 核心约束

- 当前 job 状态主要在内存，服务重启后任务记录丢失；cut draft 和 history 只有部分持久化能力。
- API Key 只能存在服务端 `.env`，不得写入 `web/`、日志、测试 fixture 或 Git。
- 源时间和剪后时间必须明确转换；文字语义范围与物理音频吸附边界不能混淆。
- 预览和最终导出必须共享归一化数据契约。
- 工作区经常有未提交的产品修改；只改任务需要的文件，不清理或回退用户改动。

## 规范导航

- 后端/API/媒体：`../backend/index.md`
- 浏览器编辑器：`../frontend/index.md`
- 测试：`../testing/index.md`
- 配置、启动与打包：`../operations/index.md`
