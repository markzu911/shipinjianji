# Bug Analysis: 重复文案结构合法但实例错切

## 1. Root Cause Category

- **Category**: B/E - 跨层契约与隐式假设
- **Specific Cause**: alignment sidecar 的 `validation.valid` 只证明字符序列与时间结构可解析，shared resolver 却隐式把它当成删除/保留转场的语义授权。相邻重复文本使模型可以输出单调、完整但实例归属错误的字符时间。前端又把物理 `start/end` 当 suggestion 展示边界，造成未选字符孤立分组。

## 2. Why Fixes Failed

1. 固定尾部扩张或直接信任 forced end：能去除部分尾音，但会进入下一次重复表达。
2. 全局 coarse deviation 阈值：能拒绝当前错位，却会误伤已验证的“得/你”大偏差正确边界。
3. 仅调整物理边界：媒体可能正确，但展示仍混用物理范围，继续出现“人”“你身”孤立行。
4. 首轮重复检测只验证“所以说啊”内部谷底并用简化“得/你”fixture 做非回归；放回完整上下文后，“你身边…觉得 / 你身边…觉得…”也被正确识别为重复，但无内部双肩谷底，于是错误退回 `37.120s`。缺失的是“forced candidate 后独立 quiet gap”这一可信类别。

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | 在共享 resolver 建立 transition-level trust，文字和 timeline 复用 | DONE |
| P0 | Runtime | 重复 forced 候选必须获得持续、相对 PCM 谷底佐证 | DONE |
| P0 | Test Coverage | 覆盖重复/局部重叠/同字、无谷底、增益和“得/你”保护 | DONE |
| P0 | Test Coverage | “得/你”使用完整重复上下文，并覆盖 forced-gap、gap 高能、缺少两侧语音、overlap 与 delete-start 对称 | DONE |
| P0 | Cross-layer Contract | 展示只读 `original*`，媒体只读物理 `start/end` | DONE |
| P1 | Documentation | 更新 backend/frontend/testing 与跨层检查规范 | DONE |

## 4. Systematic Expansion

- **Similar Issues**: 任何模型输出包含重复实体、重复字幕或同名素材时，都不能用结构校验替代实例身份校验。
- **Design Improvement**: 静态模型/cache validity 与依赖当前编辑状态的动态 trust 分层；动态 trust 再区分内部 PCM 谷底和 candidate 后独立 quiet gap，后者只授权 candidate 本身，绝不推进到 gap 尾部。
- **Process Improvement**: 媒体边界回归必须使用能触发真实分类的完整上下文，双向证明“删干净”和“保留完整”，并检查展示语义没有消费物理校准范围。

## 5. Knowledge Capture

- [x] 更新 `.trellis/spec/backend/media-and-timeline.md`
- [x] 更新 `.trellis/spec/frontend/architecture-and-state.md`
- [x] 更新 `.trellis/spec/testing/index.md`
- [x] 更新 `.trellis/spec/guides/cross-layer-thinking-guide.md`
- [x] 本仓库没有 `src/templates/markdown/spec/`，无需模板同步
