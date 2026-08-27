## Bug Analysis: deleted-head PCM lookahead 被提前截断

### 1. Root Cause Category

- **Category**: E - Implicit Assumption；同时包含 D - Test Coverage Gap。
- **Specific Cause**: 实现把 forced candidate 同时当作“最终切点上界”和“声学证据扫描上界”。PCM probe 虽然配置到 candidate 之后，循环却在 `candidate + 1ms` 停止；需要后续高能 block 才能确认的真实起音因此返回 `None`。失败分支又无条件把 forced candidate 标为可信，导致被删首字的低能起音残留。

### 2. Why Fixes Failed

1. 直接退到 retained hard limit：把保护下界误当最终切点，真实试听导致前后保留表达一起消失。
2. 仅放开 lookahead：能看到 attack，但若仍把成功点 clamp 回 candidate，或扫描整个字符窗口，分别会继续残音或把更晚的独立语音误认成本次起音。
3. 旧测试只覆盖 attack 证据完全位于 candidate 之前，并明确断言失败后保留 forced candidate，没有覆盖“确认 block 跨过 candidate”的实际波形。

### 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | 分离 evidence window 与 final boundary window；post-candidate 只确认 attack，final 严格位于 `[retainedLimit, forcedCandidate)` | DONE |
| P0 | Test Coverage | 参数化 candidate 偏移、增益、噪声、多 attack、晚到独立 attack 和失败 hard-limit 保留 | DONE |
| P0 | Real Media | 用 `source.mp4` 承载 source forced 坐标；剪后附件只按输出拼接时间验证 | DONE |
| P1 | Documentation | 更新媒体时间轴 code-spec 和跨层媒体/坐标检查项 | DONE |
| P1 | Code Review | 检查 helper 返回值、diagnostic final 与外层 resolver 是否描述同一个物理点 | DONE |

### 4. Systematic Expansion

- **Similar Issues**: repeated 与 cross-segment resolver 可能出现相同 lookahead/trust 混用；本次审计确认它们只扫描封闭走廊且失败返回 `None`，无需修改。
- **Design Improvement**: hard limit、forced candidate、evidence lookahead 必须保持三个独立角色，不能由单个时间变量隐式兼任。
- **Process Improvement**: 真实媒体 gate 必须先记录媒体路径、哈希、时长和坐标类型；否则同一个数值落在剪前/剪后媒体上会产生相反结论。

### 5. Knowledge Capture

- [x] 更新 `.trellis/spec/backend/media-and-timeline.md` 的 deleted-head 可执行契约、矩阵、案例和测试要求。
- [x] 更新 `.trellis/spec/guides/cross-layer-thinking-guide.md` 的 source/output 时间轴核对项。
- [x] 任务测试覆盖 text、timeline、用户点击文案拆分和真实 source media gate。
- [x] 项目没有 `src/templates/markdown/spec/` 镜像目录，无模板需要同步。
- [ ] 规范和产品改动按本任务约束暂不提交、推送、合并或部署。
