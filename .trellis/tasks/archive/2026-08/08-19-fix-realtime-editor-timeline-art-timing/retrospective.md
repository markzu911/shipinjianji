# Bug Analysis: 拆分后文案删除不再同步艺术字

## 1. Root Cause Category

- **Category**: C - Change Propagation Failure；D - Test Coverage Gap
- **Specific Cause**: 删除旧 `art-text.js` 运行时时迁移了 ArtTool 的渲染、编辑和保存能力，却没有迁移 `applyEditorCutDraft` 触发的全文轨道重建、锚点艺术字隐藏与撤销恢复。新的 `CUT_TIMING_CHANGED` 只更新 cut 和 cut timeline；已有 Store 测试还把“cut 后艺术字完全不变”写成了断言。

## 2. Why Fixes Failed

1. 前期统一页面只验证 document/video/Store 唯一和面板可用，没有列出旧 cut-draft 消息的全部业务副作用。
2. model 测试只覆盖全文轨道生成和短语匹配，没有覆盖“先添加艺术字，再删除文案，再撤销”的状态序列。
3. UI 迁移以隐藏 DOM 是否存在推断产品需求，误把旧页面中隐藏的文案编辑区暴露为正式功能。

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | `CUT_TIMING_CHANGED` 在一个 Store transaction 中 reconcile cut/art/selection/timeline | DONE |
| P0 | Test Coverage | model、Store、浏览器覆盖单字/整 cue/跨 cue 删除、锚点隐藏、自定义保留和撤销恢复 | DONE |
| P0 | Documentation | 记录 `suppressedOverlays`、草稿恢复和 compose 隔离契约 | DONE |
| P1 | Migration Review | 删除旧运行时前建立“旧事件 -> 副作用 -> 新 owner -> 测试”清单 | DONE |

## 4. Systematic Expansion

- **Similar Issues**: 画中画、AI 草稿、播放跟随等旧页面逻辑也可能包含未显式建模的事件副作用。
- **Design Improvement**: 跨工具业务同步归属 Store/model；UI 组件只派发命令，不持有第二份领域状态。
- **Process Improvement**: 运行时迁移验收必须包含跨工具状态序列，不只检查静态 DOM 和单工具功能。

## 5. Knowledge Capture

- [x] 更新 `.trellis/spec/frontend/architecture-and-state.md` 的可逆 cut-to-art 契约。
- [x] 更新 `.trellis/spec/frontend/picture-in-picture-runtime.md` 的 schema v2 草稿契约。
- [x] 更新 `.trellis/spec/guides/cross-layer-thinking-guide.md` 的旧运行时迁移检查项。
- [x] 增加 model、Store、静态和真实浏览器回归。
