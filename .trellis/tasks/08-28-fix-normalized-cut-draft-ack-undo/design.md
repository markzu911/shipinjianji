# 规范化剪辑草稿确认与撤销修复设计

## Root Cause

服务端 PUT 在返回前已经把草稿持久化并推进 revision，同时会把时间量化到毫秒、把 speech-safe 范围的物理 `start/end` 吸附到安全音频边界。前端保存队列先比较未经同等量化的语义签名，签名不等便抛错；`cutDraftRevision`、acknowledged snapshot 和服务端对齐应用都没有执行。UI 随后可按本地 history 撤销，但补偿保存仍携带旧 revision，因此服务端权威删除无法清除。

## State Contract

一次 PUT 响应分为三个独立判断：

1. **提交身份**：响应属于当前 in-flight request、job 和 generation。
2. **权威版本**：响应 revision 是有限正整数且严格大于请求 revision。200 响应已经持久化，因此通过此门槛后立即更新本地权威 revision。
3. **结构兼容**：比较命令集合身份而不是时间数值；要求各集合 key/数量/唯一性、文字、初始化标记、boundary mode 和 split ownership 一致。服务端规范化后的语义/物理时间均可变化。只有结构兼容响应才能成为 acknowledgement 候选。

`cutDraftRevision` 表示浏览器已知的服务端最新版本；`cutDraftAcknowledged` 表示某个本地语义签名已被该版本确认。两者不能再被当作同一个状态：服务端若提交了协议异常响应，revision 仍须推进，但当前签名不得被标记为已保存。

## Frontend Changes

### Structural Response Identity

新增单一结构校验入口，在修改 live state 前完成以下验证：text/no-speech/timeline/split 集合数量相同、key 唯一且集合相同，文字身份不变，`automaticNoSpeechInitialized` 一致，timeline `boundaryMode`/`splitClipKey` 一致。所有时间数值由服务端规范化后返回，不能再用 request 与 response 数值全等决定是否合法。

现有 semantic signature 继续描述浏览器当前完整语义状态，用于保存去重和 desired/ack 比较；服务端 snapshot 安装后重新构造 payload 和 post-normalization signature。不能只对旧签名执行三位小数取整，因为自然字符边界规范化会合法改变文字 `original*`，no-speech 和 split 也需要同步安装。

### Atomic Normalized Snapshot Installation

扩展既有服务端对齐 owner，使其先构造完整的 text map、no-speech map、timeline ranges 和 normalized split points，通过全部结构校验后再一次性替换 live state。随后协调当前 history endpoint，并用安装后的 payload/signature 更新 desired、ack、本地缓存、retained projection guard、Store 和时间轴。任何构造/校验失败都不得留下部分 state。

### Successful Response Transition

`persistCutDraft()` 按以下顺序处理 200 响应：

1. 校验 response draft 与递增 revision；
2. 立即记录响应 revision，避免已经提交的响应被当成网络失败；
3. 验证结构命令身份；结构不一致进入可恢复错误状态，不设置 acknowledged；
4. 若 request 仍是当前 desired，原子安装完整服务端 snapshot、协调 history，并重建 post-normalization desired/signature；
5. 用 post-normalization signature 记录 acknowledgement，随后同步 localStorage、retained projection、Store、时间轴和保存提示；
6. 若 desired 已更新，只确认旧请求和 revision，不回写旧 snapshot；finally 继续现有 latest-state-wins 保存。

对齐失败与结构身份不一致仍显示错误，但不能回退已经确认的服务端 revision。`cutDraftFailedSignature` 继续阻止同一异常签名无限自旋；撤销或其他不同签名可携带新 revision 继续保存。

## History And Refresh

沿用 `reconcileCurrentCutHistorySnapshot()`：服务端物理范围应用后，把当前 transaction 的 `after` 替换为规范化 snapshot。这样 undo 回到用户操作前状态，redo 回到已经规范化的状态，不会重新引入未确认的原始物理边界。

每次 undo/redo 仍走现有 `updateSelectionSummary()` 和保存队列。保存成功后 localStorage 使用服务端 snapshot；刷新从服务端/本地恢复时二者语义和 revision 一致。

## Tests

- 浏览器路由 fixture 模拟真实服务端：PUT revision 单调增加，文字/静音/timeline/split 数值规范化，speech-safe `start/end` 扩宽，并持久保存供 GET/刷新恢复。
- 新回归覆盖 `删除 -> 规范化确认 -> undo -> redo -> refresh`，逐步断言请求 revision、服务端范围、保存状态和刷新结果。
- 增加结构不一致分支：响应已经推进 revision，但缺失/重复 key、文字或 split ownership 变化不得显示成功；下一不同操作必须使用新 revision。
- 复跑现有 burst、in-flight rebase、failed retry、refresh、split_exact 和真实 cut-draft API 测试。
- 修改 `app.js` 后同步 `web/index.html` 资源版本与静态契约断言。

## Compatibility And Rollback

- API schema 不变，不迁移既有 `cut-draft.json`；旧草稿恢复继续使用同一字段。
- 修改集中在前端保存确认状态机和测试，不改变服务端 VAD 输出。
- 若出现回归，可整体回滚结构身份校验、响应 transition、完整 snapshot 安装和对应资源版本；持久草稿仍保持现有 schema，可直接由旧版本读取。
