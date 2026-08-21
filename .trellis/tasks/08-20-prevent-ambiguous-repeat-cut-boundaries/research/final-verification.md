# 最终验证证据

## 真实 Resolver

- 只读媒体：`data/jobs/ac6169d9-1c7c-4e31-a83b-eacb7493d352/source.mp4`
- 只读 job 导出：`C:\Users\jiadi\AppData\Local\Temp\codex-residual-audio-20260820\job.json`
- “一起给 / 一起给”：semantic fallback/forced candidate `29.171s`，retained hard limit `29.790s`，retained-side terminal gate final `29.789s`，`trustReason=repeat_retained_pcm_valley`。
- “觉得 / 你”完整重复上下文：semantic fallback `37.120s`，forced candidate/final `37.790s`，retained hard limit `39.850s`，`trustReason=forced_pcm_gap`。
- “在另一 / 在另一”：semantic fallback `122.370s`，错误方向 forced candidate `121.728s`，retained hard limit `124.248s`，terminal gate final `124.246s`，真实持续语音约从 `124.29s` 开始。
- “所以说啊 / 所以说啊”：semantic fallback `141.156s`，错误 forced candidate `142.030s`，final `141.814s`，PCM retained hard limit `141.825s`，`trustReason=forced_pcm_valley`。

## 完整成片

- 临时输出：`C:\Users\jiadi\AppData\Local\Temp\codex-repeat-cut-fixed-20260821\fixed-full-v3.mp4`
- SHA256：`61022B1CFD9DC129AC83F89A83B200BC32CFE1D85AD521469276DD6973839994`
- 时长：`142.900s`
- 第一处拼接后的局部 ASR 为“而是你身边所有人一起给你画的那条正常的线。”，只保留一次“一起给”；保留起音窗口与源音频相关性 `0.8591`，lag 约 `12ms`。被额外删除的 `29.171-29.789s` 走廊 RMS `14.15`，hard limit 前最后 `80ms` RMS `11.74`，其后 `300ms` 保留语音 RMS `1514.14`。
- “得/你”下一保留起音源/成片最大相关性 `0.9977`，lag `19.0ms`；删除后 `1.8s` 静音 RMS `38.78`，被删尾音窗口 RMS `2745.66`，能量比 `0.0141`。
- 第二次“所以说啊”保留起音源/成片最大相关性 `0.9781`，lag `39.38ms`；前一次删除尾部的局部指纹未在拼接后窗口复现。
- 五个拼接窗口二次 ASR 分别保留“所有人一起给你”“你身边人”“极限。为啥很多人”“在另一群人眼中”“所以说啊，真正的圈子”，未返回被删尾音伪词。
- 人工听感仍由用户验收，不用自动相关性替代主观听音结论。
- 用户于 `2026-08-21` 确认 `fixed-full-v3.mp4` 试听通过，可以提交。

## 自动化

- 最终聚焦声学/草稿/渲染/组合/前端契约与浏览器工作流：`178 passed, 1 deselected, 1 xfailed`；新增 retained hard-limit 单样本爆音的 delete-end/delete-start 对称回归，确认 `20ms` 重叠滑窗不会把同一噪声误认成持续起音。
- 前端截图同构 Node 回归确认保留文案、删除文案与空白行可见时间为 `[17, 18, 18, 22, 22, 22]`，单调不降；源时间 data 与试听语义保持不变。
- 真实浏览器：`28 passed, 1 xfailed`。
- 全量排除两个既有 TestClient/后台生命周期挂起用例：`333 passed, 2 deselected, 1 xfailed`。
- 排除用例：`test_cut_endpoint_renders_preview_video`、`test_upload_extracts_audio_and_returns_transcript`；两者无 FFmpeg 或外部请求子进程，属于既有测试生命周期问题。
- 最终检查代理：声学边界与前端契约通过，`compileall`、`node --check web/app.js`、`git diff --check` 通过。
