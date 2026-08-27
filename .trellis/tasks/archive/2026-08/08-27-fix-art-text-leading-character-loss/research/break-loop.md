## Bug Analysis: 文案修改拆分删除后艺术字首字缺失

### 1. Root Cause Category

- **Category**: B/C/D/E - Cross-Layer Contract / Change Propagation Failure / Test Coverage Gap / Implicit Assumption
- **Specific Cause**: 前端逐 cue 用旧 source midpoint 判断当前字符是否存在，把物理锚点误作语义身份；文字保存只刷新 editable 状态而遗漏 source segments/字符 cache；后端又用 repository schema 不接受的 `art.status = null` 表示旧成片失效。单元测试此前只覆盖相同锚点和单次保存，没有执行真实“修改 -> 拆分 -> 删除 -> 连续快照覆盖”链路。

### 2. Why Fixes Failed (if applicable)

1. 只改逐 cue 筛选会修复截图中的首字，但缺少/无效 transcript projection 会把整轨 suppressed，属于 incomplete scope。
2. 只同步可见 cue 文字会让 `_cutReconciliation` 仍持有旧文案，后续删除/恢复会复活错误基线，属于 change propagation failure。
3. 只验证 ArtModel/Store 会漏掉 `status: null` 破坏下一次快照覆盖，以及旧 `currentSegments` 扩大删除范围，属于 cross-layer test gap。

### 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | 同一 `trackId` 全轨单调 partition，`nextCut.transcript` 唯一决定字符身份并执行全文/timing 数量守恒 | DONE |
| P0 | State consistency | 正常和 stale-effect job 读取统一同步 source/editable/boundaries/cache | DONE |
| P0 | Persistence | 艺术字失效使用合法 `interrupted + retryable`，连续 text/split PUT 后重新 load 快照 | DONE |
| P0 | Test coverage | 真实锚点漂移、projection 缺失/占位/显式空、suppressed 恢复、浏览器完整操作与无媒体 reload | DONE |
| P1 | Documentation | 更新 frontend、backend 和 cross-layer Trellis 规范 | DONE |

### 4. Systematic Expansion

- **Similar Issues**: 任何按旧 source/edited 区间独立过滤当前语义对象的 overlay、PiP 或 transcript 投影；任何只刷新 editable/source/cache 其中一份的异步 effect；任何用非法空状态表达派生媒体失效的子任务。
- **Design Improvement**: 对跨 cue 语义变换统一采用“语义身份守恒 + 物理锚点仅作分界偏好”；对权威 job 响应提供单一领域同步入口。
- **Process Improvement**: 复杂编辑器 bug 的回归必须从真实用户操作一直走到 Store、timeline、preview、compose 和持久化重载，不能停在模型单测。

### 5. Knowledge Capture

- [x] 更新 `.trellis/spec/frontend/architecture-and-state.md`
- [x] 更新 `.trellis/spec/backend/persistence-and-jobs.md`
- [x] 更新 `.trellis/spec/guides/cross-layer-thinking-guide.md`
- [x] 更新当前任务 research、设计和回归清单
- [x] 确认项目不存在 `src/templates/markdown/spec/`，无模板副本需要同步
- [ ] 提交由用户另行授权；本次按用户约束保留为未提交变更
