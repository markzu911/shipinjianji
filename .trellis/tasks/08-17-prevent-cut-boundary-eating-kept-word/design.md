# 自动裁剪保留文案保护设计

## Boundaries And Ownership

- `textRanges[].originalStart/originalEnd`：文字语义删除的权威范围。
- `textRanges[].start/end`：在不穿越保留文字前提下，吸附到空白低谷后的物理范围。
- `noSpeechRanges`：自动空白选择，物理投影必须从中扣除所有识别文字。
- `timelineRanges`：用户二次确认的手动删除，可以显式覆盖文字，不受自动空白保护限制。

## Backend Flow

0. 转写阶段将 DashScope `words[].begin_time/end_time` 转换后的原始 word 边界保存为 `segments[].asrWords`；现有 `segments[].words` 继续通过 Jieba 生成，用于自然中文展示和语义分析。标点校对可以调整两层的文字附着，但不得改变 `asrWords` 时间边界。
1. 草稿 PUT 对 `textRanges` 做波形吸附时，使用零 head/tail guard 的相邻保留文字限制；吸附只能在上一保留单元结束与下一保留单元开始之间发生。
2. 解析草稿用于预览/生成时，先将文字物理范围和已扣除识别语音的空白范围组成“自动删除集”。
3. 自动删除集的合并只能跨过没有保留文字的间隔；合并后再执行一次保留文字校验/扣除，防止容差合并重新引入交集。
4. 最后再合入 `timelineRanges`；手动范围可删除文字，但不得使相邻自动范围凭容差吞掉手动范围之外的保留文字。
5. 公共预览、单独剪辑和统一组合生成继续调用同一个草稿解析所有者，生成阶段不再做独立波形吸附。
6. 所有文字语义范围在吸附和 retained transcript 处理前，先规范到与其相交的字符时序单元。每段优先从 `segments[].words` 拆出字符；缺少 `words` 时才从该段 `asrWords`，再从 segment 文本/时长逐字符回退。`timelineRanges` 不走此规范，继续表示用户明确选择的精确时间轴范围。

## Frontend Flow

1. 文案继续拆成字符 token 展示；字符触发删除时按相交字符单元规范 `originalStart/originalEnd`，不得扩展到跨自然词边界的原始 ASR token。`selectedRanges` 仍只用该语义范围判定删除状态。
2. `selectedNoSpeechRanges` 在进入预览时继续通过 `protectRecognizedSpeechFromQuietRanges`，且自动范围合并后不得跨过保留词。
3. `buildSegmentTextRuns` 的“普通已删除”只参考已提交的 `timelineRanges`；空白和文字静音扩展不参与文案状态投影。
4. 预览时间轴仍使用全部安全物理范围，因此文案显示与真实播放/生成保持一致。

## Compatibility

- 在 transcript segment 中新增可选 `asrWords` 字段，字段结构与现有 `words` 相同；它只保存原始模型参考，删除消费者逐段按 `words -> asrWords -> segment` 派生字符单元，因此旧 API 数据、旧历史和旧草稿无需迁移。
- 新转写保留 `segments[].asrWords` 的模型原始边界；历史数据缺少 `words` 时，才从该段 `asrWords` 或 segment timing 生成兼容字符单元。
- 不主动读写历史 `data/jobs` 文件；旧草稿在下次正常 PUT 时按新边界重算。
- 保留手动时间轴删除的现有二次确认和删除文字能力。

## Failure And Fallback

- 音频解码失败时，仍使用原语义范围，不为获取空白而放宽至保留文字。
- ASR 时间粗粒度导致空白与字符时序重叠时，优先保留字符；少删空白是可接受的安全退化。
- 字符时间由自然词或兼容层均分获得，不保证独立声学边界；媒体吸附只能在相邻保留字符之间寻找低谷，不能越过字符边界。

## Validation

- 单元：前后保留词边界、空白与文字部分/完全重叠、`<0.12s` 短保留词、安全空白低谷。
- API：草稿 PUT 返回安全物理范围、语义范围不变、相邻空白重算、重复 PUT 幂等。
- 生成：预览/剪辑/组合消费同一范围，保留 transcript 不丢词。
- 浏览器：删除空白行时相邻文案状态不变，预览播放不跳过保留文字。
- 转写与浏览器：模型多字 word 的原始时间不被重新分词覆盖，但删除仍按自然词派生字符执行；覆盖 `一起/给/一起/给` 对 `一起/给一/起给`、`觉得/你` 对 `得你` 两种跨界形状。
