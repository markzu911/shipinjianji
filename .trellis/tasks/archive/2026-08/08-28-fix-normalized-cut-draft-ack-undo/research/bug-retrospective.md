# Bug Analysis: 服务端规范化响应与前端确认状态分叉

## 1. Root Cause Category

- **Category**: B - Cross-Layer Contract；同时包含 D - Test Coverage Gap 与 E - Implicit Assumption。
- **Specific Cause**: 服务端在 200 前已经持久化并推进 revision，还会规范化文字、静音、时间轴和 split 数值；前端却把 request/response 精确时间签名相等当成成功前提，并在接受 revision 前抛错。它把“命令身份”和“服务端权威数值”混成一个比较，也把 revision 与 signature acknowledgement 混成一个状态。

## 2. Why Fixes Failed

1. 之前主要修 VAD/PCM 切点：解决了被删语音残留，但没有检查规范化响应如何进入前端保存、history 和刷新恢复，属于跨层范围不完整。
2. 既有保存队列测试大多 echo 请求：物理 text 范围变化的 helper 仍保留被签名的字段，无法触发 revision/ack 分叉，属于测试模型与真实服务端不一致。
3. 浏览器按钮和 DOM 看起来正常且没有 console error：只检查可见撤销会误判成功，必须查询 API 并刷新后复核。
4. 初步“时间取三位小数”只能修当前单帧样例：文字自然字符边界、静音和 split 仍会合法改变，不能代表完整问题类别。

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | 分离 `cutDraftRevision` 与 signature acknowledgement；2xx 先接受单调 revision，再做结构身份校验 | DONE |
| P0 | Runtime | 结构兼容时原子安装完整服务端 snapshot，post-normalization 重建 desired/ack/history/projection | DONE |
| P0 | Test Coverage | 浏览器覆盖规范化删除、undo、refresh、redo、refresh，并核对 API/local/history/Store | DONE |
| P1 | Test Coverage | 覆盖结构异常、非法 revision、retained projection、stale rebase 和 pending 选区 | DONE |
| P1 | Documentation | 更新 frontend code-spec、cross-layer checklist 和 testing regression rule | DONE |

## 4. Systematic Expansion

- **Similar Issues**: transcript/cut 在慢声学处理期间的联合版本、local/server `updatedAt` 恢复、多标签 DELETE 无 revision，仍是独立任务，不在本修复中静默扩展。
- **Design Improvement**: 所有“服务端规范化后持久化”的写 API 都应显式区分 command identity、authoritative revision 和 normalized snapshot，禁止 payload 全等充当 acknowledgement。
- **Process Improvement**: 状态型 UI 的回归不能只检查按钮、文案或 console；至少跨一次刷新，并核对服务端持久状态与客户端 Store/恢复副本。

## 5. Knowledge Capture

- [x] 更新 `.trellis/spec/frontend/architecture-and-state.md` 的 cut-draft 可执行契约与测试矩阵。
- [x] 更新 `.trellis/spec/guides/cross-layer-thinking-guide.md` 的规范化写响应检查项。
- [x] 更新 `.trellis/spec/testing/index.md` 的 cut-draft 状态机回归要求。
- [x] 保留联合 transcript/cut revision、local/server 恢复和 DELETE revision 为独立后续优化项。
- [x] 项目不存在 `src/templates/markdown/spec/` 或 `packages/cli/src/templates/trellis/spec/`，无需同步模板镜像。
