# 实施计划

## Phase 1: Regression First

- [x] 在 `tests/app/test_cut_acoustic_boundaries.py` 增加“所以说啊 / 所以说啊”相邻重复 fixture：forced timing 字符数量、顺序和单调结构合法，但候选越过真实保留起音；先锁定当前错误结果。
- [x] 增加持续谷底、单点尖谷、单调斜坡、均匀低能和整体增益性质测试，明确歧义转场的佐证资格。
- [x] 保留并显式断言完整重复上下文中的“得/你”大偏差用例走 `forced_pcm_gap`，防止全局 coarse-deviation threshold 或统一重复回退。
- [x] 增加完整 segment 删除的跨段 forced、跨段持续谷底、无谷底、forced overlap/立即起音和 delete-start 对称回归。

## Phase 2: Transition Trust Model

- [x] 在共享字符边界层构造删除/保留 transition context，分离 `structureValid` 与 `boundaryTrustworthy`。
- [x] 实现同 segment 删除 run/保留 run 的重复或重叠字符检测，覆盖完整短语、局部后缀/前缀和连续相同字符。
- [x] 将 alignment record 的局部验证/粗时间诊断按只读元数据带入 character units；不修改原始 transcript，不把动态 trust 写回 sidecar。
- [x] 扩展 boundary diagnostics，并使缺失新字段的旧缓存/草稿继续兼容。

## Phase 3: PCM Corroboration

- [x] 实现语义 fallback 与 forced candidate 之间的有界、方向性持续谷底搜索，复用现有 `5ms` 步长和多尺度 RMS。
- [x] 用相对能量和持续采样资格保持增益无关；拒绝单点尖谷、斜坡和均匀低能。
- [x] 从合格谷底确定低振幅切点及谷底后的保留起音硬限；删除终点只后移、删除起点只前移。
- [x] 歧义转场无内部谷底时，再用 candidate 后独立 quiet gap 的两侧语音证据授权 candidate；无任一证据时安全降级，非歧义转场保持 forced 主路径。
- [x] 更新 forced boundary cache key，使不同重复/删除状态不会错误复用同一可信度结果。

## Phase 4: Shared Entry Integration

- [x] 让文案删除和 `align_manual_timeline_ranges_to_audio()` 通过同一个 cached transition resolver，禁止复制算法。
- [x] 验证 `resolve_cut_draft_acoustic_boundaries()` 仍只解码一次 PCM、只读取/补齐一次 alignment cache，并同时返回 text/timeline 权威物理范围。
- [x] 验证 `original*` 语义不变，草稿 PUT、撤销/重做、预览、`/cuts`、`/compose` 和 FFmpeg 只消费持久化 `start/end`，生成阶段不二次解析。
- [x] 让相邻 segment 的 last/first unit 进入同一个 cached transition resolver；forced 缺失或 overlap 时复用 Phase 3 sustained-valley helper，禁止 `sharedEnd` 把跨段边界静默冻结到 semantic fallback。
- [x] timeline 在 forced 缺失时不得于 resolver 前短路；`0.20s` 只判断用户端点是否靠近 semantic transition，可信 final 可以更远，quiet-gap 范围仍保持精确。

## Phase 5: Frontend Display Projection

- [x] 在 `tests/app/test_frontend_contracts.py` 增加两组真实数值回归：物理起点提前到未删“人”的中点、物理终点延后覆盖未删“你身”的中点；先锁定当前孤立行。
- [x] 修改 suggestion presentation 投影：优先使用 `originalStart/originalEnd`，字段缺失时兼容回退 `start/end`；不修改 `selectedRanges` 或媒体范围。
- [x] 断言连续 retained run 重新合并为完整行，restore run 仍按语义范围聚合，timeline 删除和旧 suggestion 行为保持兼容。
- [x] 用浏览器打开真实 job，确认列表不再单独显示“人”“你身”，恢复按钮、播放、撤销/重做和立即生成仍正常。

## Phase 6: Product And Regression Gate

- [x] 定向运行：`.venv\Scripts\python.exe -m pytest -q tests/app/test_acoustic_alignment.py tests/app/test_cut_acoustic_boundaries.py tests/app/test_cut_draft.py tests/app/test_cut_rendering.py tests/app/test_composition.py tests/app/test_frontend_contracts.py tests/app/browser/test_editor_workflows.py`。
- [x] 用任务 `d87e13fe-8f83-4712-97fc-a9b6eb4f717f` 的只读源媒体和同一草稿走产品 resolver，确认重复边界从歧义 `142.030s` 调整到 `141.814s` 的持续谷底。
- [x] 生成完整 FFmpeg/H.264/AAC 临时成片；运行被删尾音能量、保留“得/你”和“所以说啊”起音 PCM 相关/lag/RMS 对比。
- [ ] 对临时成片人工试听：听不到前一次被删残音，后一次“所以说啊”从首音开始完整保留。
- [x] 回归上一轮“得/你”真实产品 gate，确认终点 `37.790s`、删除后静音能量仅为被删尾音约 `1.4%`、下一“你”相关性 `0.9977`。
- [x] 运行全量测试（排除两个已知 TestClient 生命周期挂起用例）、`.venv\Scripts\python.exe -m compileall -q server` 和 `git diff --check`。
- [x] 定向覆盖整段文字删除与手动时间轴删除：跨段 forced、无 forced PCM、无谷底、立即保留起音、delete-start 对称和远离 transition 的时间轴端点。

## Phase 7: Knowledge And Delivery

- [x] 使用 `trellis-check` 检查 spec、跨层数据流、定向/全量测试和真实媒体双向证据。
- [x] 使用 `trellis-break-loop` 记录“结构合法不等于重复实例语义正确”，以及内部谷底与 candidate 后独立 quiet gap 必须分型的新根因。
- [x] 使用 `trellis-update-spec` 更新 backend media/timeline 与 testing 契约，固化 transition-level trust、两类重复歧义 PCM 佐证和完整上下文保护。
- [ ] 提交产品代码、测试、spec、任务证据和 journal；不提交用户媒体、模型缓存或临时音频。

## Risky Files And Rollback Points

- `server/app.py`：共享 boundary resolver 同时服务文案和 timeline。每完成一个 phase 先跑声学定向测试，避免两入口行为漂移。
- `server/acoustic_alignment.py`：只允许补充可复验的静态诊断，不把动态删除状态写入 sidecar，也不破坏旧 cache key。
- `tests/app/test_cut_acoustic_boundaries.py`：合成 PCM 必须同时构造错误 forced candidate 和真实保留起音，不能只断言某个硬编码秒数。
- `web/app.js`：只修改 suggestion 展示投影，不能把物理边界从保存/生成链移除；前端静态资源版本和 Node/浏览器契约必须同步验证。
- 真实 `data/jobs`、`data/history` 和用户视频只读；所有重新生成输出写临时目录。真实媒体 gate 失败时回到 transition trust 设计，不用调大固定扩张补丁通过。
