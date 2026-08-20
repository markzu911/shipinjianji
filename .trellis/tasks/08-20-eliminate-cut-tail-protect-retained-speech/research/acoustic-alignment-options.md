# Research: 高精度文字裁剪声学边界方案

- Query: 为本仓库设计可实施的高精度字符/声学边界策略，既清除被删语音尾音又不吞掉下一个保留字；评估复用 DashScope/Paraformer 时间戳与新增本地强制对齐器的可行性。
- Scope: mixed (repository code/data, installed dependency metadata, upstream documentation/model cards)
- Date: 2026-08-20

## Findings

### Executive recommendation

推荐保留现有 DashScope `paraformer-realtime-v2` 作为识别和文案来源，新增一个可缓存的本地 FunASR `fa-zh` 对齐层，专门输入“原始音频 + 已知文案”并产生每个可发声字符的起止时间。它是当前仓库中精度、体积、中文支持和 Windows/Mac 可部署性之间最实际的折中。

不应把强制对齐输出直接当作无约束裁剪点。正确链路是：

1. DashScope 原始 `asrWords` 提供句段、token 顺序和粗声学包络。
2. `fa-zh` 使用精确已知文案（中文按可发声字符分 token）产生字符级 `acousticStart/acousticEnd`。
3. 相邻“删除字 / 保留字”只生成一个共享边界。模型给出两字之间的转换先验，现有 PCM 低振幅/过零吸附只在该先验附近的小窗内消除爆音，不再在上百毫秒的字符中心走廊内猜语义边界。
4. 删除终点的硬上限是下一保留字的对齐起音点；删除起点的硬下限是上一保留字的对齐尾点。两侧结果必须共用，不得分别修正。
5. 对齐失败时使用现有受限波形低谷算法；仍无可信边界时回退语义先验。任何降级都不得为了消尾音跨入下一保留字。

这是一个分层方案，不需要替换现有转写、自然分词、文字删除语义或 FFmpeg 拼接。

### Why the current DashScope result is insufficient

- 仓库已在 `Recognition.call()` 显式传入 `timestamp_alignment_enabled=True`，见 `server/app.py:9014-9037`。因此再“开启时间戳校准”不是新解法。
- DashScope SDK 1.26.4 的 `Recognition` 只是识别调用；本地 SDK 接口为 `call(file, phrase_id=None, **kwargs)`，时间戳校准开关不接收“必须与此参考文本对齐”的参数。它不是 forced alignment API。
- 响应解析只保存 `item.words[].begin_time/end_time`，见 `server/app.py:9054-9094`。随后自然分词继续复用这些原始 token 为 `asrWords`，见 `server/app.py:9097-9126` 和 `server/app.py:7850-7910`。
- 对三个现有 history transcript 的只读统计显示，原始 `asrWords` 中多字符 token 占比分别为 `87.8%`、`87.6%` 和 `86.9%`，最大为 2 个可发声字符。例如已有样本包含 `起给 19.550-20.030s`、`得一 25.820-26.540s`。这说明 token 时间戳对于“得/你”这类 token 内裁剪不够用。
- `transcript_acoustic_character_units()` 目前仍把一个原始 token 按字符数均分，见 `server/app.py:2529-2584`。`refine_shared_character_boundary()` 只能在这个机械先验附近用 RMS 低谷推断，见 `server/app.py:2796-2938`。当两个字连读而且无静音谷时，纯波形算法没有语言学证据可区分尾音和下一字起音。

结论：继续调整 DashScope 开关、RMS 阈值或固定毫秒补偿，都无法从根本上解决 token 内字符时间未知的问题。

### Option evaluation

| Option | Precision/fit | Runtime and packaging | Recommendation |
| --- | --- | --- | --- |
| Keep current DashScope timestamp + waveform valleys | 已有集成，对有明显停顿的边界有效；无法识别连读 token 内字界 | 无新依赖，快 | 保留为降级路径，不作主解 |
| Switch/re-call another DashScope Paraformer recognition model | 仍是“识别后返回模型 token 时间”，不接收确定参考文本；不能保证每个汉字拆开 | 额外网络、费用和延迟，仍受云 API 输出 schema 限制 | 不推荐作为边界修复 |
| FunASR `fa-zh` timestamp prediction | 输入音频和对应文本，直接返回与 token 数一致的时间戳；中文文本按字分 token 即得字级时间 | 模型占用约 159.3 MiB；FunASR 带来 PyTorch/NumPy/SciPy/ModelScope/Transformers 等新运行时；模型卡声明支持 Linux/Mac/Windows | **首选**：只做对齐适配器，不替换云 ASR |
| WhisperX Chinese wav2vec2 alignment | 支持 `return_char_alignments=True`且有字符 score；对已知文本做 CTC 对齐 | WhisperX 3.8.6 强绑 torch/torchaudio/torchvision 约 2.8；默认中文 wav2vec2 权重约 1.2 GiB，且完整 WhisperX 还带 faster-whisper/pyannote/pandas | 精度升级备选，不适合第一次落地 |
| Raw `ctc-segmentation` + Chinese CTC model | 能产生字符概率和置信分，可按已知文本对齐 | `ctc-segmentation` 本身小，但必须自行选择、下载、运行语言匹配的 CTC 网络，并处理 tokenizer/blank/UNK；中文常用权重同样约 1.2 GiB | 只在 `fa-zh` 真实样片验证不达标时进入二期 |
| Montreal Forced Aligner | Kaldi/HMM 传统强制对齐，可到 phone 级 | 主安装路径是 Conda，需 Kaldi、Mandarin acoustic model 和 pronunciation dictionary；与当前 pip + FastAPI 一键运行差异大 | 不适合嵌入当前桌面应用 |

### Why `fa-zh` is the practical first choice

- ModelScope 模型 `iic/speech_timestamp_prediction-v1-16k-offline` 的任务定义就是“输入语音与对应文本，生成文本 token 起止时间”，与本 bug 的缺失信息完全匹配。
- 模型卡展示中文每字时间戳，例如 `一 [380,560]`、`个 [560,800]`，而不是两字一个时间块。
- 模型卡公布的平均起点偏移 AAS：AISHELL-1 上 Paraformer CIF `71.0ms`、Kaldi force alignment `80.1ms`；工业数据上 Paraformer-FA `69.3ms`、Kaldi `60.3ms`。这不是“样本级无误差”保证，但明显优于当前可达数百毫秒误差的两字 token 等分。
- 模型约 159.3 MiB，远小于 WhisperX 默认中文 wav2vec2 的约 1.2 GiB；它属于 FunASR/Paraformer 中文生态，文本归一化风险也低于另外接一套音素词典。

### Proposed data flow and ownership

```text
DashScope Recognition (existing)
  -> raw recognized text + asrWords coarse token envelopes
  -> normalize spoken characters (same OpenCC/punctuation rules)
  -> fa-zh(audio segment + exact spaced character tokens)
  -> validated acoustic character map (cached, immutable for source text)

semantic textRanges / manual requested ranges
  -> classify deleted-vs-retained neighboring characters
  -> one shared forced-aligned transition boundary
  -> optional very-local PCM zero-crossing/de-click refinement
  -> persisted physical start/end
  -> preview, /cuts, /compose consume the same persisted boundaries
```

建议保留三层数据的独立所有权：

- `words/asrWords` 和 `originalStart/originalEnd`：文案选择与删除语义，不因对齐结果改变。
- 新的字符声学映射：只表达原片中可发声字符的声学位置；可以是 segment 下的 `acousticCharacters`，也可以是 job 级缓存，但不要覆盖原始 ASR 字段。
- 草稿的 `start/end`：唯一的媒体裁剪范围，在草稿 PUT 阶段生成和保存；生成阶段不得重算。

对齐应在原始转写完成后按 ASR 句段预计算，而不是每次草稿保存都对整部视频重跑模型。对齐缓存 key 至少应包含：

- 源媒体指纹（或 job/source 不可变标识）；
- 经统一归一化的句段可发声文本；
- 对齐器名称、模型 revision 和算法 schema version。

当用户修正文案时，只使对应句段的缓存失效。参考文本与音频无法匹配时不应强行使用旧对齐。

### Shared boundary rules

1. 对一个“删除字 L / 保留字 R”转换，先取强制对齐的 `L.acousticEnd` 和 `R.acousticStart`。
2. 若两者之间有非负间隙，只在该间隙内选能量谷/过零点；无谷时用对齐转换先验。
3. 若对齐区间重叠或共边，使用对齐器给出的唯一转换点，不得向 `R.acousticStart` 之后搜索。
4. PCM 细化窗只用于避免波形不连续，其宽度应由真实样片实验确定，不能变成新的固定“多删几毫秒”。
5. 最终边界必须 finite、单调、位于对应句段和原始 token 包络内，且不超过下一保留字的起音硬限。
6. 一个保留字两侧都是删除范围时，两侧共享边界必须为它保留正时长的声学核心，不允许两侧微调相交。

`CUT_AUDIO_FADE_SECONDS=0.008` 仍只负责消除拼接爆音，不能被当作消尾音方法。

### Manual timeline deletion policy

当前代码和测试明确保留手动 `timelineRanges` 的精确秒数，它不进入 `align_cut_draft_text_ranges_to_audio()`，见 `server/app.py:10633-10651`；`resolve_cut_draft_delete_ranges()` 后续直接加入该范围，见 `server/app.py:1859-1940`；测试在 `tests/app/test_cut_draft.py:516-546` 锁定了“manual stays exact”。要解决用户报告的手动删除尾音，该产品契约必须显式改变，不只是更换一个 RMS 阈值。

建议的兼容策略：

- 为 timeline item 分开保存用户范围 `requestedStart/requestedEnd` 和物理范围 `start/end`，与 `textRanges.originalStart/originalEnd` 的语义/物理分层同构，保证幂等和可撤销。
- 如果手动端点位于可配置的最大吸附距离内（产品已接受约几十到 200ms 的位移，建议上限 `0.20s`），吸附到最近的高质量共享字符边界。
- 如果端点明显落在某个字的声学核心深处，就不存在既“保持精确鼠标秒数”又“完整删该字且不改变相邻语音”的唯一解。安全做法是保留请求点并仅做 de-click，或在 UI 明示吸附结果；不能静默吞掉整个下一字。
- 草稿 PUT 返回最终物理范围，前端预览指示条、切口和最终导出必须同时更新到该值，不允许预览显示鼠标点而导出用吸附点。

这一改动需要更新现有测试和 `.trellis/spec/backend/media-and-timeline.md` 中“timelineRanges 不参与对齐”的旧契约。

### Alignment validation and fallback behavior

`fa-zh` 对齐结果不应仅因“模型返回了数组”就被接受。建议适配器统一校验：

- 对齐 token 数与归一化后的可发声字符数完全一致；
- 所有区间 finite、非负、单调且 `end > start`；
- 时间戳不逃出当前带有小量音频上下文的 ASR 句段包络；
- 与原始 `asrWords` 字符序列可一一对应，不使用“最像的长度”猜测错位；
- 在最终高能拼接点或对齐大幅跳出 DashScope 粗 token 包络时，记录可诊断的失败原因并降级，不要强行扩大删除范围。

降级顺序建议为：

1. 有效 forced alignment + 受限小窗 PCM 微调；
2. forced alignment 无效时，复用当前受限共享波形边界；
3. 缺模型、音频解码失败、文本不匹配或两层都无证据时，回退语义边界；
4. 所有降级以“不吞保留字”为硬不变量。

注意：`fa-zh` 模型卡示例返回 token 时间戳，未展示每 token confidence。第一期不应伪造模型置信度；应将上述结构校验与声学一致性分开记录。若真实样片证明必须依赖字符 posterior score，再升级到 CTC 方案。

### Performance and dependency risks

- 当前 `requirements.txt` 无 PyTorch、NumPy、SciPy、librosa、soundfile、ModelScope 或 Transformers。FunASR 1.4.2 的 PyPI 元数据会引入一组语音/ML 依赖，并且上游 README 明确要求先安装 PyTorch/torchaudio。例如 Windows CPython 3.11 的 torch 2.8.0 CPU wheel 约 230.2 MiB，还未包含间接依赖。
- Mac 发布包目前每次启动使用 `pip install -r requirements.txt`，而且打包规则故意只创建空的 `data/models/.gitkeep`，见 `tools/build_mac_package.py:93-116` 和 `tools/build_mac_package.py:210`。直接把 FunASR 加入基础 requirements 会明显增加首次安装时间和网络失败面。
- 模型应显式缓存在 `DATA_DIR/models` 下，避免隐式落到用户 home 的不可管理缓存。模型版本要固定，否则同一草稿的物理边界可在升级后漂移。
- 不应在每次 PUT 中重新初始化模型。建议进程级惰性单例 + 线程/并发保护，转写结束后按句段批量预计算。旧历史可在首次编辑影响句段时惰性补齐并缓存。
- 模型冷启、CPU 实时率、内存峰值和 Mac Intel/Apple Silicon wheel 可用性必须先做小型 spike；上游公布了精度和平台支持，但未为本仓库的 2-3 分钟视频给出实际冷启/端到端耗时。
- 建议把模型可用性、revision、是否降级暴露在健康/诊断信息中，避免“功能看似开启，实际一直在旧算法”。

### Verification plan

#### Adapter and contract tests

- 用假 `fa-zh` 输出验证：中文标点/空白归一化后每个可发声字符精确对应一个时间区间；数量不一致、逆序、NaN/Inf、越界统一降级。
- 验证缓存 key 包含文本和 model revision；重复保存不重跑对齐，只修改一句时仅使该句失效。
- 测试发音文本与修正文案不匹配、缺模型、模型下载失败和音频解码失败的降级；不得因对齐增强而使原有编辑失败。

#### Boundary invariants

- `words=觉得/你`、`asrWords=觉/得你`：模拟对齐将“得”尾点放在“你”起音前，断言物理终点超过旧的 token 均分点，但不大于“你”起音硬限。
- `words=一起/给/一起/给`、`asrWords=一起/给一/起给`：删除第一遍后只保留第二遍，既不多一个“一”也不丢首字。
- 单个短保留字被两个删除范围夹住时，两个共享边界不相交，并且保留字有正时长。
- 同一段 PCM 做不削波增益变换后，强制对齐共享边界和小窗过零结果不发生语义级跳变。

#### Manual timeline and cross-entry tests

- 将现有 `test_text_ranges_use_character_units_but_manual_timeline_ranges_stay_exact` 更新为新契约：保存 requested 范围，物理范围在 `0.20s` 上限内吸附；无安全候选时保持原点。
- 同一语音边界通过 AI 文字删除、手动选择文字、手动 timeline 三个入口产生同一共享物理边界。
- 连续两次 PUT 草稿完全幂等；预览、`/cuts` 和 `/compose` 读取已保存结果，生成阶段对齐器调用次数为 0。

#### Real-media gate

- 对用户附件定位的 `得/你` 切口记录：DashScope token 包络、旧均分点、`fa-zh` 两字时间、最终共享点、局部多窗 RMS 和是否触发降级。
- 使用同一已保存草稿生成预览和最终成片，断言两者的源时间保留范围完全相同。
- 二次 ASR 只能作为辅助证据；必须同时人工盲听“被删尾音是否可辨”和“下一字首音是否完整”，并保留源/输出 PCM 边界对比数据。
- 上线前在 CPU-only Windows 和 Mac 各测量模型冷启、1/3/10 分钟音频的预计算耗时、峰值 RSS 和磁盘缓存大小，再决定是否放入默认 requirements 还是使用单独的对齐运行时安装步骤。

### Files found

- `requirements.txt` - 当前运行依赖，没有本地 ML/对齐工具链。
- `server/app.py:302-321` - 当前裁剪边界常量和“ASR 时间戳不是物理切点”的现有注释。
- `server/app.py:1859-1940` - 草稿范围合并；手动 timeline 范围现在绕过文字对齐。
- `server/app.py:2529-2584` - 原始多字 token 按字符数等分为声学字符先验。
- `server/app.py:2796-3033` - 现有共享边界 RMS 低谷细化和边界缓存。
- `server/app.py:3134-3218` - 仅对 textRanges 做草稿音频对齐，解码失败时安全回退。
- `server/app.py:7850-7910` - 自然句段保留原始 `asrWords` 的当前数据流。
- `server/app.py:9014-9127` - DashScope Recognition 已开启 timestamp alignment，并将返回 token 毫秒时间存入 transcript。
- `server/app.py:10633-10651` - 草稿 PUT 中 textRanges 与 timelineRanges 目前使用两条不同的边界路径。
- `tests/app/test_cut_acoustic_boundaries.py:74-126` - `觉/得你` 多字 raw token 的现有合成低谷回归。
- `tests/app/test_cut_draft.py:516-546` - 手动 timeline 秒数保持精确的现有产品契约。
- `tools/build_mac_package.py:93-116` - Mac 首启 pip 安装和运行目录初始化。
- `tools/build_mac_package.py:210` - 发布包中模型目录故意为空，本机模型缓存不进包。
- `data/history/*/transcript.json` - 只读样本显示约 87% 原始 ASR token 包含两个可发声字符。

### External references

- DashScope Python SDK 1.26.4 installed source: `dashscope.audio.asr.Recognition`; documents `timestamp_alignment_enabled` as timestamp calibration, not reference-text forced alignment.
- FunASR 1.4.2 PyPI metadata: `https://pypi.org/project/funasr/`; dependency surface includes SciPy, librosa, soundfile, NumPy, ModelScope, Transformers and related speech tooling.
- FunASR model selection: `https://raw.githubusercontent.com/modelscope/FunASR/main/docs/model_selection.md`; recommends Paraformer when Mandarin character-level timestamps are needed.
- FunASR timestamp prediction model: `https://www.modelscope.cn/models/iic/speech_timestamp_prediction-v1-16k-offline`; input audio + corresponding text, token timestamps, published AAS comparison, model storage about 159.3 MiB, Apache 2.0 model license, Linux/Mac/Windows support. Upstream examples use the alias `fa-zh` and show revision `v2.0.4`; the current ModelScope widget metadata reports `v1.2.1`, so implementation must test and pin an exact available revision rather than copy an alias blindly.
- WhisperX 3.8.6: `https://github.com/m-bain/whisperX`; forced wav2vec2 alignment, Chinese default `jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn`, optional character alignments. The Hugging Face PyTorch checkpoint reports about 1.2 GiB.
- CTC Segmentation 1.7.4: `https://github.com/lumaku/ctc-segmentation`; supports character-wise alignment/confidence but requires CTC activations from a language/tokenizer-matched model; documentation notes inference cost dominates and Asian languages still require correct dictionary/blank configuration.
- Montreal Forced Aligner 3.4.2: `https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner`; Kaldi-based CLI, primarily installed via Conda, with separate acoustic model and pronunciation dictionary lifecycle.

### Related specs and prior decisions

- `.trellis/spec/backend/media-and-timeline.md` - 语义/物理范围分离、共享声学边界、预览/生成一致和安全回退契约。本任务若改动手动 timeline 吸附，需同步更新该 spec。
- `.trellis/spec/backend/quality-guidelines.md` - 共享逻辑、不变量、返回 schema 和外部服务回归要求。
- `.trellis/spec/testing/index.md` - 媒体算法要用短小真实样片，外部模型必须 monkeypatch，时间轴需断言源/剪后范围。
- `.trellis/spec/operations/index.md` - 新模型配置、DATA_DIR 模型缓存和 Mac 发布包必须显式设计。
- `.trellis/tasks/archive/2026-08/08-17-eliminate-deleted-text-tail-protect-next-speech/design.md` - 既有共享边界设计；已明确纯波形无法证明连读字界，强制对齐应作为独立升级。
- `.trellis/tasks/archive/2026-08/08-19-fix-deleted-transcript-audio-boundary/debug-retrospective.md` - 已记录绝对 RMS 阈值和单一真实样本无法构成通用保证。

## Caveats / Not Found

- 本轮未下载或运行 `fa-zh` 权重，因此还没有本机冷启、CPU RTF、内存峰值和用户 `得/你` 切口的实际偏移数据。实施前需先做不写入用户数据的 spike。
- 上游模型的 AAS 是数据集平均指标，不证明每个连读字都能零误差分离。“永远零尾音且永远不伤下一字”在共发音和文本/音频不匹配时仍不是数学可证承诺；实现必须保留安全降级。
- FunASR 模型卡展示 token timestamp，未展示 per-token confidence schema。若适配器需要概率分，必须从实际固定 revision 的输出验证，不能按文档猜字段。
- 英文单词、数字读法、缩写、同音修正文案和中英混读的 tokenization 需另外验证；本推荐首先覆盖用户当前的中文口播主路径。
- 手动 timeline 端点落在一个字的实际声学核心内时，用户意图本身是暧昧的。本文建议只在有限吸附半径内修正，超出半径时保留原点和可见预览；不能用声学模型替用户决定删哪个字。
