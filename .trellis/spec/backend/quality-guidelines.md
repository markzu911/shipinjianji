# 后端质量规则

## 不变量

- 所有时间区间必须满足有限数值、`0 <= start < end <= duration`；归一化后再进入渲染。
- 文字删除语义时间与物理音频切点分开：ASR 时间标识内容，实际切点可由低能量谷值吸附。不得用媒体吸附结果反写用户选择的文字语义。
- 原视频、剪辑视频、艺术字视频和统一合成必须明确所用时间轴；跨源转换复用既有 `timeline_after_deletions`、retained transcript 和 source-anchor 逻辑。
- 所有媒体输出先写 `*.tmp.*`，成功后 `Path.replace` 到最终路径。
- `JOBS`、manifest 和库目录的复合读改写必须持有对应锁。
- 清理只处理验证过的 UUID job 目录，并再次确认解析后的父目录是 `data/jobs`。

## API 变更

- 先修改 Pydantic 模型和归一化函数，再修改后台任务与前端消费者。
- 保持已有字段兼容；删除或改名必须带迁移/兼容读取和测试。
- 文件响应要验证目标存在并位于预期目录，不接受浏览器传入任意文件路径。

## 媒体处理

- 使用 `get_ffmpeg_binary` 解析 FFmpeg/FFprobe；不要散落硬编码可执行路径。
- 使用参数列表调用子进程，不拼接 shell 命令字符串。
- 长艺术字命令沿用 filter script/短相对路径方案，避免 Windows 命令行长度限制。
- 生成函数必须支持取消检查，并在完成前再次确认任务未取消。

## 变更验证

- 后端或 API：运行 `\.venv\Scripts\python.exe -m pytest -q`。
- 只改特定纯函数时可先跑对应 `-k` 用例，但交付前仍需完整测试。
- 涉及 FFmpeg 的逻辑必须至少有一个真实 1 秒媒体样片测试，外部 AI 请求继续 monkeypatch，避免费用和网络不确定性。
- 最后运行 `git diff --check`。

参考：`server/app.py` 中 cut boundary 常量与 `render_*`；`tests/app/` 中的剪辑、时间轴、艺术字和画中画功能测试。
