# 删除首字残音声学边界设计

## 1. Boundary Contract

语义删除仍由 `originalStart/originalEnd` 决定；本次只改变物理 `start`。对于相邻字符状态从 retained 变为 deleted 的 delete-start：

1. `left._forcedEnd` 是前一保留字符的硬保护下界。
2. `right._forcedStart` 是被删首字符的模型候选上界，不再自动成为最终点。
3. 在两者之间以及候选右侧极小探测窗中读取现有 PCM，确认“保留语音结束 -> 持续低能 -> 被删语音持续抬升”的顺序。
4. 证据成立时选择持续低能走廊靠近被删语音一侧的低振幅采样；证据不足时保持 forced candidate，不做固定 padding。

本例的数据流为：

```text
retained “人” forced end 28.050
  -> sustained quiet corridor
  -> deleted “一” PCM attack about 28.300
  -> forced start 28.330

current final 28.328  -> leaves attack
new final about 28.29 -> removes attack, remains > 28.050
```

## 2. Implementation Shape

- 在 `server/app.py` 的共享声学 helper 层新增或抽取一个 delete-start head corroboration helper，沿用现有多尺度 RMS、相对阈值、步长和低振幅 sample snap。
- helper 只消费现有 `samples/sample_rate/fallback/left_end/right_start`，不读取文件、不触发模型。
- 在普通、结构有效且非重复歧义的 `forced_alignment_transition_boundary()` delete-start 分支中调用；delete-end 和已有 repeat/cross-segment 分支保持原路径。
- PCM 证据成立时返回提前后的 final，并使用独立 `trustReason`（如 `forced_deleted_head_pcm_valley`），同时填充 `pcmCorroborated`、`pcmValleyStart/End`、`retainedSpeechHardLimit` 和 `pcmAdjustment`。
- PCM 证据不足时继续返回现有 forced transition，保持兼容与安全降级。

优先复用现有 `multiscale_boundary_rms()`、`boundary_rms_is_meaningfully_lower()`、`snap_to_low_amplitude_sample()` 和采样步长；不复制解码、缓存或 range 投影逻辑。

## 3. Evidence Rules

- 走廊必须位于 `[left_forced_end, right_forced_start]` 内，最终点不得越过任一端。
- 走廊需有连续多个低能 block，不能接受单点尖谷。
- forced candidate 之前或附近必须出现持续高于走廊 floor 的被删起音，避免把纯静音中的任意点解释为语言边界。
- retained hard limit 左侧应存在持续保留语音或已有可信 forced end；结果始终 `>= left_forced_end`。
- 所有门槛使用相对能量，不使用素材相关的绝对音量阈值。

## 4. Compatibility And Data Flow

边界仍在 cut-draft PUT 时一次解析并持久化：

```text
text/timeline intent
  -> resolve_cut_draft_acoustic_boundaries
  -> shared delete-start PCM corroboration
  -> persisted physical start + diagnostics
  -> preview / cuts / compose consume persisted range
```

不新增 schema 必填字段；旧草稿、旧 diagnostics 和缺少对齐/PCM 的任务继续沿现有兼容路径。生成阶段不重新分析。

## 5. Rollback

改动限定在一个共享 helper、forced delete-start 接入点和对应测试。若真实素材或回归发现误伤，回滚该接入即可恢复现有 forced candidate 行为，不影响语义范围、缓存或媒体文件。
