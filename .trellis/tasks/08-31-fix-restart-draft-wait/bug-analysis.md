# Bug Analysis: 重新开始被草稿保存阻塞

## 1. Root Cause Category

- **Category**: B - Cross-Layer Contract
- **Specific Cause**: 前端把“重新开始”错误地当作生成前保存流程，等待可能触发 VAD 的草稿 PUT；同时缺少服务端放弃代次，单纯取消浏览器请求无法阻止迟到 PUT 在 DELETE 后重新落盘。

## 2. Why Earlier Behavior Failed

1. 前端确认弹窗正常关闭，但后续没有进行中状态，等待保存期间表现为无响应。
2. 只移除前端等待会留下 DELETE/PUT 竞态，修复表象但可能复活草稿。

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | DELETE 推进服务端 write generation，迟到 PUT 持久化前复验 | DONE |
| P0 | Test Coverage | 并发 event 测试锁定 DELETE 后旧 PUT 必须 409 | DONE |
| P1 | Frontend Test | 永不结束的保存 Promise 不得阻塞重新开始 | DONE |
| P1 | Documentation | 在持久化规范和跨层检查中记录放弃语义 | DONE |

## 4. Systematic Expansion

- **Similar Issues**: 任何“取消、重试、切换任务、重新选择视频”与耗时写 API 并发的流程，都不能把客户端 abort 当作服务端取消证明。
- **Design Improvement**: 对会在锁外执行耗时工作的写路由，持久化前必须复验 attempt/generation/revision 所有权。
- **Process Improvement**: 取消类修复必须包含一个“旧请求在取消后才完成”的确定性并发测试。

## 5. Knowledge Capture

- [x] 更新 `.trellis/spec/guides/cross-layer-thinking-guide.md`
- [x] 更新 `.trellis/spec/backend/persistence-and-jobs.md`
- [x] 添加前端不等待与后端迟到写入回归测试
