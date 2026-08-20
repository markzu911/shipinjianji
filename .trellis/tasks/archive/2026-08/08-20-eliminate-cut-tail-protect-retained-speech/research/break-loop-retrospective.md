# Bug Analysis: 裁剪后反复残留被删文案尾音

## 1. Root Cause Category

- **Primary: B - Cross-Layer Contract**：系统没有把“删除哪些文字”的语义范围与“媒体在哪里切”的物理范围贯彻到草稿、前端、预览、生成和 retained transcript 的所有消费者。
- **Secondary: E - Implicit Assumption**：旧实现默认粗 ASR token 内均分字符时间足以代表真实发音边界，并假设相对 RMS 低谷可以补足语言学信息。
- **Secondary: D - Test Coverage Gap**：早期回归集中在波形函数和单入口，没有覆盖真实同 token 连字、手动时间轴、保存竞态、公共 compose 与产品 FFmpeg/AAC 后的二次 ASR。

## 2. Why Fixes Failed

1. **RMS 阈值和局部谷底调整**：只改善了部分静音边界。连续发音中的 `得/你` 没有足够波形证据，旧 `37.190s` 仍位于被删“得”的发音中。
2. **按粗 token 或字符均分扩大范围**：DashScope token 会跨自然字符和在长静音处压缩时间；扩大整个 token 会从残留尾音转成误删下一“你”。
3. **只修文字删除入口**：手动 timeline 仍绕过解析器，AI 建议、草稿 PUT、公共预览与最终生成没有共享同一个权威物理范围。
4. **只等待一次草稿保存 Promise**：等待期间可以继续排入新保存；快速修改后立即生成仍可能读取旧 revision。
5. **只信 sidecar 的 `validation.valid`**：损坏缓存和并发读改写可绕过结构不变量，使重复操作出现不稳定边界。

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
| --- | --- | --- | --- |
| P0 | Architecture | `original*` 唯一表达语义；后端 resolver 唯一生成持久化物理 `start/end`；预览和 FFmpeg 只读物理范围，retained transcript 按语义删除后按物理重定时 | DONE |
| P0 | Linguistic evidence | 只允许完整 ASR 句段 + 完整已知文本的固定 `fa-zh v2.0.4` 对齐决定连续语音字符边界；禁止短窗和粗 token 硬包络 | DONE |
| P0 | Retained-speech guard | 被删字可靠尾点与下一保留字可靠起音分别成为方向约束和硬保护；quiet gap 不随文字删除自动吞并 | DONE |
| P0 | Persistence/runtime | sidecar 指纹、读取时结构复验、按路径串行读改写、锁回收、句段惰性补齐和可诊断安全降级 | DONE |
| P0 | Revision authority | 生成前 flush 到队列引用与签名稳定，`/cuts`、`/compose` 用 `cutDraftRevision` 读取权威草稿，生成阶段零次重对齐 | DONE |
| P0 | Test coverage | Adapter、resolver、API、Node、Chromium、真实产品链 FFmpeg/AAC、二次 ASR 和保留字 PCM 同时作为回归门槛 | DONE |
| P1 | Release gate | Windows 真实素材已验证；Mac Intel/Apple Silicon 真实安装与推理、人耳盲听在发布前执行 | TODO |

## 4. Systematic Expansion

- **Similar Issues**：任何同时拥有源时间/剪后时间、用户语义/渲染物理状态的功能，例如全文艺术字 source anchors、画中画定位和公共时间轴，都应检查双范围消费者和 revision 权威性。
- **Design Improvement**：边界诊断随草稿持久化，模型不可用、文本错配、结构无效和安全降级必须可区分；不能让功能表面启用但长期静默运行旧算法。
- **Process Improvement**：音视频边界缺陷必须从产品入口走到最终编码输出验证，至少同时寻找“被删内容不存在”和“下一保留内容未退化”两类证据。
- **Knowledge Gap**：ASR token 时间是识别模型的粗语义包络，不等于逐字符声学边界；连续协同发音不能靠静音/RMS 单独解决。

## 5. Knowledge Capture

- [x] 更新 backend media/timeline 的完整句段对齐、双范围、revision、验证矩阵和测试门槛。
- [x] 更新 persistence 的 sidecar 原子锁、读取复验和懒加载契约。
- [x] 更新 frontend 的原子回写、键盘 `original*` 和生成保存队列契约。
- [x] 更新 operations/testing 的模型缓存、Mac 发布和真实模型隔离规则。
- [x] 更新 cross-layer guide，要求显式审计语义/物理消费者与异步保存 revision。
- [ ] 在 Mac Intel/Apple Silicon 实机完成依赖安装、模型下载和真实推理。
- [ ] 对产品重生成样片完成人耳盲听。
