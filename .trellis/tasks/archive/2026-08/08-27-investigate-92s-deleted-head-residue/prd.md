# 修复同段删除起点的被删首字残音

## Goal

修复一类可跨视频、说话人和文字内容复现的删除起点边界误判：当强制对齐给出的被删首字起点略晚于真实声学起音时，利用 VAD 与 PCM 的联合证据把物理删除起点落在被删起音之前的可靠低能位置，优先保证被删语音不留下可闻片段，同时保护相邻保留表达。

## Background

- 用户要求修复算法类别，禁止针对 `1:32`、汉字“在”或单个视频写特例。
- 用户的产品优先级是“被删声音绝不残留”；可以接受相邻保留音节轻微受损，但不能删掉整句或整段保留表达。
- 不允许用固定毫秒 padding、硬编码样本时间或直接退到保留字符 hard limit。
- 本任务只修改和验证开发环境，不提交到生产、不推送、不合并、不部署。

## Confirmed Facts

- 附件 `C:\Users\jiadi\Downloads\飞书20260728-152857-当前预览版.mp4`、job `b7692265-d8e3-4829-8eba-b4bfc4f1d793` 的 `composition.mp4` 与 `edited.mp4` SHA-256 均为 `A0DACE1B1911D665E1D6B9C88AE45B3B93BFEDC36FF450888FD4CC7A482AFAB9`，已排除文件错配和旧生成结果。
- 语义删除范围为 `119.328–122.370s`，草稿保存及 FFmpeg 实际消费的物理范围为 `119.008–123.459s`，已排除草稿 revision 和生成消费错误。
- 左侧保留“是”forced end 为 `118.608s`，被删首字“在”forced start 为 `119.008s`；VAD 把 `118.088–119.588s` 判为连续 speech，未找到可信静音走廊。
- 真实 PCM 在约 `118.99s` 前保持低能，约 `119.000s` 出现持续起音。当前 forced candidate `119.008s` 已进入该起音，因此残留不足一个音节的“在/另”片段。
- 直接把物理起点退到 retained hard limit `118.608s` 的试听结果为“两句都没有了”，属于不可接受的过切。
- 诊断切点 `118.995s` 经用户试听确认：残音消失，相邻保留表达可接受。该数值只是真实媒体验收基准，不得成为产品代码常量。
- `corroborate_forced_deleted_head_with_pcm()` 的 probe window 已延伸到 candidate 之后，但循环在 `attack_start > forced_candidate + 0.001` 时提前停止。本样本需要 candidate 后的连续高能块才能确认起音，helper 因此返回 `null`。
- helper 返回 `null` 后，`forced_alignment_transition_boundary()` 仍无条件写入 `boundaryTrustworthy=True` 和 `trustReason=forced_transition`，aggressive resolver 最终保留未经 PCM 佐证的 `119.008s`。

## Root Cause And Impact Class

这是系统性但有边界的算法缺陷，不是单个视频的偶发现象。以下条件同时出现时都可能复现：

1. 删除从同一 ASR/可编辑段落内部的某个字符开始，且不是重复文本歧义路径。
2. 相邻字符之间没有被 VAD 识别为独立静音，语音存在连读、共发音或轻噪声。
3. forced alignment 受帧粒度或模型误差影响，候选起点比真实被删起音晚若干毫秒。
4. PCM 需要 candidate 后一个或多个高能 block 才能确认前面的 quiet-to-attack 转换。
5. 失败佐证被错误降级为“forced transition 可信”。

这些条件与具体汉字、时间位置和视频无关，因此在不同说话人、语速、录音增益和素材上都可能再次出现；但不影响已有可信静音走廊、删除尾端、重复文本或跨段路径，除非审计发现相同的 lookahead 截断模式。

## Requirements

- R1. 修复范围以 `same_segment + delete_start + non-repeat` 的 forced/PCM 佐证链路为主，不能按媒体时间、汉字或固定偏移写分支。
- R2. PCM 可以读取 candidate 之后的有限窗口，但这些样本只能确认 sustained attack，不能成为最终切点，也不能把最终切点推迟到 candidate 之后。
- R3. 成功佐证时，最终物理删除起点必须来自 attack 之前的持续低能证据，并满足 `retainedSpeechHardLimit <= final < forcedCandidate`。
- R4. helper 返回的边界、`pcmValleyStart`、`pcmValleyEnd`、`pcmAttackStart` 和 trust reason 必须语义一致；不得依赖外层 resolver 再把一个仍等于 forced candidate 的“成功结果”隐式改早。
- R5. 没有可信 quiet-to-attack 时，必须保留“未佐证”状态并进入受 retained hard limit 保护的删除方向 waveform fallback；不得继续把 forced candidate 当作声学可信点。无法同时无损分离时按用户优先级偏向清除被删语音，但不能越过 hard limit 吞掉完整保留表达。
- R6. 保持 attack 证据完全位于 candidate 之前时的现有精确行为；均匀高能、均匀低能、短暂低谷、单采样低点、单调缓升和轻微噪声不得产生虚假佐证。
- R7. 参数化验证 candidate 相对真实起音的多种偏移、不同增益、轻噪声和多个起音事件，证明算法依据波形结构而不是当前样本数值工作。
- R8. 文字删除、用户点击文案拆分后产生的可编辑段落、时间轴删除及后续预览/生成必须消费同一 resolved physical point；语义文字范围不得被物理吸附反写。
- R9. 审计重复文本和跨 segment 两条 resolver 路径是否存在同类 premature lookahead；没有同类缺陷时只补审计结论和回归，不扩大修改面。
- R10. 真实媒体 gate 必须同时验证残音消失、上一保留表达“以前不敢想的事”可听、下一保留表达“一群人眼中”未丢失。

## Acceptance Criteria

- [x] AC1. 参数化单元测试覆盖 candidate 在真实起音前后不同位置；只要存在满足持续性和相对能量条件的 quiet-to-attack，返回边界均位于已确认低能区且严格早于 candidate。
- [x] AC2. 不同非削波增益、轻噪声和多个起音事件得到结构等价结果，并选择 retained limit 之后第一个可信起音对应的保守删除边界。
- [x] AC3. 均匀高能、均匀低能、brief dip、single point 和 monotonic rise 不被误报为可信 deleted-head 转换；PCM 佐证失败后不得再无条件把同一个 forced candidate 标为可信。
- [x] AC4. 现有“attack 完全早于 candidate”的成功用例保持通过，删除尾端、重复文本、跨 segment、VAD fallback 和 `split_exact` 行为无回归。
- [x] AC5. 同一删除范围在 text、timeline、editable segment、cut draft、retained transcript、预览和 FFmpeg 计划中共享同一物理边界；生成阶段不重新运行 FA/VAD/PCM。
- [x] AC6. 真实附件在目标拼接点得到约 `118.995s` 的声学边界（允许一个 PCM step 的离散误差，产品实现不硬编码该值），用户确认的被删首音消失，前后保留表达均存在。
- [x] AC7. 代码中不新增固定毫秒补偿、目标媒体时间或目标文字判断；完整相关测试、完整应用测试和 `git diff --check` 通过。

## Out Of Scope

- 不修改 VAD 模型、ASR/forced-alignment 模型或模型权重。
- 不借本任务重构全部音频边界 resolver；重复和跨段路径仅在审计确认同类根因时修改。
- 不修改用户真实 job、history 或原始媒体。
- 不推送、合并、部署或修改生产环境。
