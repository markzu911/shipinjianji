# Bug Analysis: 重复文案结构合法但实例错切

## 1. Root Cause Category

- **Category**: B/D/E - 跨层契约、测试覆盖缺口与隐式假设
- **Specific Cause**: alignment sidecar 的 `validation.valid` 只证明字符序列与时间结构可解析，shared resolver 却隐式把它当成删除/保留转场的语义授权。相邻重复文本使模型可以输出单调、完整但实例归属错误的字符时间。后续保护机制又把低噪声从约 `11` 到 `16` 的微小相对上升当成保留起音，使 `29.171-29.790s` 与 `122.370-124.248s` 的删除过早停止。前端则同时用源时间和剪后时间渲染同一列表，造成可见时间倒序。

## 2. Why Fixes Failed

1. 固定尾部扩张或直接信任 forced end：能去除部分尾音，但会进入下一次重复表达。
2. 全局 coarse deviation 阈值：能拒绝当前错位，却会误伤已验证的“得/你”大偏差正确边界。
3. 仅调整物理边界：媒体可能正确，但展示仍混用物理范围，继续出现“人”“你身”孤立行。
4. 首轮重复检测只验证“所以说啊”内部谷底并用简化“得/你”fixture 做非回归；放回完整上下文后，“你身边…觉得 / 你身边…觉得…”也被正确识别为重复，但无内部双肩谷底，于是错误退回 `37.120s`。缺失的是“forced candidate 后独立 quiet gap”这一可信类别。
5. 第二轮只根据保留侧相对能量上升停止删除：噪声底的轻微波动也满足相对条件，保护区被错误提前，所有整段删除继续在新段落前留下尾音。
6. 首版 retained-side gate 只挂在 `alignment_wrong_direction` 分支：“一起给”的 candidate 恰好等于 semantic fallback，真实 `29.171s` 仍未进入新逻辑。必须在内部谷底和 forced gap 都失败后统一进入第三证据路径。
7. 列表保留行通过 live spans 显示剪后时间，完整删除行却回退源时间；单独检查任一行都合理，组合后才暴露 `00:28 -> 00:19` 倒序。

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | 在共享 resolver 建立 transition-level trust，文字和 timeline 复用 | DONE |
| P0 | Runtime | 重复 forced 候选必须获得持续、相对 PCM 谷底佐证 | DONE |
| P0 | Test Coverage | 覆盖重复/局部重叠/同字、无谷底、增益和“得/你”保护 | DONE |
| P0 | Test Coverage | “得/你”使用完整重复上下文，并覆盖 forced-gap、gap 高能、缺少两侧语音、overlap 与 delete-start 对称 | DONE |
| P0 | Runtime | retained hard limit 只在终端持续低能且保留侧有连续语音肩部时授权，最终点严格不越界 | DONE |
| P0 | Test Coverage | candidate==fallback、wrong-direction、孤立爆音、无保留语音、多增益和失败 hard-limit 保留均有回归 | DONE |
| P0 | Cross-layer Contract | 展示只读 `original*`，媒体只读物理 `start/end` | DONE |
| P0 | Cross-layer Contract | 行 data 保留源时间，所有可见徽标统一映射为剪后时间，完整删除行折叠到拼接点 | DONE |
| P1 | Documentation | 更新 backend/frontend/testing 与跨层检查规范 | DONE |

## 4. Systematic Expansion

- **Similar Issues**: 任何模型输出包含重复实体、重复字幕或同名素材时，都不能用结构校验替代实例身份校验。
- **Design Improvement**: 静态模型/cache validity 与依赖当前编辑状态的动态 trust 分层；动态 trust 区分内部 PCM 谷底、candidate 后独立 quiet gap 和 retained hard-limit terminal gate。最后一类必须同时观察 hard limit 两侧，不能把“相对能量上升”单独当成语音。
- **Process Improvement**: 媒体边界回归必须使用能触发真实分类的完整上下文，双向证明“删干净”和“保留完整”，并用真实草稿重放所有已知拼接点。任何同时携带 source/edited 坐标的列表还要做整体单调性测试，不能只测单行格式。

## 5. Knowledge Capture

- [x] 更新 `.trellis/spec/backend/media-and-timeline.md`
- [x] 更新 `.trellis/spec/frontend/architecture-and-state.md`
- [x] 更新 `.trellis/spec/testing/index.md`
- [x] 更新 `.trellis/spec/guides/cross-layer-thinking-guide.md`
- [x] 本仓库没有 `src/templates/markdown/spec/`，无需模板同步
