# 文案展示片段与编辑弹窗一致性设计

## 1. Design Goal

让文案列表中的每个可编辑展示片段成为弹窗、文字保存、拆分和可执行方向合并的同一操作目标，同时保留 `currentEditableSegments`、删除范围、声学物理边界和现有 Store/草稿同步链路。

## 2. Root Cause And Ownership

- `buildSegmentTextRuns()` 会把一个权威 editable segment 按 `restore/deleted/edit` 状态拆成多个展示行。
- 展示行当前只把父 `segmentIndex` 传给 `openSegmentEditDialog()`；弹窗再读取整个 `currentEditableSegments[segmentIndex]`，因此展示粒度和命令粒度分叉。
- `web/app.js` 负责从权威段派生展示片段 identity 和弹窗 active target。
- `server/app.py::apply_transcript_segment_operation()` 继续负责字符范围校验、文字重分词、拆分/合并和 source ownership 守恒；浏览器不自行持久化重组后的权威段。

## 3. Display Fragment Contract

`buildSegmentTextRuns()` 为每个 run 增加父段 Unicode code point 范围：

```javascript
{
  segmentIndex,
  characterStart,
  characterEnd,
  semanticStart,
  semanticEnd,
  start,
  end,
  text,
}
```

偏移通过 token 顺序累计 `Array.from(token.text).length` 得出，禁止用 `indexOf()`，因为同一父段可能包含重复短语。渲染节点写入 character range，reconcile signature 同时包含该范围；复用节点不能保留旧操作目标。

打开弹窗时从点击行创建 active target，验证：

1. 父段和字符范围仍存在；
2. `Array.from(parent.text).slice(start, end).join("") === displayText`；
3. 展示语义/物理范围有限且正向。

验证通过后，textarea 使用 `displayText`，时间使用该行 `displayStart/displayEnd` 的剪后投影。验证失败时拒绝打开并提示刷新，不回退显示整个父段。

## 4. Scoped Commands

### 4.1 Text save

局部 target 发送现有 `action="text"`，附带父段 `selectionStart/selectionEnd` 和 textarea 文字。服务端按字符 token 重建：

```text
new parent text = prefix + replacement + suffix
```

随后复用 `retokenize_editable_segment_text()`、source segment 同步、艺术字文本同步和 Store effect。完整父段不带范围，保持兼容。

### 4.2 Split

textarea 选择仍以局部 code point 计数；请求偏移为 `active.characterStart + localOffset`。服务端继续使用现有 split 分支，不增加协议。

### 4.3 Directional merge

局部 merge 请求附带 active range。服务端在内存快照中原子执行：

- `merge_up`：只接受 `selectionStart === 0`，把 target 后缀隔离，合并外部上一段与 target。
- `merge_down`：只接受 `selectionEnd === parentTokenCount`，把 target 前缀隔离，合并 target 与外部下一段。
- 完整父段沿用原有 merge。
- 中间片段或被删除文字挡在目标方向时前端禁用按钮，服务端仍重复校验并返回 400。

一次请求只安装一次最终 `editableSegments`，不会暴露“已拆分但未合并”的中间 revision。隔离出的删除片段仍由原 selected range 命中，因此继续显示为恢复行。

## 5. State And Compatibility

- `TranscriptSegmentOperation` 已有可选 `selectionStart/selectionEnd`，只扩展 text/merge 对它们的解释，不新增 endpoint 或持久化字段。
- job `updatedAt` 的并发版本检查、editable boundary enrichment、source ownership、art/compose 字符守恒和 cut-draft 保存路径保持现有 owner。
- selected ranges 以源时间为 identity，不依赖 editable segment index；结构调整后仍能命中被删除 token。
- 更新 `app.js` 资源版本，避免旧点击消费者与新数据属性混用。

## 6. Validation And Rollback

- Python 单元覆盖局部文字替换、重复短语第二处、前缀/后缀隔离合并、非法跨删除方向和 source ownership。
- Node/静态契约覆盖 run 字符范围、reconcile identity、局部到父段偏移换算和不使用 `indexOf()`。
- 真实 Chromium 覆盖部分删除后打开、保存、拆分、向下/向上合并、删除片段仍可恢复，以及 cut/art/timeline/preview/compose 文本一致。
- 若 scoped merge 无法证明原子结构安全，可独立回滚 merge 范围扩展，同时保留弹窗、保存和拆分的一致性修复。
