# Implementation Plan

## Ordered Steps

1. 在 `tests/app/test_cut_acoustic_boundaries.py` 先补失败回归：构造 quiet run 在 candidate 前、持续 attack 需要 candidate 后 block 才确认的波形，证明当前实现错误返回未佐证 candidate。
2. 参数化 candidate 相对 attack 的偏移、gain、轻噪声和多 attack；补齐 uniform high/low、brief dip、single point、monotonic rise 反例。
3. 修改 `corroborate_forced_deleted_head_with_pcm()` 的证据扫描与 final boundary 选择，确保 post-candidate 只参与 attack confirmation，返回点来自 pre-attack quiet run。
4. 修正 same-segment deleted-head 失败后的 trust/fallback 诊断，避免 PCM 失败被无条件标记成可信 forced transition；保持其他 transition 类型现有语义。
5. 增加 resolver 级测试，断言 `retainedLimit <= final < forcedCandidate`、diagnostics 与返回值一致，并保留 attack 完全位于 candidate 前的现有结果。
6. 覆盖用户点击文案拆分后的 editable segment、text range 和 timeline range，断言相同字符 transition 使用同一 resolved physical point。
7. 审计 repeated/cross-segment 路径的 lookahead 与 trust 降级；只在发现同类逻辑时做最小修复，否则记录测试证明其不受影响。
8. 验证 cut draft、retained transcript、预览/FFmpeg 使用同一保存点，生成阶段 FA/VAD/PCM 调用增量为零。
9. 用真实附件运行局部 media gate，目标边界约 `118.995s`（一个 PCM step 容差），确认被删首音消失且前后保留表达存在。
10. 运行相关测试、完整测试和 diff hygiene，整理变更供用户确认；不推送、不合并、不部署。

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_cut_acoustic_boundaries.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_cut_draft.py tests/app/test_cut_rendering.py
.\.venv\Scripts\python.exe -m pytest -q tests/app
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

真实媒体 gate 使用本地附件和匹配 job，只写入任务临时目录；不得改写 `data/jobs/b7692265-d8e3-4829-8eba-b4bfc4f1d793`、history 或附件本身。

## Risk And Rollback Points

- 风险：lookahead 放宽后把 candidate 后的独立语音误当成本次起音。控制：邻近窗口、持续 quiet/attack、第一可信转换和反例测试。
- 风险：选择过早边界损伤左侧保留句。控制：retained hard limit 下界、真实媒体试听和前后文双向验收。
- 风险：helper 返回值与 aggressive resolver 二次调整不一致。控制：helper 直接返回最终保守点，resolver 和 diagnostics 断言同一点。
- 风险：共享 resolver 影响重复/跨段行为。控制：限定 same-segment non-repeat 分支并审计相邻路径。

每完成一个风险点都先跑定向测试。若保留句丢失或反例出现假阳性，停止扩大修改，回退最近的局部算法步骤并重新收紧证据条件。

## Implementation Evidence

- 失败回归先行：candidate 相对缓升起音 `-3ms/0ms/+3ms`、不同非削波增益和轻噪声的 3 组样本在旧实现均返回 `None`；candidate 后独立 quiet gap 再出现晚到 attack 的反例在无限 lookahead 中错误返回 `0.505s`。
- 最终 helper 只允许由 `CUT_BOUNDARY_STEP_SECONDS` 和两个持续 attack block 推导的邻近 lookahead；post-candidate 样本只确认 attack，成功点直接取 pre-attack sustained quiet edge，并严格满足 `retainedLimit <= final < forcedCandidate`。
- same-segment non-repeat delete-start 在 PCM 未佐证时保持 `boundaryTrustworthy=False`，以 `forced_deleted_head_pcm_not_corroborated` 进入方向性 waveform fallback；fallback 下界受 `retainedSpeechHardLimit` 保护。
- 文字删除、手动 timeline 删除和用户点击文案拆分的 editable boundary 回归共享同一 `deleteRight` 点；VAD 连续语音的 aggressive 模式下 helper、最终边界和 diagnostics 一致。
- 真实源片只读 PCM gate：`retainedLimit=118.608s`、`forcedCandidate=119.008s` 时返回 `118.995s`；`pcmValley=118.995-119.010s`、`pcmAttackStart=119.015s`，命中用户已试听接受的切点。未改写 job、history 或用户附件。
- repeat 审计：`corroborate_transition_with_pcm()` 只扫描 fallback 与 candidate 的封闭走廊，不读取 candidate 后证据；失败返回 `None`。cross-segment 审计：同样使用封闭走廊，失败保留 `cross_segment_pcm_not_corroborated`，且不调用 deleted-head helper。两条路径无需代码修改。
- 最终新增/受影响定向选择：`17 passed`；修改中完整声学边界回归 `102 passed`；cut draft + rendering `62 passed`；acoustic alignment `14 passed`。仅出现既有 Starlette/httpx deprecation warning。
- 完整应用与全仓测试留给独立 Trellis check 阶段；本实现阶段不提交、不推送、不合并、不部署。

## Independent Check Evidence

- 独立 reviewer 核对媒体时间轴：`source.mp4` 为源时间轴（SHA-256 `F34587E8F453F35F97373051E632F5ABBD86F5412B1F6A9E252A8D848C76E06B`，`184.0s`）；附件、`edited.mp4` 与 `composition.mp4` 为相同剪后文件（SHA-256 `A0DACE1B1911D665E1D6B9C88AE45B3B93BFEDC36FF450888FD4CC7A482AFAB9`，`143.1s`）。禁止把源坐标 `118.608/119.008s` 用于剪后附件。
- 对匹配 job 的 `source.mp4` 只读解码后，helper 在 `retainedLimit=118.608s`、`forcedCandidate=119.008s` 返回 `118.995s`；诊断为 `pcmValley=118.995-119.010s`、`pcmAttackStart=119.015s`。附件只沿用用户已在约 `92.358s` 输出拼接位置完成的试听结论。
- 额外审计 VAD 连续语音且 PCM 不成立的路径：最终输出点与诊断 `final` 一致，`boundaryTrustworthy=False`，并保留 `retainedSpeechHardLimit` 下界。
- 独立验证：声学边界 `102 passed`；acoustic alignment + cut draft + rendering `76 passed`；全仓 `462 passed`。`compileall`、`task.py validate` 和 `git diff --check` 通过；项目未配置独立 lint/type-check 工具。仅出现既有 Starlette/httpx deprecation warning。
- `implement.jsonl` 与 `check.jsonl` 的 seed `_example` 行已删除，各保留 5 条真实规范上下文；任务校验通过。未提交、未推送、未合并、未部署，也未改写真实 job、history 或用户媒体。

## Pre-Start Gate

- `prd.md`、`design.md`、`implement.md` 已通过最终审阅。
- `implement.jsonl` 与 `check.jsonl` 已配置真实 spec context。
- 用户在看到最终规划摘要后另行明确批准实施。
- 在批准前不得运行 `task.py start` 或修改产品代码。
