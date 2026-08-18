# 实施计划

1. 在 `server/app.py` 增加按段建立自然字符到 `asrWords` 的顺序映射与合法性校验，复用现有标点过滤规则，不改变 `transcript_character_units` 的语义输出。
2. 实现受约束的共享声学边界细化：生成局部搜索走廊、计算多尺度短窗能量/相对改善、执行单调与字符核心限制，并缓存同一字符交界的结果。
3. 将 `build_transcript_delete_boundary_limits`、`snap_suggestion_ranges_to_audio` 和 `align_cut_draft_text_ranges_to_audio` 收敛到同一个文字物理边界所有者；前端建议初始化、范围规范化和合并选择保留 `originalStart/originalEnd` 与 `start/end` 双层所有权；保留无音频/无 `asrWords` 的安全回退。
4. 确认前端预览、草稿解析、公共预览、单独剪辑和统一组合不二次吸附或把物理点裁回语义点；retained transcript 仍只消费 `originalStart/originalEnd`。
5. 在 `tests/test_app.py` 增加不等长声学边界、首音残留、尾音残留、无可信低谷、跨 token `给一`/`得你`、多范围复用和回退测试。
6. 增加草稿 PUT、前端 Node 行为与生成一致性回归，验证重复 PUT 幂等、短保留字符不被合并穿越、下一保留字符后的静音不推动删除终点、连续已删 token 跨 `rangeKey` 合并展示且恢复全部聚合 key、现有前置任务测试不回退。
7. 运行定向测试，再运行 `python -m pytest -q`、`python -m py_compile server/app.py`、`node --check web/app.js` 与 `git diff --check`。
8. 在系统临时目录用 `data/jobs/cd541254-a931-4ecc-ba86-f7ff620a56b2/source.mp4` 和现有草稿生成验证成片；对比附件、二次 ASR 和拼接点短音频，确认“所有人一一起给”消失且后一遍“一起给你”完整。
9. 实现和检查过程中只提交本任务相关补丁块；不覆盖 `server/app.py`、`tests/test_app.py` 中其他未提交任务的修改，不改真实用户数据。

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_app.py -k "acoustic or boundary or suggestion_snapping or cut_draft_alignment"
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

## Risk And Rollback Points

- `server/app.py` 与 `tests/test_app.py` 同时包含前置任务未提交改动，实施前后必须按函数/测试块审查 diff，不能整文件还原。
- 若声学候选在合成样本通过但真实媒体仍残留，先记录候选评分和走廊证据再调参；禁止通过固定扩张或恢复整 token 删除让测试表面通过。
- 若真实媒体必须依赖专用 forced alignment 才能同时满足两个边界目标，本任务停在安全回退并另建模型能力任务，不把大型运行依赖混入当前修复。
