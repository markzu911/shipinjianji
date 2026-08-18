# Bug Analysis: 删除文字后残音与相邻首字保护

## 1. Root Cause Category

- **B - Cross-Layer Contract**: `originalStart/originalEnd` 的文字语义范围与 `start/end` 的媒体物理范围在后端解析和前端合并时被重新混用，已保存声学边界会被裁回字符先验。
- **E - Implicit Assumption**: 自然字符和原始 ASR token 内的均分时间只是真实交界的先验，不是声学事实；字符中心或 token 边界可能落在音节内部。
- **D - Test Coverage Gap**: 合成低谷单测没有覆盖完整草稿 -> 前端预览 -> `/cuts`/`/compose` -> 真实成片 -> 二次 ASR 链路。

## 2. Why Earlier Fixes Failed

1. 对完整 ASR token 扩张删除范围会吞掉下一保留字符，解决尾音的同时破坏文字语义。
2. 无方向的全局最低 RMS 会选到被删字符或保留字符的中心，真实样本把 `37.120` 错移到 `36.941`，反而留下“得”的后半音。
3. 一律排除字符走廊端点会漏掉真实交界。第一处 `28.337` 是绝对安静端点，保留语义点 `28.454` 时二次 ASR 仍为“所有人一一起给你”。
4. 只用字符中心走廊无法覆盖被 ASR 均摊进相邻 token 的真实停顿。第四处必须在上一 token 内找到 `119.037` 的绝对静音，才能从“在在另一群人”变为“事，在另一群人”。
5. 对删除终点对称开放 token 静音扩展会搜索到下一保留字符说完后的停顿，从而吞掉整个保留字符。

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | 语义边界与物理边界分别持久化并由所有消费者按字段所有权使用 | DONE |
| P0 | Runtime constraint | 删除起点只向前、删除终点只向后；终点禁止 token 扩展 | DONE |
| P0 | Acoustic validation | fallback 已安静时不动；连续语音只接受内部局部谷或绝对安静方向端点 | DONE |
| P0 | Retained-text safety | 短保留字符岛禁用 token 扩展，范围合并继续受保留字符保护 | DONE |
| P1 | Test coverage | 覆盖 `给一`、`得你`、真实停顿、单调坡、后置静音、前后端与生成链路 | DONE |
| P1 | Real-media gate | 临时目录重切完整素材并做完整二次 ASR | DONE |
| P1 | Documentation | 在媒体时间轴规范记录非对称 token 静音扩展和双层字段契约 | DONE |

## 4. Systematic Expansion

- AI 建议、草稿恢复、撤销重做、公共预览、单独剪辑和统一组合都是同一双层范围契约的消费者，任何一个重新规范化 `start/end` 都会使修复失效。
- 波形低能不等于语言字符边界；响亮相对低谷、单调坡和字符中心必须分别测试。
- 真实媒体是声学边界任务的必需质量门，合成 PCM 只能验证约束，不能证明连续中文语流上的效果。

## 5. Knowledge Capture

- [x] 更新 `.trellis/spec/backend/media-and-timeline.md`。
- [x] 保留 `.trellis/spec/guides/cross-layer-thinking-guide.md` 中语义层/权威层检查项。
- [x] 新增后端、前端、端点和真实媒体回归证据。
- [x] 未引入固定毫秒扩张、整 token 删除或新的 forced-alignment 运行依赖。

## Validation Evidence

- Full tests: `167 passed`。
- Real text boundaries: `28.337-29.171`, `33.160-37.190`, `103.080-105.800`, `119.037-122.370`, `139.760-141.156`。
- Full-output ASR: “所有人一起给你画的那条正常的线”；“以前不敢想的事，在另一群人眼中就是家常便饭”。
- Validation artifacts are under `C:\Users\jiadi\AppData\Local\Temp\codex-shared-boundary-validation-20260818` and do not modify `data/jobs` or `data/history`.

## Supplement: 连续已删文案被拆成多行

### Root Cause Category

- **E - Implicit Assumption**: `presentationKey` / `rangeKey` 是剪辑状态的内部身份，不是用户可见的自然段落边界；原合并条件把两者误当成同一概念。
- **D - Test Coverage Gap**: 静态源码断言只能证明字段存在，无法证明跨 key 合并后会通过真实点击委托一次恢复全部范围。

### Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Display contract | 相邻 `restore` 跨 `presentationKey` 合并并聚合全部 `rangeKeys`；保留文字仍切断分组 | DONE |
| P0 | State isolation | `deleted` 时间轴分组和独立空白行继续使用原有展示身份，不受恢复态例外影响 | DONE |
| P1 | Behavior test | Node 回归执行生产点击委托，断言全部 key、历史记录、刷新次数和预览起点 | DONE |
| P1 | Documentation | 更新前端展示边界规范，明确内部状态身份不能直接充当自然展示边界 | DONE |

### Systematic Expansion

- UI 分组必须由用户可见语义决定；内部持久化 key、建议 key 或媒体范围 key 只能作为状态引用。
- 修改聚合展示时必须同时验证聚合操作的反向动作，避免“显示为一段、恢复只处理一部分”的状态漂移。

### Knowledge Capture

- [x] 更新 `.trellis/spec/frontend/architecture-and-state.md`。
- [x] 新增跨 key 合并、保留文字隔断、时间轴分组、空白独立和真实恢复点击回归。
