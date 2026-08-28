# 修复跨源句合并后文字重复

## Goal

修复两个不同 ASR 源句的相邻文案段合并后再次编辑时，后一源句文字被重复保留的问题。

## Requirements

- 跨源合并必须保留每个 token 的真实 `sourceSegmentIndex` 归属，不能让整个合并段只继承第一源句。
- 后续文字编辑回写源句时，源句拼接结果必须与当前 editable 文案一致，不重复、不丢字。
- 合并后的文字仍须保持合法、单调的 token/source 时间映射。
- 后续 `text`、`split`、`delete` 操作必须继续正常。
- 同一源句内部的拆分与合并行为保持兼容。
- 不修改物理声学边界、retained transcript 或艺术字协议，只修复源句同步的数据一致性。

## Acceptance Criteria

- [x] 两个不同 `sourceSegmentIndex` 的相邻段执行 merge 后再执行 text 修改，源句拼接字符等于编辑结果且后一源句不重复。
- [x] 跨源合并后没有字符丢失，token/source 时间保持有限、单调并落在合法包络内。
- [x] 真实 `PUT /editable-segments` API 路径覆盖 merge 后 text 保存及持久化结果。
- [x] 既有同源 split/merge 回归继续通过。
- [x] 定向测试和完整 pytest 全部通过，`git diff --check` 通过。

## Notes

- 这是独立于只读交互审计任务的单一 P1 修复。
- 字符语义权威来自当前 editable 文案；source timing 只用于映射，不能决定字符是否存在。
