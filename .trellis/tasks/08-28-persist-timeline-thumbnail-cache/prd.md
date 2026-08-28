# 持久化时间轴预览帧缓存

## Goal

同一任务和同一源视频刷新后直接复用已经生成的时间轴预览帧，消除重复逐帧 seek/Canvas JPEG 编码和“正在生成帧预览”等待，同时保持首次生成、删除映射、播放和失败降级稳定。

## Background

- 当前 `cutTimelineThumbnailCache` 只存在于 `app.js` 页面内存，刷新会清空并重新创建隐藏 video extractor。
- 同一页面内的删除、恢复和拆分已经只重映射 source-time frames，不会重抽帧。
- 当前每次按时间轴宽度采样 `8..180` 张 `116px` JPEG；刷新重复生成没有产品必要。
- 浏览器中尚无 IndexedDB 持久缓存所有者，不能使用同步 `localStorage` 存放大体积 Base64 JSON。

## Requirements

- R1：使用异步 IndexedDB 按稳定 cache signature 持久化时间轴 JPEG Blob；signature 继续覆盖缓存版本、job、source、源时长和采样数量。
- R2：同一浏览器 context 刷新同一任务后，先读取持久缓存；有效命中时直接渲染，不创建隐藏 extractor、不逐帧 seek、不显示“正在生成帧预览”。
- R3：首次或缓存未命中时沿用现有抽帧质量和 source-time 采样；帧完成后立即渲染，缓存写入和清理在后台异步进行，不延迟可见结果。
- R4：删除、恢复、拆分和剪辑边界变化只使用已有 source-time frames 重新投影，禁止把 cut revision 或删除范围加入 cache key。
- R5：缓存损坏、Blob/shape 不合法、IndexedDB 不可用、open/transaction 失败或版本不匹配时静默回退到现有内存抽帧流程；时间轴、播放和编辑必须继续可用。
- R6：缓存最多保留 24 条、总计约 64 MiB，且清理超过 30 天未访问的记录；按最近访问时间删除最旧记录，不提供新的用户设置。
- R7：Object URL 在内存缓存替换、任务重置和页面销毁时释放；持久 Blob 不因普通页面刷新或切换任务立即删除。
- R8：只持久化时间轴预览帧，不持久化视频、转写文本、剪辑状态或预览合成结果；不改变服务端 schema/API。
- R9：同步提升新缓存脚本和 `app.js` 的静态资源版本，刷新必须加载新逻辑。

## Acceptance Criteria

- [x] AC1：首次打开可正常生成并显示非 loading 的预览帧，IndexedDB 中保存 Blob 记录；帧可见后才允许后台缓存维护继续运行。
- [x] AC2：同一页面刷新后预览帧恢复，extractor 创建数和逐帧 seek 数均为 0，状态栏不出现“正在生成帧预览”。
- [x] AC3：cache signature 的 job/source/duration/count/version 任一变化时不复用旧帧并正常重新生成。
- [x] AC4：删除、恢复和拆分后 extractor 创建数不增加，缩略帧仍按剪后时间轴从 0% 到 100% 连续覆盖。
- [x] AC5：损坏记录和 IndexedDB 失败都能回退并生成帧，不产生未处理 Promise、pageerror 或阻断播放/剪辑。
- [x] AC6：超过年龄、条数或字节上限的旧记录按 LRU 清理，当前命中/新写入记录保留。
- [x] AC7：刷新复用、首次生成、桌面/375px、完整浏览器工作流、前端契约、JS 语法和 `git diff --check` 通过。

## Out Of Scope

- 跨浏览器、跨设备或云端同步预览帧。
- 服务端生成雪碧图、修改视频源或提高缩略帧分辨率/数量。
- 缓存艺术字、画中画、最终预览或历史成片封面。
- 改变时间轴缩略帧的 source/edited 时间投影和连续覆盖算法。

## Key Decisions

- 使用 IndexedDB Blob，而不是 `localStorage` Base64，避免同步序列化阻塞和体积膨胀。
- 缓存是性能优化而不是权威状态；任何读取或写入失败都必须无感降级。
- 首次生成的 UI 完成条件不等待持久写入或 LRU 清理。

## Risks And Deferred Items

- 浏览器隐私模式或配额策略可能拒绝 IndexedDB；由 R5 的内存回退覆盖。
- 不承诺关闭浏览器后永久保留，浏览器仍可按自身存储策略回收站点数据。
