# 产品链真实媒体重跑

## 结论

2026-08-20 使用当前产品实现完成同草稿真实媒体自动化重跑。产品 resolver 把目标删除范围的物理终点从旧 `37.190s` 修正为 `37.810s`，语义终点继续保持 `37.120s`，下一保留“你”的可靠起音 `39.850s` 作为不可穿越硬上限。

真实 `render_cut_video()` 输出中，被删尾音指纹相对同链路旧边界显著下降；下一“你”的新旧输出 PCM 高度一致。Faster Whisper tiny 二次 ASR 在旧边界单独返回“都觉得”，新边界不再返回该被删残留，并继续识别保留的“你身边人都觉得”。

人耳盲听未执行，因此 AC1 的人工听感部分仍未通过，不把本次自动化结果表述为完整验收。

## 输入与隔离

- 只读源：`data/jobs/58012dc3-3adf-4def-97eb-71a5f32323dd/source.mp4`
- 源 SHA256：`F34587E8F453F35F97373051E632F5ABBD86F5412B1F6A9E252A8D848C76E06B`
- 只读同草稿：`data/jobs/9fecd1d3-8215-492e-8fd2-87364a9ac922/cut-draft.json`
- 草稿 SHA256：`9C4AF34DC8968A7DB030E17E2F635B45288CAAB88830314D954FB915B82F8CF7`
- 临时工作目录：`C:\Users\jiadi\AppData\Local\Temp\codex-product-cut-gate-20260820-01`
- 源视频因 C/D 盘不能建立硬链接而复制到临时目录；所有 sidecar、模型副本、WAV、报告和 MP4 都只写临时目录，真实 `data/jobs`、`data/history` 未写入。

对齐输入使用完整句段 `32.800-47.400s` 和完整已知文本，不使用短窗局部对齐。目标附近语义 word 时间沿用同草稿证据，原始粗 token 仍记录为 `都觉 36.040-36.760s`、`得你 36.760-37.480s`、`身边 37.480-38.200s`，但不充当字符硬包络。

## 产品 Adapter 与 Resolver

产品 `server.acoustic_alignment.ensure_acoustic_alignment_cache()` 在固定环境中生成临时 sidecar：

- `aligner=funasr-fa-zh`
- `modelRevision=v2.0.4`
- `fullSegment=true`
- `expectedCharacterCount=42`
- `alignedCharacterCount=42`
- `confidence=null`，未伪造模型未提供的置信度
- 被删“得”：`37.570-37.810s`
- 下一保留“你”：`39.850-39.990s`

随后主环境调用产品 `resolve_cut_draft_acoustic_boundaries()`，命中并复用该 sidecar：

- alignment summary：`completed`，`validSegmentCount=1`，`reusedSegmentCount=1`
- 物理目标范围：`33.160-37.810s`
- 语义目标范围：`33.160-37.120s`
- diagnostic：`direction=delete_end`、`alignmentSource=funasr-fa-zh`、`alignmentRevision=v2.0.4`、`adjacentCharacters=[得,你]`、`retainedSpeechHardLimit=39.850`、`structureValid=true`、`pcmAdjustment=0`、`fallbackReason=null`

完整报告位于临时目录 `product-gate-report.json`。

## 产品渲染与 PCM Gate

当前产品 `render_cut_video()` 对同一组其余草稿范围分别生成旧/新边界对照：

| 输出 | 目标恢复点 | 时长 | SHA256 |
| --- | ---: | ---: | --- |
| `product-old-boundary.mp4` | `37.190s` | `146.100s` | `6F046D3F3AD186AEE97E4007D0731649077961B1BB512DF6CAD79FB137C0819A` |
| `product-same-draft.mp4` | `37.810s` | `145.500s` | `B2214F4374B0F9197D87C694A7BE732E3E4A6D889153B791A33D6B95B520F185` |

两份输出都经过产品完整 FFmpeg/H.264/AAC、`8ms` fade 和全片响度归一化链。PCM 对比使用源 `37.570-37.810s` 作为被删尾音指纹，源 `39.850-40.150s` 作为下一保留“你”的起音窗口：

| 指标 | 旧 `37.190` | 新 `37.810` |
| --- | ---: | ---: |
| 右侧首 `800ms` 被删尾音最大相关 | `0.362062` | `0.172824` |
| 下一“你”相对源相关 | `0.447279` | `0.444839` |
| 下一“你”相对源 lag | `19.9375ms` | `13.5625ms` |
| 下一“你”相对源 RMS 比 | `2.274860` | `2.284377` |

因全片响度归一化会改变相对源 RMS，本轮还直接比较了旧/新输出中的下一“你”：归一化相关 `0.992636`、额外 lag `0ms`、新/旧 RMS 比 `1.024921`。这证明新边界显著减少被删尾音，同时未对下一保留起音造成可测的额外削弱。

完整 PCM 报告位于临时目录 `product-pcm-comparison.json`。

## 二次 ASR Gate

使用仓库本地缓存的 Faster Whisper tiny revision `d90ca5fe260221311c53c58e660288d3deb8d356`，参数保持 `language=zh`、`beam_size=5`、word timestamps、关闭 VAD 和 previous-text conditioning。

- 旧 `37.190s`：单独返回被删残留“都觉得” `3.40-4.28s`，随后返回保留“你身边人都觉得” `5.62-7.36s`。
- 新 `37.810s`：不再返回独立“都觉得”，直接返回保留“你身边人都觉得” `4.94-6.74s`。

完整 ASR 报告位于临时目录 `product-secondary-asr.json`。二次 ASR 是辅助证据，不替代 PCM 保护与最终人耳盲听。

## 剩余 Gate

- 人耳盲听：未执行，需要最终验收者试听 `product-same-draft.mp4`，确认听不到被删尾音且下一“你”完整。
- Mac Intel/Apple Silicon 模型安装和实机运行：未执行，仍是默认发布前 gate。

