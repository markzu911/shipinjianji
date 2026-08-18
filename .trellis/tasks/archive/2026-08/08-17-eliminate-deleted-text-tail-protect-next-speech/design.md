# 文字裁剪共享声学边界设计

## Boundaries And Ownership

- 文字语义层：`originalStart/originalEnd` 与自然分词派生的字符单元决定“删哪些字”。
- 原始声学层：`segments[].asrWords` 提供模型返回的 token 文本和起止时间，只用于建立局部声学走廊。
- 物理媒体层：`textRanges[].start/end` 使用共享声学边界，决定 FFmpeg 实际拼接点。
- 剪后文案层：retained transcript 只按文字语义层删除和重定时，不能用物理扩张再次删字。

## Root Cause

现有 `split_timed_text_units` 在自然词时间内按字符数均分时长。该值适合选择和兼容回退，却不代表实际音节交界。`build_transcript_delete_boundary_limits` 又把下一保留字符的均分开始时间当作硬上限，导致两种互斥失败：停在均分点会留下被删音节；越过均分点找低谷则可能吞掉下一字符。解决点必须是重新估计两者共享的实际交界，而不是继续调整固定 guard。

## Acoustic Character Alignment

1. 逐段归一化 `words` 与 `asrWords` 的可发声字符序列，忽略空白和标点。只有字符序列一致时才建立声学映射；不一致时该段回退现有字符时序。
2. 将每个自然字符映射回覆盖它的原始 ASR token。token 边界继续作为强锚点；token 内部边界以按字符比例得到的时间作为先验，不把 token 整体扩展进删除范围。
3. 对实际位于“删除/保留状态切换”的字符边界做按需细化，不为所有字符全量扫描。搜索走廊限制在相邻字符先验中心之间，并截断到所属原始 token 的起止时间。
4. 在走廊内以 `5ms` 步长计算多尺度短窗能量，候选评分同时考虑局部 RMS、相对两侧能量下降比例和距先验点的偏移。先选择满足相对改善阈值的最近低谷，再把最终点吸附到附近的低振幅/过零位置以减少拼接爆音。
5. 所有结果按字符顺序保持单调，并保留相邻字符的最小有效核心。候选超界、非有限、走廊过短或无相对改善时，使用原字符先验。

## Shared Boundary Contract

- 增加后端唯一所有者，输入 `segments + semantic delete ranges + PCM samples + duration`，输出每个删除范围的安全物理起止点和对应保护限制。
- 删除范围起点取“上一保留字符 / 第一删除字符”的共享点；终点取“最后删除字符 / 下一保留字符”的共享点。
- 同一字符交界无论被相邻哪个范围引用都只计算一次，结果按边界键缓存，避免两个范围独立吸附到不同位置。
- `snap_delete_ranges_to_samples` 保留通用媒体低谷能力，但文字裁剪传入已经细化的共享目标和严格限制，不再把机械字符开始时间当成不可调整的下一字声学起点。
- 多个范围的 `0.12s` 合并仍受 retained character ranges 保护，不因新物理点重新跨过保留字符。

## Data Flow

```text
natural words -> semantic character units -> delete semantics
asrWords + source PCM -> constrained shared acoustic boundaries
delete semantics + shared boundaries -> textRanges.start/end
textRanges.start/end -> preview / cut / compose media
originalStart/originalEnd -> retained transcript / delete UI state
```

## API And Compatibility

- 不增加前端必填字段；草稿 PUT 继续返回现有 `textRanges` 结构。
- 新转写和已有带 `asrWords` 的内存任务自动获得细化能力。
- 旧历史缺少 `asrWords`、ASR 文本与修正文案不一致或音频解码失败时，按段回退现有字符级语义边界。
- 前端无需实现波形分析，只应用带 revision/signature 校验的后端草稿响应；预览和生成继续消费已保存的 `start/end`。
- 不修改 `data/jobs`、`data/history` 文件格式，也不做迁移。

## Failure And Safety

- 删除/保留交界是唯一允许细化的边界；纯保留字符内部不会被媒体裁剪访问。
- 下一保留字符保护由同一个共享边界表达，不允许额外尾部 guard 在其后继续搜索。
- 若细化无法证明候选优于先验，返回先验；安全退化允许少删残音，不允许猜测性吞掉保留文案。
- 真实媒体验收失败时先调节走廊与相对评分，不扩大到完整 `asrWords` token。仍无法通过时停止并将 forced alignment 拆为独立任务。

## Validation Strategy

- 单元测试使用合成 PCM 表达不等长字符、连续发声低谷、无可信低谷、首尾边界和跨 token 形状。
- 契约测试覆盖 `给一`、`得你`，断言语义范围不变、物理共享点可移动、保留字符核心不被覆盖。
- API/生成测试断言草稿 PUT、预览、剪辑与组合只使用一次对齐结果，重复 PUT 不漂移。
- 真实媒体只读验证：用源 `source.mp4` 和现有草稿生成临时成片；对第一处拼接点输出前后短音频，运行完整二次 ASR，并人工试听下一字符完整性。

## Rollback

- 新声学细化应封装在文字边界所有者内；回滚时移除该细化并恢复现有字符先验回退，不影响字符级语义保护、`asrWords` 保存或其他未提交任务。
