# Bug Analysis: 文字删除边界随录音增益漂移

## 1. Root Cause Category

- **E - Implicit Assumption**：共享边界把固定 `CUT_LOW_ENERGY_RMS_THRESHOLD` 当作“已经足够安静”和“候选允许扩张”的通用事实，但 PCM 绝对幅值会随录音增益变化，同一波形结构会因此进入不同分支。
- **D - Test Coverage Gap**：上一轮测试覆盖了若干低谷、真实时间点和相邻字符保护，却没有做统一增益变换的性质测试；方向端点和删除起点 token 补充走廊也没有分别跨过绝对阈值验证。

## 2. Why Fixes Failed

1. 上一轮共享边界修复正确建立了方向和字符走廊，但用“fallback 已低于 500 就停止”避免安静点漂移，把幅值相关经验值误当成了结构不变量。
2. 第一版修复只移除了共享字符走廊的 fallback 提前返回；检查阶段发现方向端点仍以 `RMS <= 500` 获得资格，真实波形在约 `32x` 局部增益时仍会从 `6.329s` 翻回 `6.250s`。
3. 删除起点 token 补充走廊还保留三条绝对阈值分叉；缩小增益时，单调斜坡也可能因落入阈值而被误判为安静端点。
4. 只验证具体尾音样本能证明一次修复有效，不能证明其他文本、音量和边界方向不会再次触发同类分叉。

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | AI 建议和草稿 PUT 复用同一共享声学边界所有者，预览与生成只消费持久化结果 | DONE |
| P0 | Scale-independent decision | 候选使用严格相对改善、局部低谷和走廊谷底形状；固定 RMS 阈值不再决定共享文字边界搜索路径 | DONE |
| P0 | Retained-speech safety | 删除终点不进入下一 token，所有返回统一验证方向和字符走廊，短保留字符岛继续禁用 token 扩展 | DONE |
| P0 | Token extension safety | 删除起点补充走廊要求至少两个相邻采样步长形成持续谷底，且只在显著优于字符走廊候选时使用 | DONE |
| P1 | Property tests | 内部低谷、双向端点和 token 补充谷底在 `1x..64x` 非削波增益下保持稳定；单调斜坡始终回退 | DONE |
| P1 | Cross-entry tests | AI 建议与草稿对相同文字、PCM 产生同一物理边界 | DONE |
| P1 | Real-media gate | 真实 `4.871-6.250s` 只读复算到 `6.329s`，不超过下一字符中心 `6.332s` | DONE |
| P1 | Documentation | 更新媒体时间轴规范和任务设计，记录相对证据、谷底形状与安全回退 | DONE |

## 4. Systematic Expansion

- **Similar Issues**：任何以 PCM 绝对 RMS 决定控制流的文字边界分支都可能随录音增益漂移；内部低谷、方向端点和 token 补充走廊必须分别验证。
- **Design Improvement**：把相对改善、谷底资格和方向/走廊校验收敛为命名辅助函数，使所有共享边界候选使用同一套不变量。
- **Process Improvement**：声学算法修复除了具体回归，还必须包含不改变波形结构的增益变换测试；真实素材只读验证不能替代性质测试。
- **Knowledge Limit**：纯波形启发式无法在没有可证明声学交界的连续语音上同时承诺绝对零残音和绝对不伤下一字；安全回退继续优先保留未删除语音。

## 5. Knowledge Capture

- [x] 更新 `.trellis/spec/backend/media-and-timeline.md` 的共享声学边界合同、错误矩阵、案例和必需测试。
- [x] 更新本任务 `design.md`，移除绝对安静判定并记录增益稳定不变量。
- [x] 增加通用性质、双向端点、token 补充、单调斜坡和跨入口一致性测试。
- [x] 检查模板镜像；仓库不存在 `src/templates/markdown/spec/`，无需同步。

## Validation Evidence

- 定向声学、草稿和渲染测试：`61 passed`。
- 全量测试：`263 passed, 1 xfailed`。
- 编译检查：`python -m py_compile server/app.py` 通过。
- 差异检查：`git diff --check` 通过，仅显示已有 LF/CRLF 提示。
- 真实素材：`4.871-6.250s -> 4.871-6.329s`，下一保留字符声学中心 `6.332s`，候选 RMS 约从 `132` 降到 `22`。
- 数据安全：真实 `cut-draft.json` 和只读 ASR 文件时间戳未变化。
