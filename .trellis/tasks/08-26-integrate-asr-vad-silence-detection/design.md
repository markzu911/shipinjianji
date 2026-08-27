# 技术设计

## 1. 设计目标与不变量

本任务把 ASR/强制对齐、FSMN-VAD 与 PCM 组合成一个相邻字符边界解析器，而不是把 VAD 接到全局静音建议层。

核心不变量：

- ASR/`fa-zh` 决定左右字符身份和局部搜索包络。
- VAD 判断局部窗口中的 speech / non-speech，PCM 在可信 non-speech 中选择精确采样点。
- 用户语义与媒体物理时间分层；物理吸附不得反写字符身份或 `originalStart/originalEnd`。
- 有静音时左右删除共享同一点；无静音时保留中性、删除左侧、删除右侧三个结果。
- cut draft 是删除物理范围权威；预览和生成只消费已保存范围，生成阶段不重新运行声学解析。

## 2. 当前根因

### 2.1 强制对齐不是最终采样边界

`fa-zh` 能给出字符级候选，但目标重复短语的下一保留“一”曾出现约 `20ms` 漂移。现有 PCM 逻辑可找相对低谷，却不知道低谷是否属于真实 non-speech，容易在被删音节内部短凹点或下一字低能起音间选错。

### 2.2 全局 VAD 粒度不足

目标 `27s-32s` 在 FSMN-VAD 中是一个连续 speech 区间。全局 VAD 补集不能定位字符转换；局部裁剪结果也有 onset/end padding，不能直接作为 FFmpeg 切点。VAD 只提供局部 speech/non-speech 约束，最终点仍由 PCM 选择。

### 2.3 用户文案拆分沿用均分 token 时间

`apply_transcript_segment_operation()` 通过 `editable_segment_character_tokens()` 将词时间均分到字符，再由 `build_editable_segment_from_tokens()` 直接写入新段落 `start/end`。该路径没有调用现有声学 resolver，因此用户拆分出的段落会继承不真实的字符边界。

### 2.4 实时预览可能晚于声学边界跳转

浏览器共享播放帧回调更新视觉状态，但跳过删除范围依赖 `timeupdate`。即使 FFmpeg 物理范围正确，低频事件仍可能短暂播放删除区间，需要在同一播放帧时钟中处理 skip。

## 3. 数据契约

### 3.1 相邻字符身份

边界 key 由以下稳定字段生成：

```text
source media fingerprint
left sourceSegmentIndex + left spoken-character ordinal + character
right sourceSegmentIndex + right spoken-character ordinal + character
fa-zh model revision + VAD model revision + boundary schema version
```

重复文字不能只用文本生成 key；跨段转换必须同时包含左右 source segment 和字符序号。

### 3.2 边界记录

job result 新增 additive `editableSegmentBoundaries[]`，每条记录至少包含：

```json
{
  "key": "...",
  "left": {"segmentIndex": 3, "characterIndex": 8, "text": "人"},
  "right": {"segmentIndex": 3, "characterIndex": 9, "text": "一"},
  "semanticFallback": 28.328,
  "neutral": 28.299,
  "deleteLeft": 28.304,
  "deleteRight": 28.294,
  "mode": "silence",
  "diagnostic": {}
}
```

- `mode="silence"` 时三个 final 收敛到同一无声走廊。
- `mode="aggressive"` 时 `deleteLeft` 与 `deleteRight` 可不同，`neutral` 只用于尚未删除时展示。
- `mode="fallback"` 表示 VAD 不可用，仍提供 `fa-zh + PCM` 结果与稳定原因。

`editableSegments[].start/end/words` 保持语义 ASR 时间；新增 `mediaStart/mediaEnd` 作为用户可见和媒体投影时间。相邻段的 `mediaEnd/mediaStart` 引用同一边界记录。前端生成文字删除范围时，`original*` 取语义时间，物理 `start/end` 取对应方向的媒体时间。

### 3.3 持久化

- 初始系统分段和用户文案拆分产生的记录随 job result / `project-state.json` 保存；历史结果缺字段时按需重建，不批量迁移。
- cut draft 继续在 `cut-draft.json` 持久化最终 `textRanges/timelineRanges.start/end` 与 `boundaryDiagnostics`。
- `acoustic-alignment.json` 只保存静态完整句段 forced 证据；VAD/PCM 动态转场可信度和删除方向不得写入该 sidecar。
- 生成只读取匹配 `cutDraftRevision` 的物理范围。

## 4. VAD 运行时

新增 `server/voice_activity_detection.py`，采用已有 FunASR 依赖中的 FSMN-VAD：

- 模型：`iic/speech_fsmn_vad_zh-cn-16k-common-pytorch`
- alias：`fsmn-vad`
- revision：`v2.0.4`
- `model.pt`：`1,721,366` bytes
- SHA-256：`B3BE75BE477F0780277F3BAE0FE489F48718F585F3A6E45D7DD1FBB1A4255FC5`
- 输入：16 kHz 单声道局部 WAV；输出归一化为相对窗口的 speech ranges。

模块职责：

- 固定模型身份、revision、权重大小和哈希，使用 `DATA_DIR/models`、CPU、`disable_update=True`。
- 按模型缓存目录进程内单例加载；加载锁与推理锁分离。
- 校验 finite、单调、正时长且位于局部窗口内的范围，合并重叠结果。
- 把运行时、下载、校验、加载、推理和返回结构错误映射为稳定 reason。
- 不依赖 FunASR 私有 frame probability；只消费公开 speech range。

建议接口：

```python
def analyze_local_voice_activity(
    audio_path: Path,
    duration: float,
    model_cache_dir: Path,
) -> dict[str, Any]: ...
```

局部音频由调用层在 job 目录创建唯一临时 WAV，成功或失败后删除。普通测试必须替换 runner，不能访问真实模型目录或网络。

## 5. 共享边界算法

### 5.1 建立转场上下文

1. 从 source transcript 生成稳定可发声字符单元，保留 source segment/character identity。
2. 使用现有完整句段 `fa-zh` sidecar复验左右字符；无效记录按现有策略惰性重算。
3. 结合语义 fallback、forced 字符包络、相邻 retained hard limit 和现有重复转场 context 建立局部窗口。
4. 局部窗口包含左右字符的必要上下文，但候选切点只能落在两字符转换走廊或方向性 aggressive hard limit 内，不做任意全局搜索。

### 5.2 VAD 与 PCM 融合

1. 对局部 WAV 运行 FSMN-VAD，将 speech ranges 加回 source offset。
2. 计算局部 non-speech 补集，并与字符转换走廊相交。
3. 使用现有 `5ms` step 和 `20/40/80ms` 多尺度 RMS 查找持续低能 floor；单点尖谷、均匀低能、单调斜坡和被删音节内部短凹点不能成为静音走廊。
4. 只有 VAD non-speech 与持续 PCM floor 有有效交集时才判定 `mode="silence"`；在交集中选择最低振幅采样点，`neutral/deleteLeft/deleteRight` 共享该点。
5. VAD 的 onset/end padding 只限制粗走廊，不能直接作为最终点；PCM exact point 必须保持方向、hard limit 与 finite interval 不变量。

### 5.3 无静音的方向性 aggressive 结果

VAD 可用但无可信交集时：

- `deleteLeft`：从被删左字符尾部向右推进，以删除其完整衰减为优先；可最小幅度进入右侧保留字符起音，但不得越过该相邻字符的声学主体包络。
- `deleteRight`：从被删右字符起音向左推进，以覆盖其完整起音为优先；可最小幅度削弱左侧保留字符尾部，但不得越过该相邻字符的声学主体包络。
- `neutral`：选择两方向结果之间的稳定低振幅/forced 中性点，只用于未发生删除时的段落显示。
- 禁止固定毫秒 padding；推进停止条件来自删除侧持续语音消失与保留侧 hard limit。

VAD 运行失败时复用现有 forced/PCM resolver 生成同样三个字段，`mode="fallback"` 并记录原因。VAD 失败与“VAD 成功但没有静音”必须可区分。

### 5.4 统一入口与缓存

在 `server/app.py` 提取/扩展唯一 `resolve_adjacent_character_boundary()`：

- 初始系统 editable segments、用户文案拆分和 cut draft 都调用该入口。
- 同一请求中的文字/timeline 路径复用既有 forced boundary cache、PCM fingerprint cache 和新增 local VAD cache。
- job 中已有边界记录只有在媒体 fingerprint、左右 identity、模型 revision 和 schema 全部匹配时才复用；文本编辑或源媒体变化自然失效。
- 不能仅以 `validation.valid`、相同文本或全局偏差阈值复用动态结果。

## 6. 业务接入

### 6.1 初始系统分段

`process_job()` 完成 ASR、editable segment 构建和 `fa-zh` 对齐后，批量解析所有相邻 editable segment 边界，写入 `editableSegmentBoundaries` 和每段 `mediaStart/mediaEnd`。VAD 失败只降级边界，不让转写任务失败。

### 6.2 用户文案拆分/合并

`PUT /api/transcriptions/{job_id}/editable-segments`：

- `split` 先保持现有字符分组语义，再只解析新产生的最多两个相邻边界。
- `merge_up/merge_down` 删除被合并的内部边界，保留外侧仍有效记录。
- `text` 修改使受影响段落两侧 key 失效，按新字符 identity 重算或安全降级。
- 响应 additive 返回 `editableSegments` 与 `editableSegmentBoundaries`；写入 job result 后继续使用现有 snapshot 持久化。

前端 `web/app.js`：

- 文案列表和 `#cutFrameTimelineText` 优先投影 `mediaStart/mediaEnd`。
- 删除前仍用语义时间构造 `original*`；确定删除方向后使用边界记录中的 `deleteLeft/deleteRight` 构造物理范围。
- 服务端响应只在当前 job/操作仍匹配时安装，随后一次性重绘文字列表、时间轴与 Store，不 reload 基础视频。

### 6.3 cut draft、预览与生成

- `resolve_cut_draft_acoustic_boundaries()` 通过同一 boundary key 复用/解析三个结果，并根据相邻字符 deleted state 选择方向。
- cut draft PUT 保存选择后的 final 与完整诊断；后续响应和 retained transcript 继续区分语义/物理范围。
- `/cuts`、`/compose`、公共预览和最终 FFmpeg 只读取权威 draft `start/end`，不得再次调用 FA/VAD/PCM。
- 时间轴播放头 `split_exact` 仍完全跳过声学解析，保持原契约。

### 6.4 实时预览

把删除区间 skip 合并到唯一播放帧时钟：每帧先用预计算 spans 判断源时间是否进入删除范围，命中时立即 seek 到该范围末端并终止本帧旧时间的视觉更新。`timeupdate` 只保留兼容降级，不能建立第二条播放循环。

## 7. 失败、兼容与回滚

- 新字段全部 additive；历史 job、旧草稿或旧前端缺少字段时使用语义/现有 forced+PCM 路径。
- VAD 模型失败公开稳定 reason，不返回原始异常、绝对路径或模型响应。
- 无数据库迁移，不改写 `data/jobs`、`data/history` 或用户附件。
- requirements 无新增 Python 包；README 与 Mac 包说明补充第二个固定模型的大小、缓存和降级。
- 回滚时可关闭 VAD 适配与 editable boundary enrichment，恢复现有 forced+PCM；已保存 cut draft 物理范围仍可继续生成，新增 JSON 字段会被旧代码忽略。

## 8. 验证重点

- 合成 PCM 分别覆盖可信静音、连续共发音、删除左侧、删除右侧、重复短语、跨段边界、立即起音、单点/斜坡/均匀低能和多组非削波增益。
- 同一 boundary key 在系统分段、用户文案拆分、文字删除与 timeline 删除中返回相同三元结果。
- 拆分、合并、文字修改、刷新恢复和草稿 revision 不产生过期边界或二次漂移。
- 浏览器预览与 FFmpeg 分开断言，不用扩大删除范围掩盖帧调度问题。
- 用户视频做最终局部试听与频谱验收；二次 ASR 不能替代人耳门槛。
