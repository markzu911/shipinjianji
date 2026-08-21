# 最新相邻重复文案残音证据

## Sample

- 用户成片：`C:\Users\jiadi\Downloads\飞书20260728-152857-当前预览版 (7).mp4`
- SHA256：`1E9721BAF5F951C7879F0C74D3A67E83C271F20F2AAA6034B2667C097D599418`
- 成片时长：约 `145.500s`
- 产品 job：`d87e13fe-8f83-4712-97fc-a9b6eb4f717f`
- 只读导出：`C:\Users\jiadi\AppData\Local\Temp\codex-residual-audio-20260820\job.json`
- 临时证据目录：`C:\Users\jiadi\AppData\Local\Temp\codex-residual-audio-20260820`

## Reproduction

成片约 `111s` 的残音对应源视频删除范围 `139.760-142.010s`。原文案相邻出现两次“所以说啊”，草稿删除第一次、保留第二次：

```text
semantic delete: 139.760-141.156
persisted physical delete: 139.760-142.010
diagnostic: adjacentCharacters=["啊", "所"]
structureValid=true
retainedSpeechHardLimit=142.010
```

当前物理终点直接来自 structurally valid forced alignment。

## Alignment Evidence

任务本地重新运行 segment 14 的完整句段 `fa-zh v2.0.4`，sidecar 位于：

`C:\Users\jiadi\AppData\Local\Temp\codex-residual-audio-20260820\alignment-segment-14\acoustic-alignment.json`

关键字符：

| 实例 | 字符 | start | end |
| --- | --- | ---: | ---: |
| 第一次 | 所 | 140.050 | 140.210 |
| 第一次 | 以 | 140.210 | 140.410 |
| 第一次 | 说 | 140.410 | 140.650 |
| 第一次 | 啊 | 141.850 | 142.030 |
| 第二次 | 所 | 142.030 | 142.190 |

结果的 34 个字符数量和顺序正确、时间 finite 且单调，所以 `validation.valid=true`；同时记录：

```text
coarseTokenMappingValid=true
coarseTokenMaxBoundaryDeviationSeconds=1.043
coarseTokenMaxEscapeSeconds=0.874
```

这证明结构校验没有识别重复实例错位。

## Independent Boundary Evidence

- 独立 ASR 把保留的第二次“所以说啊”起音放在约 `141.880s`。
- 当前 `142.010s` A/B 拼接在局部二次 ASR 中产生“被抓/比如说”等伪词，说明切点进入了保留语音。
- 使用 `141.880s` 拼接时，局部二次 ASR 能正确识别保留的“所以说啊”。
- 临时片段：`splice-current-142010.wav` 与 `splice-retain-141880.wav`。它们只用于本地验证，不进入仓库。

## Ruled Out

- FunASR 依赖、模型加载或服务运行失败：服务与实际模型已可用，segment 14 对齐成功。
- AAC 帧或 fade 带回已删除语音：错误已经存在于传给 FFmpeg 的物理恢复点。
- 上一轮“得/你”：该端点实际为 `37.791s`，被删尾音相关仅 `0.107`，保留“你”波形完整，不是本次主要残音。
- 源 `105.8-106.0s` 保留岛：该区间为静音，已对齐被删“限”结束于 `105.598s`。

## Root Cause

`server/acoustic_alignment.py:285` 的句段校验只证明结构可用；`server/acoustic_alignment.py:338` 的粗 token 偏差只作为诊断；`server/app.py:3139` 随后把结构可用等同于当前转场可信。相邻重复文本让强制对齐产生了“结构合法但重复实例归属错误”的结果，现有测试没有覆盖该类别。

不能用全局 coarse-deviation threshold 修复，因为此前真实有效的“得/你”对齐会合法逃出粗 ASR 两秒以上。修复应在删除/保留转场层识别重复歧义，并要求局部 PCM 持续谷底佐证。

## Frontend Fragment Evidence

截图中的“人”“你身”不是后端独立段。导出 job 的 `editableSegments` 保留完整句子；孤立行来自前端 presentation 投影混用物理范围：

| 字符 | 中点 | 位于物理 suggestion | 位于语义删除 |
| --- | ---: | --- | --- |
| 人 | 28.3345 | 是，物理起点 28.328 | 否，语义起点 28.454 |
| 你 | 37.300 | 是，物理终点 37.791 | 否，语义终点 37.120 |
| 身 | 37.660 | 是，物理终点 37.791 | 否，语义终点 37.120 |
| 边 | 38.020 | 否 | 否 |

`selectedTextRangeKeysAtTime()` 已使用 `original*` 判定 restore；`suggestionTextRangeKeysAtTime()` 却使用物理 `start/end` 生成 presentation key。于是“人”和“你身”仍是 edit 状态，却因 presentation key 与相邻 retained 字符不同而被 `buildSegmentTextRuns()` 拆成独立行。

修复边界：suggestion 展示优先使用 `originalStart/originalEnd`，旧数据缺失时回退 `start/end`；媒体删除继续使用物理范围，不能为了修 UI 收回声学校准。
