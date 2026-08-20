# 统一字符声学对齐与裁剪边界设计

## 1. Design Goal

把“删哪些内容”和“媒体从哪里切开”彻底分离，并让 AI 文案删除、手动文案删除、手动时间轴删除在草稿保存阶段使用同一个后端物理边界解析器。最终切点必须完整覆盖被删发音，同时把下一保留字符的可靠起音作为不可穿越的硬边界。

本设计不再尝试从连续语音的 RMS 局部低谷猜测语言学字界。现有 DashScope 继续负责文案与粗粒度 token 时间；新增本地已知文本强制对齐，只负责生成可缓存的字符声学证据。

## 2. Alignment Engine Decision

首选 `FunASR fa-zh`（`iic/speech_timestamp_prediction-v1-16k-offline`），固定经过真实样片验证的 model revision。原因：它直接接收音频和对应文本并返回中文 token 时间，模型约 159 MiB，职责与本缺陷缺失的信息一致。

不采用以下方案作为主路径：

- DashScope `timestamp_alignment_enabled=True` 已启用，但返回的 `asrWords` 仍大量包含两个字符，且没有已知文本强制对齐接口。
- `faster-whisper tiny` 虽已在本机缓存，真实样片 spike 出现长跨度错配、低 token 概率和多字符 BPE 合并；即使手动拆字符 token，局部对齐仍坍缩到同一时刻，不能承担保留语音硬保护。
- 继续调整 RMS、固定补偿或扩到整个 ASR token 都无法区分 `得/你`，会在残留尾音和误删下一字之间摆动。

独立真实样片自动化 gate 已通过固定 `fa-zh v2.0.4`，详见 `research/fa-zh-spike-results.md`。`得/你` 的旧 `37.190s` 切点在真实 FFmpeg/AAC 后仍被二次 ASR 识别出被删“都觉得”；`37.810s` 不再返回残留，且下一“你”的 PCM 相关、延迟和 RMS 与旧点一致。人耳盲听仍保留到最终真实媒体验收。

Windows 隔离环境实测约 `1.266GB`、峰值 RSS 约 `997MB`、模型冷加载约 `4.2-7.5s`、热推理约 `0.05-0.18s/句段`。这些数据允许继续实现，但 Mac Intel/Apple Silicon 依赖和运行验证仍是默认发布前的硬 gate。

## 3. Ownership And Data Model

### 3.1 Semantic ranges

- `textRanges[].originalStart/originalEnd`：文字选择语义，继续规范到完整自然字符。
- `timelineRanges[].originalStart/originalEnd`：用户确认的精确拖拽范围，不扩成完整文字字符。
- `noSpeechRanges`：无语音删除语义，继续按现有保留文字扣除规则处理，不做强制对齐。

### 3.2 Physical ranges

- `textRanges[].start/end` 与 `timelineRanges[].start/end`：唯一媒体切点，草稿 PUT 阶段生成并持久化。
- 公共预览、播放跳过、`/cuts`、`/compose` 和 FFmpeg 只消费物理范围。
- retained transcript 用 `original*` 决定删除哪些字符，再用物理范围重映射剪后时间。

旧 timeline 项缺少 `original*` 时，兼容读取为 `originalStart=start`、`originalEnd=end`；不扫描或改写现有 jobs/history。

### 3.3 Acoustic alignment cache

在 job 工作目录保存原子写入的对齐 sidecar，不覆盖原始 `words/asrWords`。缓存记录至少包含：

```text
schemaVersion
sourceFingerprint
aligner = "funasr-fa-zh"
modelRevision
segments[] = {
  segmentKey,
  spokenTextFingerprint,
  envelopeStart,
  envelopeEnd,
  characters[] = { text, start, end },
  validation,
}
```

`segmentKey` 由源媒体指纹、归一化可发声文本、粗句段包络、模型 revision 和算法 schema 组成。新转写在 `process_job()` 已有 PCM 与 transcript 时预计算；旧任务在首次影响对应句段的草稿保存时惰性补齐。进程内使用惰性单例和锁复用模型，sidecar 使用临时文件后 `Path.replace`。

用户修改文案后，仅当可发声字符序列和 fingerprint 仍一致时复用；否则只重算相关句段。撤销、重做和重复 PUT 命中缓存，不重复全片推理。

## 4. Alignment Validation

对齐结果必须全部满足才可进入边界解析：

1. 归一化后的字符数量和顺序完全一致，不按“长度差不多”猜映射。
2. 对齐输入必须是完整 ASR 句段、完整已知可发声文本及有限音频上下文；短窗局部对齐结果不得进入边界解析。
3. 所有时间 finite、非负、单调且 `end > start`，并整体位于完整句段上下文包络内。
4. `asrWords` 只用于建立字符顺序映射和记录时间偏差，不作为逐字符时间硬包络。对齐逃出粗 token 但仍符合完整句段、quiet range 和单调结构时可以有效。
5. 相邻字符不能整体坍缩到同一点；删除区间两侧必须为保留字符留下正时长声学核心。
6. 强制对齐与粗 token 明显冲突时记录偏差诊断；只有完整句段文本错配、字符结构无效、越出句段包络或保留字符无正声学核心时拒绝。
7. 若固定模型 revision 不提供 per-token confidence，不伪造置信度；分别记录结构校验和波形一致性。若真实样片证明必须依赖 posterior score，则回到设计阶段评估 CTC 对齐。

降级顺序为：有效强制对齐加极小窗去爆音微调 -> 现有受限共享波形边界 -> 规范后的语义/请求边界。所有降级都以不跨入保留字符为硬不变量，并记录明确 reason。

## 5. Shared Boundary Resolver

将现有文字专用校准提升为一次处理全部端点的 `resolve_cut_draft_acoustic_boundaries(...)`。它在一次 PCM 解码/缓存读取中完成：

1. 规范 text/timeline 的原始语义范围。
2. 按字符序列标记删除与保留状态。
3. 为每个相邻“删除/保留”状态转换建立唯一 boundary key。
4. 优先使用完整句段强制对齐中左字符 `end` 与右字符 `start` 的共享转换证据。
5. 只在两者间隙或转换点附近的极小窗口内寻找过零/低振幅点以消除爆音；PCM 不再决定字义边界。
6. 同一 boundary key 在 AI 建议、文案草稿和 timeline 吸附中只计算一次。

对于“删除在左、保留在右”，最终点不得早于可信删除尾点，也不得晚于右侧保留字符起音。存在非负 quiet gap 时，文字删除物理终点仍使用被删字符可靠尾点；是否删除后续 quiet gap 继续由 `noSpeechRanges` 决定。反向边界对称处理。若模型区间重叠，使用经验证的唯一转换点；不得向下一字符说完后的静音搜索。

高能量局部谷值不能仅凭相对 fallback 改善获得资格。强制对齐缺失时，现有波形算法只作为保守降级，失败时宁可保留原范围，也不以固定毫秒扩张。

## 6. Manual Timeline Policy

timeline 项保存双范围：

- `original*` 永远保留鼠标确认的精确范围。
- 每个物理端点只在距离高质量字符状态转换不超过 `0.20s` 且不会跨越保留声学核心时吸附。
- 完全落在无语音区域、没有可靠候选或位于字符核心且无法判断用户语义时，`start/end` 保持 `original*`。
- 起点与终点分别解析；不能因为一端可吸附就猜测另一端。

前端二次确认后可以先显示 pending 请求范围，但必须在 cut-draft PUT 成功后原子应用 text/timeline 的最终物理范围，更新当前撤销快照而不新增历史项。旧响应继续受 expected signature/revision 保护，不能覆盖新拖拽。

## 7. Cross-Layer Data Flow

```text
DashScope transcript + source PCM
  -> fa-zh known-text character alignment
  -> validated/cached acoustic characters

AI text / manual text / manual timeline intent
  -> PUT cut-draft + revision
  -> one shared acoustic boundary resolver
  -> persisted semantic ranges + physical ranges + diagnostics
  -> frontend atomically applies authoritative draft
  -> preview / MediaController / Store frame
  -> /cuts or /compose with cutDraftRevision
  -> FFmpeg consumes persisted physical ranges only
  -> retained transcript uses semantic deletion + physical retiming
```

`generateCut()` 和统一预览/compose 在取最终 frame 前必须等待最新草稿保存完成。新客户端附带 `cutDraftRevision`，服务端按该 revision 读取权威草稿；过期或缺失返回冲突而不是把保存前范围当最终范围。旧客户端不带 revision 时继续保持现有扁平 `ranges` 兼容行为。

## 8. Diagnostics

草稿或 sidecar 保存通用边界诊断，至少包含：入口类型、端点方向、requested/fallback/final、alignment source/revision、相邻字符、保留起音硬限、结构校验结果、PCM 微调量和 fallback reason。日志不得包含媒体内容或凭证。

健康/任务状态应能区分：模型可用、模型下载/加载失败、文本不匹配、结果无效和安全降级，避免功能表面开启但实际长期运行旧算法。

## 9. Dependency And Packaging

- 固定 `funasr==1.4.2`、`modelscope==1.39.1`、`torch/torchaudio==2.9.1+cpu`、Windows `charset-normalizer==3.4.4` 与 `fa-zh v2.0.4` 模型提交/权重校验和，不使用浮动 alias。
- 模型必须缓存到 `DATA_DIR/models`，不能依赖用户 home 的隐式缓存。
- 模型下载、加载和推理失败必须可诊断，并不得破坏原有转写/草稿保存。
- Mac 包继续不携带本机模型、jobs/history 或密钥；需验证 Intel/Apple Silicon 安装路径、首次下载提示和离线安全降级。
- 模型只在需要对齐时惰性加载，不增加普通健康检查的冷启动耗时。

## 10. Rollout And Rollback

先用真实样片和合成用例通过 adapter gate，再接入新转写，最后统一 timeline 与生成 revision。每一阶段保持可独立回滚：

- 回滚 adapter：删除新 sidecar/依赖调用，原始 transcript 不受影响。
- 回滚 timeline 吸附：旧 `original*` 可直接恢复精确物理范围。
- 回滚生成 revision：保留现有 ranges 匹配兼容路径。

不得批量删除对齐缓存；缓存 schema/revision 变化时按 key 自然失效。

## 11. Verification Strategy

- Adapter：完整句段文本归一化、结果结构、缓存 key、重复短语、长 quiet gap、模型缺失/失败和单句失效。
- Boundary：`觉得/你`、`给/一`、连续高能量、重叠字符、短保留字岛、增益/采样率/声道性质测试。
- Draft/API：三入口同一点、timeline 双范围、revision 冲突、重复 PUT 幂等、响应原子应用。
- Generation：保存竞态关闭，`/cuts`/`/compose` 不再调用对齐器，物理/语义范围各自一致。
- Media：短真实 FFmpeg fixture 加用户真实样片只读 gate；同时检查被删音节不可辨识、下一保留字完整、二次 ASR 和边界前后 PCM/频谱。
- Frontend：Node 契约与真实 Chromium，覆盖旧响应、撤销/重做、刷新、公共 Store、立即生成和 375px。
- Release：Windows CPU 冷启/内存/1、3、10 分钟耗时，Mac 依赖与包内容，全量 pytest 和 `git diff --check`。
