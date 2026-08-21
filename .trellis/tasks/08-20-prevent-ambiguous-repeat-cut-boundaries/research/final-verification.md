# 最终验证证据

## 真实 Resolver

- 只读媒体：`data/jobs/ac6169d9-1c7c-4e31-a83b-eacb7493d352/source.mp4`
- 只读 job 导出：`C:\Users\jiadi\AppData\Local\Temp\codex-residual-audio-20260820\job.json`
- “觉得 / 你”完整重复上下文：semantic fallback `37.120s`，forced candidate/final `37.790s`，retained hard limit `39.850s`，`trustReason=forced_pcm_gap`。
- “所以说啊 / 所以说啊”：semantic fallback `141.156s`，错误 forced candidate `142.030s`，final `141.814s`，PCM retained hard limit `141.825s`，`trustReason=forced_pcm_valley`。

## 完整成片

- 临时输出：`C:\Users\jiadi\AppData\Local\Temp\codex-repeat-cut-fixed-20260821\fixed-full-v2.mp4`
- SHA256：`77295E398F14B181124EA33A3523C7137BAC1F5F1AE5C2104E488D35F415A2E5`
- 时长：`143.800s`
- “得/你”下一保留起音源/成片最大相关性 `0.9977`，lag `19.0ms`；删除后 `1.8s` 静音 RMS `38.78`，被删尾音窗口 RMS `2745.66`，能量比 `0.0141`。
- 第二次“所以说啊”保留起音源/成片最大相关性 `0.9781`，lag `39.38ms`；前一次删除尾部的局部指纹未在拼接后窗口复现。
- 人工听感仍由用户验收，不用自动相关性替代主观听音结论。

## 自动化

- 聚焦声学/草稿/渲染/组合/前端契约：`139 passed, 1 deselected`。
- 真实浏览器：`28 passed, 1 xfailed`。
- 全量排除两个既有 TestClient/后台生命周期挂起用例：`322 passed, 2 deselected, 1 xfailed`。
- 排除用例：`test_cut_endpoint_renders_preview_video`、`test_upload_extracts_audio_and_returns_transcript`；两者无 FFmpeg 或外部请求子进程，属于既有测试生命周期问题。
- 最终检查代理：声学边界与前端契约通过，`compileall`、`node --check web/app.js`、`git diff --check` 通过。
