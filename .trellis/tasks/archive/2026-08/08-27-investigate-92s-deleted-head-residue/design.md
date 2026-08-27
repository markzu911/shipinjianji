# Technical Design

## Scope

主修改面限定为 `server/app.py` 中 same-segment、non-repeat、delete-start 的 forced/PCM transition corroboration。测试主入口为 `tests/app/test_cut_acoustic_boundaries.py`，必要时补充 cut draft、retained transcript 与 rendering 的一致性测试。

## Existing Data Flow

```text
semantic text selection / editable split
  -> adjacent character transition
  -> forced candidate + retained speech hard limit
  -> VAD silence corridor check
  -> PCM transition corroboration
  -> directional deleteRight boundary
  -> cut draft physical range
  -> retained transcript / preview / FFmpeg
```

当前故障发生在 PCM transition corroboration：证据窗口名义上跨过 candidate，但扫描提前停止；失败后 forced candidate 又被无条件提升为可信。它不是持久化、timeline 映射或 FFmpeg 执行错误。

## Boundary Contract

对 deleted-head 转换定义三个不同角色，禁止混用：

- `retainedSpeechHardLimit`：最终边界的最早保护界限，不是默认切点。
- `forcedCandidate`：forced alignment 给出的参考点和最终边界的最晚上界，不是天然可信的声学起音。
- post-candidate samples：只用于确认 candidate 附近是否存在 sustained attack，不得直接被选为删除起点。

成功结果必须满足：

```text
retainedSpeechHardLimit <= finalBoundary < forcedCandidate
finalBoundary belongs to the confirmed pre-attack quiet run
pcmValleyStart <= finalBoundary <= pcmValleyEnd < pcmAttackConfirmationEnd
```

`finalBoundary` 应由通用 PCM step、持续 quiet blocks、持续 attack blocks 和相对能量阈值推导；不得引入针对本样本的偏移常量。

## Algorithm Change

1. 保留现有有限 probe window，但允许扫描器消费 window 内 candidate 之后的 block 来确认持续起音，不再用 `candidate + 1ms` 截断证据。
2. candidate 之后的 block 只能补足 attack confirmation。候选 attack 必须与 candidate 邻近，并且其前方存在满足现有相对能量阈值和最小持续 block 数的 quiet run。
3. 找到第一个可信 quiet-to-attack 后，从该转换对应的、且不晚于 candidate 的低能区选择保守 deleted-head 边界。helper 直接返回这个边界，并让 diagnostics 描述同一个决定。
4. 返回前统一 clamp 到 `[retainedSpeechHardLimit, forcedCandidate)`。若离散采样下无法得到严格早于 candidate 的可信点，则返回 `None`，不得伪造 PCM 成功。
5. forced transition 的其他既有成功路径保持原状。same-segment deleted-head 佐证失败时返回 `None`，不再把 forced candidate 标为可信；下游沿用受 retained hard limit 保护的 deletion-direction waveform fallback，并保留真实 failure reason，便于测试和诊断。

## False-Positive Controls

- 至少两个 quiet block 和两个 attack block 保持现有持续性门槛。
- 使用相对 RMS 改善与 `boundary_rms_is_meaningfully_lower()`，保证非削波增益等价。
- 均匀低能没有 attack，不成功；均匀高能没有 quiet run，不成功。
- brief dip、single sample、monotonic rise 和轻微噪声不能仅凭局部最小值成功。
- 多个 attack 时选择 retained limit 之后第一个满足完整证据的转换，避免后续语音把更早的真实 deleted onset 覆盖。

## Compatibility

- 不改 API schema、cut draft 格式、cache key、VAD 模型或历史数据。
- `originalStart/originalEnd` 的语义层不变，只调整新解析得到的物理 `start`。
- 历史已保存 draft 不批量迁移；用户重新触发相关解析/保存时按现有流程产生新边界。
- 用户点击文案拆分只改变 editable segmentation；相邻字符仍经过同一个 acoustic transition resolver，因此无需为拆分来源建立第二套算法。

## Cross-Path Audit

- 检查 repeated transition 的 PCM valley、quiet gap、retained-limit fallback 是否也把 candidate 后证据错误截断。
- 检查 cross-segment PCM fallback 的扫描边界和失败 trust 语义。
- 若两条路径已正确返回 `None` 且由 waveform fallback 接管，只增加覆盖说明，不修改它们。

## Verification Strategy

- 纯 helper 参数化测试验证波形结构、边界不变量和 diagnostics。
- resolver 测试同时覆盖 text range、timeline range、editable split 产生的同一 transition，并比较最终物理点。
- cut draft / retained transcript / render 测试验证下游只消费保存边界且不重新推理。
- 真实附件生成局部对照，记录 resolved point、波形证据和可试听片段；自动断言不能替代用户已定义的听感门槛。

## Rollback

变更应局限于 helper、对应 trust/fallback 分支和测试。若真实媒体或完整回归出现相邻保留句丢失，回滚该局部算法修改，不修改用户数据、不回退既有 VAD/ASR 功能。
