# 实现与验证

## 实现

- editable segment 的逐字符 token 保留 `sourceSegmentIndex`；跨源 merge 同时记录覆盖的源句索引。
- text 编辑复用全文字符差分投影，将新文案单调分配回原 token 的源句归属和时间包络；editable 路径保留内部空白。
- source segment 回写、retained transcript 分组、editable 声学边界和艺术字 cue 更新均消费逐 token 归属。
- 兼容旧版已合并但未记录 token 归属的草稿：按逐字符时间中点推断源句，优先已声明源句包络并保证 owner 单调。
- 某个被合并源句被编辑为空时，源句、retained transcript 和艺术字 cue 一起清空/抑制，不保留旧文案。

## 验证

- `tests/app/test_cut_draft.py`: 54 passed。
- `tests/app/test_cut_acoustic_boundaries.py`: 102 passed。
- `tests/app/test_art_text_api.py tests/app/test_art_text_track.py`: 47 passed。
- 完整 `pytest -q`: 489 passed, 1 warning。
- `python -m compileall -q server`: passed。
- `git diff --check`: passed。
- 项目未安装 Ruff/Mypy，无独立 lint/type-check 命令可执行。

## 覆盖

- 纯函数：跨源 merge -> text -> split，字符守恒、内部空白保留、逐 token 归属、时间有限且落在源句包络；另覆盖旧草稿跨源自然词。
- API/持久化：真实 merge + text PUT 后，内存与 `project-state.json` 中的源句、editable 文案、retained transcript、边界和艺术字文案一致且无重复。
- 既有同源 split/merge、retained transcript 和声学边界回归保持通过。
