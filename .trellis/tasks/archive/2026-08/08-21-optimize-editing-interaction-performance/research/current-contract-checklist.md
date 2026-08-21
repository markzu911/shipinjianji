# 当前契约检查清单

本清单解决完整规格超过 Trellis 单文件上下文注入上限的问题。实现和检查仍以源码及下列完整规格为权威；子代理必须按规格索引在工作区读取相关章节，不能把本清单当成替代规范。

## 权威规格

- `.trellis/spec/frontend/architecture-and-state.md`：状态所有权、剪辑草稿、双层时间、原子 editor frame 与单页工具运行时。
- `.trellis/spec/frontend/ui-and-interactions.md`：剪辑命令历史、ArtTool 三页签、模板 listbox 和交互可见性。
- `.trellis/spec/frontend/api-and-media.md`：媒体 source key、`src/load()`、请求错误与 source/edited 时间。
- `.trellis/spec/backend/media-and-timeline.md`：文字语义/物理双范围、重复转场、PCM 佐证和 retained-side hard limit。
- `.trellis/spec/backend/persistence-and-jobs.md`：cut-draft revision、锁、原子写入和缓存生命周期。
- `.trellis/spec/testing/index.md` 与 `.trellis/spec/testing/browser-workflows.md`：声学 fixture、浏览器隔离、三工具和 ArtTool 回归。

## 本任务不可破坏的不变量

1. `selectedRanges`、`selectedNoSpeechRanges` 和已提交 timeline ranges 仍是唯一剪辑选择 owner；`EditorProjectStore` 仍是公共 frame 的唯一 owner。
2. 每个独立命令同步捕获 before/after/history meta。rAF 只合并可见渲染和副作用，不能丢失两个同帧命令的撤销边界。
3. 草稿语义签名排除服务端派生的 text/timeline 物理 `start/end`、revision、diagnostics 和时间戳。请求 envelope 在发送时使用最近 acknowledged revision 重建。
4. 旧响应可以推进服务端 revision，但只有 in-flight 语义签名仍等于 current desired 时才可应用规范化物理范围。生成等待 pending commit、timer、in-flight、语义签名和 revision 全部稳定。
5. PCM cache 只缓存媒体解码结果，不缓存 range alignment、forced boundary 或动态 transition trust。缓存开关、并发命中、miss、淘汰和失败路径必须返回完全一致的范围、diagnostics 和 revision。
6. 声学回归固定覆盖完整段落跨段转场、“得/你”、“一起给”、delete-start/delete-end、下一段立即起音、短保留字符和 retained-side hard limit；同时证明尾音消失且下一段起音不受损。
7. cut frame 重绘不得改变 ArtTool 的三页签状态、selection 从有变无的返回规则、模板 listbox 焦点/关闭语义、manual/transcript 轨道或 document/video identity。
8. 性能终点在 commit 后第二个 rAF 中读取已更新 DOM；第一个 rAF 回调入口不能作为可见完成时间。

## 最小验证集合

- 确定性计数：extractor、基础 video `src/load()`、Store action、history serialization、PUT 数和最大并发。
- 保存队列：300ms burst、在途编辑、revision rebase、规范化物理边界、失败、刷新和生成前 flush。
- 浏览器：600 字/30 区间性能 fixture、同帧两命令两次撤销、cut/art/pip identity、ArtTool 三页签/listbox。
- 后端：连续/并发 PCM 命中、指纹失效、按字节 LRU、失败不缓存，以及上述完整声学 fixture 的缓存等价性。
