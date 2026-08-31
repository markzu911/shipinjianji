# 文案展示片段与编辑弹窗一致性实施计划

## 1. Frontend Fragment Identity

- [x] 为 `buildSegmentTextRuns()` 增加 Unicode code point 起止偏移，并把偏移纳入展示节点 data 与 reconcile signature。
- [x] 用 active fragment target 替代仅有的 `activeSegmentEditIndex` 操作上下文；打开弹窗前验证父段 slice、展示文字和范围一致。
- [x] 弹窗文字/时间使用展示行数据；映射失效时拒绝操作并给出稳定反馈。

## 2. Scoped Operations

- [x] 局部保存发送父段字符范围，完整段保存保持旧 payload；服务端只替换目标 slice 并复用现有重分词与 source/art 同步。
- [x] 局部拆分把 textarea 偏移平移到父段绝对偏移。
- [x] merge 上/下按钮按 active fragment 是否贴近父段对应边界启用；请求携带 fragment range。
- [x] 后端原子隔离非目标前缀/后缀后执行方向合并，重复验证不能跨被删除文字，保留旧完整段 merge 兼容。

## 3. Regression Coverage

- [x] Python：局部 text、重复短语第二处、prefix/suffix scoped merge、非法方向、字符/source ownership 守恒。
- [x] 前端契约：偏移、identity、payload、按钮状态、失效拒绝和无 `indexOf()` 模糊匹配。
- [x] 浏览器：部分删除后弹窗与行一致；保存、拆分、方向合并后删除行仍可恢复，公共时间轴/Store/art/preview/compose 一致且媒体不重载。

## 4. Quality And Spec Sync

- [x] 更新 frontend architecture、backend media/timeline 和 testing 规范中的展示片段编辑契约。
- [x] 更新静态资源版本，运行修改 JavaScript 的 `node --check`。
- [x] 运行相关 API/前端契约/真实浏览器测试、完整 browser suite 和 `git diff --check`。

## Rollback Points

- scoped merge 可独立回滚为方向禁用，不影响片段弹窗、保存和拆分修复。
- scoped text 若 source ownership 校验失败，保留现有完整段保存并拒绝局部写入，不能降级为前端模糊拼接。
