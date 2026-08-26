# 技术设计

## Architecture

```text
source transcript + semantic delete ranges
                    |
                    v
        semantic retained characters
                    |
      validated forced timing (preferred)
      coarse timing (fallback only)
                    |
                    v
         physical delete time warp
                    |
                    v
      retained transcript projection
       |             |              |
 cut-draft GET/PUT  /cuts,/compose  browser frame/timeline
```

持久化权威仍是 source transcript 与 cut-draft ranges/revision。retained transcript 是可重建的派生值，不写入 CutDraftRequest 或 `cut-draft.json`。

## Backend Projection

1. 复用 `transcript_acoustic_character_units()` 构建按原 transcript 排序的自然字符单元。
2. 仅用单元的语义 `start/end` 与 semantic delete ranges 判断是否保留。`_forced*` 和 `_acoustic*` 不参与字符身份判定。
3. alignment record 结构有效且文字顺序一致时，使用 `_forcedStart/_forcedEnd` 作为保留字符的 source timing；否则使用粗语义时间。
4. timing 经 `timeline_after_deletions()` 映射到 edited timeline。因物理 cut 而坍缩的连续保留字符与同 run 最近正时长区间组合/单调分配，不得 `continue` 删字。
5. 字符投影是真值；主 `words` 按 natural word 连续 run 聚合，`asrWords` 按原 ASR item 聚合。输出增加可选 source anchors 与 `sourceSegmentIndex`，旧消费者可忽略。
6. `build_retained_transcript()` 增加可选 `alignment_cache`，缺省保持调用兼容。

## Cut Draft Response

- 新增纯派生 helper，从 normalized draft 计算 semantic ranges、physical ranges、output duration 与 retained transcript。
- cut-draft GET/PUT 返回 `{cutDraft, retainedTranscript}`，两者基于同一 revision 快照。
- helper 只读已有 acoustic sidecar，不触发 FunASR 新推理。旧草稿在 GET 时重建派生值，不迁移文件。

## Frontend Projection

浏览器保存一份受守卫的服务端投影：

```javascript
{ jobId, signature, revision, transcript }
```

- 本地选区、撤销/重做、草稿恢复或 job 切换先失效旧投影。
- `applyPersistedCutDraftAlignment()` 仅在现有 signature/revision guard 通过后安装服务端 transcript。
- 抽取 `getCurrentRetainedProjection()`，供 `buildLiveCutDraftState()`、时间轴文案/宽度/播放命中和 EditorSuite/Store 共同消费。
- `getRetainedSegmentParts()` 保留为响应前/旧服务降级，但改为先语义选字、后物理映射。坍缩 token 只降级时间精度，不降级文字内容。

## Generation And Recovery

- `/cuts`、`/compose` 和 project-state/edit 恢复调用同一 retained projection helper，并读取已有 alignment sidecar。
- FFmpeg 仍只消费已持久化物理 ranges，生成阶段不重新解析声学边界。
- history 保存最终 edit transcript，无新必填 schema 字段。

## Compatibility And Failure Matrix

| 条件 | 处理 |
| --- | --- |
| sidecar 有效 | forced timing -> physical warp |
| sidecar 缺失/文字不匹配 | 粗时间不丢字降级 |
| cut-draft 响应过期 | 忽略 ranges 和 retained transcript |
| 旧服务不返回 transcript | 前端本地降级继续可用 |
| 旧草稿无派生值 | GET 时重建，不迁移文件 |

回滚点只在 retained projection 和 cut-draft 派生响应；boundary resolver、ranges/revision 和 FFmpeg 路径不在修改范围。

## Test Strategy

- 后端纯函数：forced 可用、粗时间完全在 cut 内、无 alignment、整 item 坍缩、标点、`asrWords`、跨 segment、单调/正时长。
- API：cut-draft GET/PUT revision 与派生 transcript 同步，请求 schema 不接受派生字段，旧草稿兼容。
- 生成：`/cuts`、`/compose`、project-state/history 恢复文字一致。
- 前端：本地降级不丢“一起”/“你”，server projection 匹配时成为单一消费值，stale 响应被拒绝。
- 浏览器：列表、时间轴、Store frame 和 compose payload 逐字一致，草稿恢复后仍一致。
- 声学：物理边界、首字残音、“得/你”和相邻重复起音保护不变。
