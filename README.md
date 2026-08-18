# AI 口播视频剪辑 Web MVP

当前 MVP 已打通上传转写、可选文字剪辑、艺术字和 AI 画中画流程。文字识别完成后，用户可以直接基于原视频添加艺术字或画中画，不要求先剪辑；也可以继续使用剪辑版或艺术字版视频。

## 已实现

- MP4、MOV、MKV、WebM 上传，最大文件大小默认 1GB。
- FFprobe 视频有效性检查。
- FFmpeg 提取 16kHz 单声道 MP3，减少在线传输体积。
- 阿里云百炼 `paraformer-realtime-v2` 中文识别，返回全文、段落和词级时间戳。
- Paraformer 语义断句 + `qwen-plus` 标点校对；只允许调整标点，正文字符变化时自动回退。
- 使用 Jieba 将 Paraformer 的机械时间块重新切成自然中文词语，并映射回原始时间轴。
- `qwen3.7-max` 自动初筛口误、重复、语气词和无效片段；只给出建议，由用户确认后才标记删除。
- 上传进度、音频提取、语音识别、成功和失败状态。
- 转写全文编辑、复制、TXT 下载和分段查看。
- 按词选择或一键选择整段文字，红色删除态实时标明待删除内容。
- 自动合并相邻时间区间，使用 FFmpeg 截取并拼接保留的视频片段。
- 剪辑任务进度、成片在线预览和 MP4 下载；每次生成新文件，不覆盖原视频。
- 支持手动添加多条艺术字并分别调整模板、排版、位置和显示时间。
- 支持将全文生成一条逻辑艺术字轨道：服务端按词级时间戳自动切成不重叠的单行片段，前端只需设置一次样式和位置，预览与导出共用同一组片段数据。
- 艺术字效果模板库支持上传 `.json`/`.arttext` 效果模板、修改模板名称和删除我的模板；上传的是可编辑效果参数，不是 TTF/OTF 字体。
- 转写完成页提供“直接添加艺术字”和“直接插入画中画”，两个功能均可跳过视频剪辑并使用原视频时间轴。
- AI 结合口播时间轴与低清关键帧拼图，按用户输入的数量生成艺术字草稿；用户可逐条修改、取消或确认，确认前不会写入艺术字列表。
- 可直接从原视频、剪辑视频或艺术字视频中选择任意口播文字片段，在对应时长插入 AI 画中画；支持输入画面描述，或由 AI 根据所选文字自动构思。
- 画中画支持图片和动态视频两种素材：图片使用 Seedream 5.0 Lite，视频使用 Seedance；两者都支持自定义提示词或根据所选文案智能生成，生成后可实时预览并分别调整位置与大小，用户确认后才合成最终视频。
- Chrome/Edge 桌面与窄屏响应式界面。

当前任务状态保存在内存中，服务重启后任务记录会清空。最终成片成功保存或任务进入终态失败后，`data/jobs/` 中的工作目录会立即删除；未完成任务由启动清理和定时清理按保留策略回收。

## 本地启动

需要 Python 3.11/3.12、FFmpeg 和一个在线语音识别 API Key。不再下载本地模型。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# 编辑 .env，填写 DASHSCOPE_API_KEY
.\start.ps1
```

打开 <http://127.0.0.1:8001>。

启动后也可以打开 <http://127.0.0.1:8001/settings> 修改各功能使用的模型名称、服务商请求地址和 API Key。配置保存后即时生效，通过局域网访问应用的设备也可以修改。

如果系统中的 `python` 不可用，可使用 Codex 工作区 Python 创建虚拟环境：

```powershell
& 'C:\Users\jiadi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m venv .venv
```

## 配置

应用启动时会自动读取项目根目录的 `.env`。常用配置：

- `DASHSCOPE_API_KEY`：阿里云百炼 API Key；程序也兼容原有的 `ASR_API_KEY` 变量名。
- `DASHSCOPE_HTTP_API_URL=https://dashscope.aliyuncs.com/api/v1`：百炼文本与多模态模型的 HTTP 请求地址。
- `ASR_MODEL=paraformer-realtime-v2`：直接识别本地音频，启用时间戳校准并返回句子和词级毫秒时间戳。
- `PUNCTUATION_MODEL=qwen-plus`：对连续口播执行二次标点和断句校对。
- `SUGGESTION_MODEL=qwen3.7-max`：分析疑似口误并返回带词级索引的结构化删减建议。
- `ART_SUGGESTION_MODEL=qwen3.6-flash`：结合关键帧和时间轴生成待确认的艺术字草稿。
- `ART_TEXT_SEGMENTATION_MODEL=qwen-plus`：按语义将全文切分为艺术字单行片段。
- `PIP_PROMPT_MODEL=qwen-plus`：为画中画素材编写提示词，与口误分析模型独立配置。
- `ARK_API_KEY`：火山方舟 API Key，供 Seedream 生图和 Seedance 视频生成共同使用。
- `SEEDREAM_MODEL=doubao-seedream-5-0-lite-260128`：Seedream 图片生成模型，可替换为当前账号已开通的兼容模型 ID。
- `SEEDANCE_MODEL=doubao-seedance-2-0-260128`：Seedance 2.0 视频生成模型，可替换为当前账号已开通的兼容模型 ID。
- `ARK_API_BASE_URL=https://ark.cn-beijing.volces.com/api/v3`：火山方舟图片和视频生成 API 地址。
- `DASHSCOPE_WEBSOCKET_URL`：百炼 WebSocket 接口；有业务空间专属域名时可替换。
- `MAX_UPLOAD_MB=1024`：上传大小限制。
- `JOB_RETENTION_DAYS=7`：临时任务目录保留天数；只影响 `data/jobs/`，不会删除剪辑历史。
- `JOB_MAX_STORED=80`：最多保留多少个非活跃临时任务目录；设为 `0` 时关闭数量上限清理。
- `JOB_CLEANUP_INTERVAL_SECONDS=21600`：服务运行期间自动清理临时任务的间隔，默认每 6 小时执行一次；设为 `0` 时关闭定时清理。
- `HISTORY_MAX_STORED=20`：剪辑历史最多保留最新 20 条，超出后自动删除最旧记录及其文件；设为 `0` 时关闭历史数量上限。
- `DATA_DIR=./data`：视频和提取音频的保存目录。

API Key 只配置在服务端 `.env`，不要写入 `web/` 下的浏览器代码，也不要提交到 Git。

## 临时任务清理

`data/jobs/` 保存上传源视频、提取音频和生成中的临时文件。服务会在启动时立即清理一次，并在运行期间按 `JOB_CLEANUP_INTERVAL_SECONDS` 定时清理。也可以先预览再手动执行：

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/maintenance/jobs
Invoke-RestMethod http://127.0.0.1:8001/api/maintenance/jobs/cleanup -Method Post -ContentType 'application/json' -Body '{"dryRun":false}'
```

临时任务清理只会处理 UUID 形式的 `data/jobs/` 任务目录，并跳过正在解析或生成的任务。`data/history/` 由独立的 `HISTORY_MAX_STORED` 上限管理，默认只保留最新 20 条。

## 艺术字效果模板文件

艺术字模板文件使用 UTF-8 JSON，保存效果类型和配色。可从模板库上传窗口下载示例：

```json
{
  "name": "我的蓝色立体字",
  "sample": "蓝色",
  "description": "蓝色主色与深蓝描边的立体艺术字。",
  "baseStyle": "impact",
  "color": "#59C7FF",
  "strokeColor": "#102A43"
}
```

`baseStyle` 可使用内置效果 ID：`impact`、`neon`、`metal`、`sticker`、`clean`、`gradient`、`comic`、`ice`、`ink`、`ribbon`、`luxury`。上传后模板记录保存在 `data/art-templates/manifest.json`。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

测试会用 FFmpeg 生成一个 1 秒样片，并用模拟在线接口验证“上传—提取音频—返回文字—按时间段剪辑—读取成片”的完整 API 链路，不会产生真实 API 请求或费用。

首次运行真实浏览器工作流测试前，需要安装 Chromium：

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser
```

浏览器测试使用随机本地端口和隔离的临时数据目录，不会连接已启动的 8001 开发服务，也不会调用外部 AI 服务。

## 当前剪辑 API

- `POST /api/transcriptions/{job_id}/cuts`：提交需要删除的 `{start, end}` 时间区间，创建后台剪辑任务。
- `GET /api/transcriptions/{job_id}`：读取转写任务及 `edit` 剪辑进度。
- `PUT /api/transcriptions/{job_id}/transcript`：保存用户修改后的识别全文，自动对齐对应词块并保留原时间戳。
- `PATCH /api/transcriptions/{job_id}/transcript`：按单个词块修正 ASR 文字，供精确编辑和兼容调用使用。
- `GET /api/transcriptions/{job_id}/edited-video`：在线播放剪辑成片；添加 `?download=true` 下载 MP4。
- `POST /api/transcriptions/{job_id}/picture-in-picture/images`：按所选文字时间段和用户描述生成一张画中画图片。
- `POST /api/transcriptions/{job_id}/picture-in-picture/videos`：创建 Seedance 动态画中画生成任务，状态会保存在转写任务的 `pictureInPictureVideos` 中。
- `GET /api/transcriptions/{job_id}/picture-in-picture/videos/{asset_id}`：播放已生成的动态画中画素材。
- `POST /api/transcriptions/{job_id}/picture-in-picture`：提交已确认的图片或视频素材、位置和大小，创建画中画合成任务。
- `GET /api/transcriptions/{job_id}/picture-in-picture-video`：在线播放画中画成片；添加 `?download=true` 下载 MP4。

## 文档

- [MVP 产品需求文档](./01-产品需求文档-PRD.md)
- [MVP 技术开发文档](./02-技术开发文档.md)
