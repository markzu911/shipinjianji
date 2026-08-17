# 媒体与时间轴

## 时间轴语义

系统同时存在源视频时间和剪后时间：

- ASR word/segment 时间戳首先锚定源视频。
- 删除区间经 `normalize_delete_ranges`、`build_keep_ranges` 和音频边界吸附形成物理剪切计划。
- 剪后 transcript、艺术字和画中画需要使用 retained transcript/source anchor 映射，不能凭相同秒数猜测。
- 预览和最终合成必须消费同一组归一化 overlay 数据。

任何跨剪辑边界功能都应明确输入时间轴、输出时间轴和转换函数，并增加往返测试。

## FFmpeg/FFprobe

- 可执行文件通过 `get_ffmpeg_binary` 获取。
- 统一经 `run_ffmpeg` 执行需要取消支持的生成命令。
- 参数使用列表，不启用 shell 字符串拼接。
- 先 probe 时长/尺寸；不合法媒体在进入后台长任务前失败。
- 输出写入同目录临时文件，成功后原子替换。
- 文字资源使用 UTF-8 临时文本/filter script，避免直接把长文案塞入命令行。

## 渲染契约

- `render_cut_video` 只负责删除范围后的基础成片和音频规范化。
- `render_art_text_video` 使用已经归一化的文字 overlay；安全区由 `ART_TEXT_SAFE_AREA_RATIO` 保护。
- `render_picture_in_picture_video` 使用已确认素材和标准化位置/尺寸。
- `process_preview_composition_job` 是剪辑、艺术字、画中画统一预览链路；修改任一层时同时验证单功能和组合功能。

## 资源与安全

- 临时图片、视频、字幕文本和 filter script 必须位于 job 工作目录。
- 下载外部视频后重新 probe/规范化，不信任扩展名或响应声明。
- 用户可控颜色、字体、位置、尺寸、时长先经过白名单或 clamp。
- 不允许输出路径逃逸 `DATA_DIR`，也不允许清理任意用户路径。

## 验证重点

- 删除边界不会吞掉保留语音；媒体吸附不改变文字选择。
- 原视频直接加艺术字/画中画与剪后源都可用。
- 预览组合与最终输出在时间、位置和样式上相同。
- Windows 长命令、缺失字体、取消、失败清理和音频规范化有回归测试。

参考：`server/app.py` 的 `timeline_after_deletions`、`build_retained_transcript`、`render_*`；`tests/test_app.py` 的 cut boundary、art text、picture-in-picture 和 preview composition 用例。

## 场景：文字草稿在预览前完成音频边界校准

### 1. Scope / Trigger

- 文字删除范围来自 ASR word/segment 时间戳时，必须在进入公共预览和最终生成前吸附到真实音频低谷。
- 时间轴手动范围和已检测的无声范围不参与这次文字边界校准。

### 2. Signatures

- API：`PUT /api/transcriptions/{job_id}/cut-draft`
- 后端：`align_cut_draft_text_ranges_to_audio(media_path, text_ranges, segments, duration)`
- 前端：`applyPersistedCutDraftAlignment(draft, expectedSignature)`

### 3. Contracts

- `textRanges[].originalStart/originalEnd` 表示删除哪些文字，不因波形吸附而改变。
- `textRanges[].start/end` 表示真实媒体删除范围；草稿 PUT 响应可以在保留文字保护限制内扩大该范围。
- `adjacentSilenceBefore/After` 必须按校准后的物理边界重新计算。
- 前端只有在当前草稿签名仍等于本次请求签名时才能应用响应；应用后更新当前撤销快照，不新增撤销记录。
- 剪辑任务的 `ranges/requestedRanges` 保持物理预览范围，另以 `transcriptRanges` 保存语义文字范围；生成和统一合成使用前者裁切媒体、使用后者重建剪后 transcript。
- 后续修正文案而重建剪后 transcript 时优先读取 `transcriptRanges`，历史任务缺少该字段时兼容回退到 `requestedRanges/ranges`。
- `/cuts`、`/compose` 和公共预览继续消费草稿中同一组 `start/end`，生成阶段不得再次吸附。

### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| job、媒体或时长无效 | 沿用既有 `404` / `409` 契约，不写草稿 |
| range 非有限值或 `end <= start` | `400`，不写部分草稿 |
| 草稿 revision 过期 | 校准前或写入前返回 `409` |
| 音频解码/分析失败 | 保留请求中的物理范围，草稿仍可正常保存 |
| 保存期间前端又发生编辑 | 只推进 revision，不用旧响应覆盖新编辑；队列继续同步新状态 |

### 5. Good / Base / Bad Cases

- Good：ASR 尾点落在低音量尾音中，物理 `end` 延伸到相对更低的局部谷值，文字 `originalEnd` 不变。
- Base：ASR 边界已经位于同等低的谷值，返回范围保持不变，重复保存不继续漂移。
- Bad：只在生成阶段调用波形吸附，导致列表/公共预览与成片使用不同删除范围。

### 6. Tests Required

- 单元测试：低整体音量样本仍按相对能量改善识别尾音，不依赖固定 RMS 阈值。
- API 测试：草稿 PUT 返回校准后的 `start/end`、原始语义边界和重算的相邻静音，并验证重复 PUT 幂等。
- 生成回归：`process_cut_job` 与组合生成不得再次调用边界吸附，最终 `ranges` 等于已保存草稿物理范围；物理范围延长时 `transcriptRanges` 仍只删除选中的语义文字。
- 前端契约：校准响应更新预览和当前撤销快照，旧请求响应不能覆盖并发新编辑。

### 7. Wrong vs Correct

```python
# Wrong: 导出时才校准，预览与成片不一致。
media_ranges = snap_delete_ranges_to_audio(video_path, requested_ranges, duration)

# Correct: 草稿保存时校准一次，后续消费者直接复用。
text_ranges = align_cut_draft_text_ranges_to_audio(
    video_path, text_ranges, source_segments, duration
)
media_ranges = copy.deepcopy(requested_ranges)
```
