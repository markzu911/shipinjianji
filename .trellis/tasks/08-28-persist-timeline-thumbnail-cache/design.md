# 设计：时间轴预览帧持久缓存

## Architecture And Ownership

- 新增 `web/timeline-thumbnail-cache.js`，通过 `window.TimelineThumbnailCache` 提供唯一 IndexedDB 访问边界；不拥有时间轴 DOM、媒体 video 或 source/edited 映射。
- `web/app.js` 继续唯一拥有采样数量、cache signature、extractor、Canvas 抽帧、内存 cache 和缩略帧投影。
- `web/index.html` 在 `app.js` 前加载缓存脚本；缓存不可用时 `app.js` 使用 no-op/null store 继续现有流程。

## Persistent Record

```javascript
{
  signature: string,
  cacheVersion: number,
  jobId: string,
  sourceDuration: number,
  count: number,
  frames: Array<{ sourceTime: number, blob: Blob }>,
  byteSize: number,
  createdAt: number,
  lastAccessedAt: number,
}
```

数据库使用独立名称和单一 `timeline-thumbnails` object store，`signature` 为 keyPath。清理读取有限记录后按 `lastAccessedAt` 排序，同时应用 30 天、24 条和 64 MiB 三个上限。

## Cache API

```javascript
TimelineThumbnailCache.createStore(options?) -> {
  load(signature) -> Promise<record | null>,
  save(record) -> Promise<void>,
  prune({ preserveSignature? }?) -> Promise<void>,
  close() -> void,
}
```

- API 永远异步；调用者捕获失败并降级。
- `load()` 校验 record 和每个 Blob，命中时更新 `lastAccessedAt`。
- `save()` 原子写入单条完整记录；随后后台 prune，不能让维护延迟可见帧。
- `versionchange` 关闭连接，`blocked/error` 使本次操作失败但不影响编辑器。

## Build Data Flow

```text
buildCutTimelineThumbnails()
  -> memory signature hit: render existing frames
  -> reserve one generation owner before async work
  -> IndexedDB load
      -> valid hit: Blob -> Object URL -> memory cache -> render
      -> miss/error: existing hidden video seek loop
          -> canvas.toBlob(image/jpeg, 0.72)
          -> Object URL -> memory cache -> render immediately
          -> background save + prune
```

所有 await 后检查 build id、AbortSignal 和 owner identity。相同 signature 的并发调用复用当前 owner；source/signature 切换 abort 旧 generation。IndexedDB transaction 本身不强制取消，但迟到结果不得写内存或 DOM。

## Object URL Lifecycle

- 内存 frame 同时持有 `blob` 和仅用于当前 document 的 `url`。
- 替换或清空内存 cache 前统一 `URL.revokeObjectURL(frame.url)`。
- 持久记录只保存 Blob 和 sourceTime，不保存跨 document 无效的 Object URL。
- 普通 source-time 重映射复用同一组 URL，不重复创建。

## Validation And Fallback Matrix

| Condition | Behavior |
| --- | --- |
| 内存 signature 命中 | 直接重映射，无 IDB/extractor |
| IDB 有效命中 | 创建本 document Object URL 并渲染，无 extractor |
| IDB miss/不可用/损坏 | 进入现有 extractor 流程 |
| 生成中切换 signature | abort video owner；迟到 IDB/Blob 回调 no-op |
| cache save/prune 失败 | 已显示帧保持；不显示产品错误 |
| 删除范围变化 | 只调用投影，不修改/重写 Blob record |
| 采样 count 或源时长变化 | 新 signature，重新生成并写新记录 |
| 页面卸载 | abort extractor、释放 Object URL、关闭 DB；保留 Blob record |

## Compatibility And Rollback

- 不修改后端、草稿或项目 schema；删除新脚本引用和持久 load/save 路径即可回到现有内存行为。
- 静态资源升级确保刷新不混用旧 `app.js` 和新缓存 API。
- 旧浏览器或禁用 IndexedDB 的环境继续生成帧，只失去刷新复用优化。

## Test Strategy

- Node/static：缓存脚本资源顺序、API surface、Blob/URL 清理和 `app.js` 版本契约。
- Chromium：首次生成后检查 IDB Blob；reload 后 extractor/seek 为 0、帧可见且状态不显示生成；损坏记录回退；真实 IDB prune 上限。
- 现有性能/时间轴回归：删除、恢复、拆分仍为零次新增 extractor，帧连续覆盖和高度不变。
