# 跨层变更检查指南

## 系统数据流

```text
浏览器上传
  -> FastAPI 校验并写 data/jobs/<job_id>
  -> 后台线程提取音频/调用 ASR
  -> JOBS 中的 transcript + word timestamps
  -> app.js 文字编辑和删除草稿
  -> editor-suite.js 协调顶层 ArtTool/PipTool、统一预览与时间线
  -> FastAPI 归一化 overlay 和 source anchor
  -> FFmpeg 预览/最终合成
  -> data/history 持久成片
```

## 每次跨层修改必须回答

1. 权威状态在哪里：内存 job、cut draft、顶层 `EditorProjectStore`、sessionStorage 草稿还是 history manifest？
2. 时间字段属于源视频还是剪后视频？转换在哪一层发生？
3. 浏览器发送的字段由哪个 Pydantic 模型和哪个 normalize 函数校验？
4. 刷新、服务重启、取消、失败后还剩什么状态？
5. 预览和导出是否消费同一份归一化数据？
6. 同一领域对象是否同时存在“展示/语义层”和“模型/存储权威层”？如果存在，字段名、最小操作单元和旧数据回退是否逐记录定义，而不是用全局字段存在性推断？
7. 删除旧页面、iframe 或运行时前，是否用 `git show`/`rg` 列出了它在每个输入事件上的业务副作用，并为每个副作用找到新 owner 和集成测试？只验证新组件能渲染、保存或切换，不足以证明行为迁移完成。
8. 预览与导出是否先在同一个内容画布坐标中计算，再只做一次 contain/cover 显示变换？外层舞台、黑边和设备 UI 不能成为第二套字号、位置或指针坐标权威。
9. 初次 normalize 之后是否还有逐字时间、源锚点或其他派生字段回写边界？只要后续步骤可能改变不变量，就必须在最终返回/API/compose 前复用同一规范化入口，并用严格边界测试证明下一对象没有被移动或吞并。
10. 同一次编辑是否同时存在用户语义范围和媒体物理范围？若存在，必须明确 `original*`、物理 `start/end`、retained transcript、预览和 FFmpeg 各自消费哪一层，禁止用物理吸附结果反写用户意图。
11. 生成动作前是否存在异步草稿保存？不能只等待一次旧 Promise；必须等到保存队列引用稳定且当前签名已被服务端确认，再携带权威 revision 生成，避免保存期间的新编辑被遗漏。
12. 模型或缓存记录的“结构有效”是否被误当成当前业务转场可信？当相同文本可能映射到多个实例时，动态 trust 必须结合当前删除状态和局部媒体证据派生，不能写回静态 sidecar，也不能用全局偏差阈值替代；完整上下文还要区分“候选前的内部谷底”和“候选后的独立 quiet gap”，不能把所有重复转场统一退回 semantic fallback。

## 浏览器边界

- 主编辑器只有一个 document、基础 video、Store、公共预览和公共时间线；ArtTool/PipTool 通过注入的 services/commands 工作，不建立跨页消息协议。
- `editor-suite:refresh`、`editor-suite:transcript-updated`、`editor-suite:job-state` 是保留的同文档事件；不要因为旧 bridge 使用相同前缀而批量删除。
- 删除或重命名 DOM 节点前，用 `rg` 检查所有页面脚本、共享协调器和静态契约中的 selector 依赖；能力检测只能依赖完成该能力所需的稳定容器，不能依赖可选页签或状态面板。
- 修改工具布局后，真实浏览器必须从文字剪辑依次切换艺术字、画中画并返回，确认 document/video identity、公共预览、URL 参数、激活/隐藏 panel 的 inert 状态一致且 iframe 数量为 0。
- 移除旧工具运行时前，先按事件入口建立“旧事件 -> 状态副作用 -> 新 owner -> 回归测试”清单。涉及 cut/transcript 的下游效果至少验证：先创建效果，再删除文字，再撤销；同时断言 Store、预览、时间轴、草稿恢复和 compose，而不是只断言工具面板自身。

## API 边界

- 浏览器输入不可信。后端重复执行数值、枚举、路径和资源归属校验。
- 浏览器即使已经把选择规范到字符边界，后端也必须在持久化和生成入口重复规范；文字时序兼容应按段执行 `words -> asrWords -> segment` 回退，避免模型 token 跨自然词边界或混合新旧数据时部分对象失去校验或保护。
- API 错误用非 2xx + `detail`；前端解析失败时提供稳定的兜底文案。
- 轮询只在 queued/processing 等非终态继续，离开页面或取消后要停止旧轮询。

## 当前已知风险

- `JOBS` 在重启后消失，但 cut draft/history 部分持久化。
- 时间映射逻辑分布在 Python、`app.js`、`editor-suite.js` 和子工具页面。
- 服务端 job、顶层 Store 与可恢复草稿仍需严格区分权威层和持久化层。

这些风险属于后续优化目标。新改动应减少状态副本，不应增加新的私有 payload 或 HTML 快照协议。

## 验证

跨层功能至少覆盖：正常往返、空/非法字段、刷新恢复、服务重启语义、失败清理、预览与导出一致性。核心工作流再用真实浏览器验证桌面和 375px 窄屏。
