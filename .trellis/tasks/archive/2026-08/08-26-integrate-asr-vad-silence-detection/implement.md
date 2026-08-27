# 实施计划

## 1. 实施顺序与依赖

本任务保持一个父任务，因为 VAD 证据、相邻字符 resolver、editable segment 投影和 cut draft 必须共享同一数据契约。实现阶段可以并行开发独立适配器与测试，但合并顺序固定：

1. VAD 运行时适配与纯单元测试。
2. 共享边界数据结构和三结果 resolver。
3. 初始系统分段、用户文案拆分与 cut draft 接入。
4. 前端段落/时间轴投影和实时预览 skip。
5. 跨层、真实媒体与完整回归。

后续步骤依赖前一步公开契约，不允许前后端分别手写另一套 boundary key 或方向规则。

## 2. VAD 运行时适配

### Files

- 新增 `server/voice_activity_detection.py`
- 新增 `tests/app/test_voice_activity_detection.py`
- 更新 `tests/app/conftest.py`

### Checklist

1. 固定 FSMN-VAD alias/revision/权重大小/SHA-256，复用 `DATA_DIR/models`。
2. 实现 CPU 模型单例、加载锁、推理锁、公开 speech range 归一化和稳定失败 reason。
3. 接口只接受本地 16 kHz mono WAV 与显式 duration；拒绝 non-finite、逆序、越界和错误 shape。
4. 测试模型只加载一次、并发推理串行、相邻范围合并、无 speech、越界/非数字结果、下载/校验/加载/推理失败。
5. 应用 autouse fixture 替换真实 VAD runner，普通测试不得访问用户模型目录或网络。

## 3. 共享相邻字符 resolver

### Files

- 更新 `server/app.py`
- 视实际边界类型需要更新 `server/schemas.py`
- 更新 `tests/app/test_cut_acoustic_boundaries.py`
- 更新 `tests/app/test_cut_draft.py`

### Checklist

1. 定义稳定 boundary key：媒体 fingerprint、左右 source segment/字符 ordinal/text、FA/VAD revision 和 schema。
2. 扩展现有 transition context，保留完整重复短语、跨段邻接、retained hard limit 和 deletion direction。
3. 为每个局部窗口生成唯一临时 WAV；调用 VAD 后把 range 映射回 source time，所有退出路径清理临时文件。
4. 将 VAD non-speech 与现有 `5ms` step、`20/40/80ms` PCM floor 相交；交集存在时输出同一点的 `neutral/deleteLeft/deleteRight`。
5. 无可信交集时输出方向性 aggressive 三结果；删除左/右分别以完整移除被删尾音/首音为第一优先级，不使用固定 padding。
6. VAD unavailable 时沿用 forced+PCM 并输出 `mode=fallback`；和 `mode=aggressive` 明确区分。
7. 统一诊断字段并让文字、普通 timeline 和 editable segment 复用同一 resolver/cache。
8. 保持 `split_exact` 路径对 FA/VAD/PCM 调用数为零。

### Tests

- 可信 VAD+PCM 静音交集，三个 final 相等且位于交集。
- VAD non-speech 但 PCM 无持续 floor、PCM 低谷但 VAD 仍 speech、VAD 返回 onset/end padding。
- 连续共发音时 `deleteLeft != deleteRight`，分别无被删尾/首音。
- 重复“一起给”、完整“得/你”上下文、跨段删除、立即起音、双侧夹短保留字。
- 单点、一个 `5ms` 凹点、均匀低能、单调斜坡、轻噪声和多组非削波增益。
- 同 key 跨 AI/text/timeline/editable 路径一致；不同字符实例不得缓存串用。
- VAD/PCM/FA 失败、临时文件清理、PCM cache 启用/禁用等价。

## 4. 系统分段与用户文案拆分

### Files

- 更新 `server/app.py`
- 更新 `web/app.js`
- 更新 `web/index.html` 的资源版本（若 `app.js` 版本由 HTML 固定）
- 更新 `tests/app/test_cut_draft.py`
- 更新 `tests/app/test_frontend_contracts.py`
- 更新 `tests/app/browser/test_editor_workflows.py`

### Checklist

1. `process_job()` 在 ASR/FA 后批量解析初始 editable segment 相邻边界，写入 additive `editableSegmentBoundaries` 和 `mediaStart/mediaEnd`。
2. `split` 保留选择字符语义，只解析新产生的最多两个边界；`merge_*` 删除内部记录；`text` 使受影响 key 失效并重算/降级。
3. endpoint 响应与 job result 原子安装更新后的 segments/boundaries，随后使用既有 project snapshot 持久化。
4. 历史结果缺少新字段时按现有语义时间显示并在首次相关操作时惰性解析，不批量迁移。
5. 前端文案列表、编辑弹窗时间和 `#cutFrameTimelineText` 使用 `mediaStart/mediaEnd`；原片字符选择仍使用语义 `start/end/words`。
6. 刚拆分时显示 neutral；删除左/右侧后用对应 final 更新物理范围和展示时间。一次操作只产生一次可见提交，不 reload 基础视频。
7. stale job/response 不得覆盖新文案或新分段；拆分失败保持弹窗可恢复并显示稳定错误。

### Tests

- 初始系统分段拥有共享 media boundary。
- 截图对应流程：选择中间文字拆成三段，前/后两个边界均解析并立即更新可见时间。
- 删除左段与右段分别选择正确 directional final；刷新后边界不漂移。
- 拆分 -> 合并、拆分 -> 修改文字、连续拆分、标点前缀/后缀和跨原始 word。
- endpoint VAD 失败仍成功返回 fallback；不存在媒体/无效文本沿用既有 4xx。
- Store/project revision、基础 video `src/load()`、当前播放位置和工具 identity 不被分段重绘破坏。

## 5. cut draft、预览与生成一致性

### Files

- 更新 `server/app.py`
- 更新 `web/app.js`
- 更新 `tests/app/test_cut_draft.py`
- 更新 `tests/app/test_cut_rendering.py`
- 更新 `tests/app/test_composition.py`
- 更新 `tests/app/browser/test_editor_workflows.py`

### Checklist

1. cut draft resolver 从 job result 读取并复验匹配的 editable boundary record；缺失/失效时调用同一 resolver。
2. 根据左右字符 deleted state 选择 `deleteLeft/deleteRight`，将 final 写入 `textRanges/timelineRanges.start/end` 和 `boundaryDiagnostics`。
3. 保持 `original*` 和 `transcriptRanges` 语义不变；retained transcript 不因 aggressive 物理范围丢失未选字符身份。
4. `/cuts`、`/compose` 和公共预览只使用匹配 revision 的持久化物理范围；测试生成阶段 FA/VAD/PCM 调用数为零。
5. 在唯一播放帧时钟中执行删除区间 skip；seek 后不使用旧 source time 更新高亮/时间线，`timeupdate` 仅作为降级。
6. 分别记录“预览是否短暂播放删除音频”和“FFmpeg 文件是否包含残音”，避免通过扩大物理范围掩盖调度缺陷。

### Tests

- 服务端 PUT 返回、磁盘 `cut-draft.json`、Store frame、preview payload、compose payload 和 FFmpeg ranges 完全一致。
- 保存期间继续编辑、revision conflict、生成前 flush、刷新恢复和服务重启恢复。
- rVFC、RAF、timeupdate 三种时钟下删除开始处立即跳转，旧 callback generation 不写新状态。
- `/cuts` 与 `/compose` 真实短媒体生成，音频范围和 retained transcript 双重断言。

## 6. 文档、打包与兼容

### Files

- 更新 `README.md`
- 更新 `tools/build_mac_package.py`
- 更新 `tests/test_build_mac_package.py`

### Checklist

1. 说明 FSMN-VAD 固定模型、首次下载大小、缓存位置和失败降级。
2. 不新增 requirements；Windows/macOS 继续使用既有 FunASR/Torch 条件依赖。
3. 打包产物不包含本机模型、jobs、history、用户视频或任务测试产物。
4. 旧 job/cut draft 缺少 boundary 字段时继续可打开、拆分、保存和生成。

## 7. 验证命令

定向验证：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_voice_activity_detection.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_acoustic_alignment.py tests/app/test_cut_acoustic_boundaries.py tests/app/test_cut_draft.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_cut_rendering.py tests/app/test_composition.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_frontend_contracts.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser/test_editor_workflows.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_build_mac_package.py
node --check web/app.js
```

完整质量门：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

真实模型 gate 必须单独标记，普通测试不触发下载：

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m vad_integration
```

最后对用户提供的只读视频执行：原始目标区间 -> 产品 resolver 诊断 -> FFmpeg 最终输出 -> 拼接点前后局部 WAV/频谱 -> 人耳试听。必须分别验证被删首音/尾音为零和保留表达仍可理解。

## 8. 风险与回滚点

- FSMN-VAD 公共输出有 padding 且可能把连续口播合并为 speech；不得依赖私有 frame probability，PCM exact 和 aggressive fallback 是必要路径。
- 初始全部段落局部 VAD 可能增加转写完成延迟；先批量复用模型和音频窗口，只有证据表明需要时再增加缓存，不缓存不带 identity 的动态结果。
- `server/app.py` 是高耦合文件；优先保持现有 helper 签名并提取单一 resolver，避免同时重构无关转写/渲染代码。
- editable segment 新字段是 additive；出现恢复或投影回归时可关闭 enrichment，旧语义字段仍可工作。
- VAD 接入失败可回滚 `voice_activity_detection.py` 调用并使用现有 FA+PCM；已经保存的 cut draft 物理范围仍可生成。
- 不修改真实 `data/jobs`、`data/history` 或用户附件；真实视频和模型缓存只读验证，不提交到仓库。

## 9. 2026-08-27 retained editable projection 复核

### 审查修复

- `build_retained_transcript()` 对非对象、非法 `sourceSegmentIndex`、非整数 source index 和跨 source 逆序的历史 `editableSegments` 改为整体 legacy fallback，避免 cut-draft GET/PUT 因增量字段损坏返回 500。
- 用户执行 editable `split` / `merge_*` 后同步重建已有 completed edit 的 retained transcript，避免当前编辑器已分段但 history/已生成 edit 文案仍保留旧大段分组。
- 服务端投影保持同一 `editableSegmentId` 的非连续 retained runs，不跨被删内部字符合并；每个 run 的 word 和 source anchors 独立保留。

### 新增覆盖

- 重复短语、标点归属、跨 source segment 的顺序映射。
- 非对象、null/非法/非整数 source index、跨 source 逆序的 legacy fallback。
- 内部删除不桥接，且 segment/word `sourceStart/sourceEnd` 不丢失。
- editable split -> merge 连续操作刷新 completed edit projection。
- 真实服务端 cut-draft 投影在浏览器中安装、刷新，并渲染同一 editable id 的两个分离 run。

### 验证证据

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_acoustic_alignment.py tests/app/test_cut_acoustic_boundaries.py tests/app/test_cut_draft.py tests/app/test_cut_rendering.py tests/app/test_composition.py tests/app/test_frontend_contracts.py
# 212 passed, 1 existing deprecation warning

.\.venv\Scripts\python.exe -m pytest -q tests/app/browser/test_editor_workflows.py
# 48 passed

.\.venv\Scripts\python.exe -m pytest -q
# 457 passed, 1 existing deprecation warning
```

本轮只修改开发工作区；未提交、合并、推送、部署，也未修改真实用户 job 或媒体数据。
