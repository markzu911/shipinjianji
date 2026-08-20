# 实施计划

1. 在 `tests/app/test_cut_acoustic_boundaries.py` 先增加通用失败性质：同一 PCM 结构在多组不削波增益下应得到稳定边界；当前实现必须能复现低增益提前返回的失败。
2. 增加参数化安全矩阵，覆盖删除起点/终点、同 token/跨 token、低底噪/正常音量、静音/连续语音/单调斜坡、单范围/相邻多范围和短保留字符岛。
3. 增加 AI 建议与草稿 PUT 的同源一致性测试，并断言所有结果满足方向、走廊、单调和保留字符核心不变量。
4. 在 `server/app.py` 收敛统一的相对改善判定；修正 `refine_shared_character_boundary` 的绝对安静提前返回，并在最终返回前统一执行安全约束。
5. 运行定向声学边界测试，再运行 `test_cut_draft.py` 与 `test_cut_rendering.py`，确认草稿和生成契约不回归。
6. 用现有源视频和历史原始转写做只读边界计算，验证“自己选出来的”终点进入 `6.250–6.332s` 且不超过下一字符声学中心；同时复核原任务的其他真实边界不发生反向或越界变化，不改写真实草稿。
7. 运行完整测试、Python 编译检查和 `git diff --check`。
8. 按重复缺陷复盘结果更新媒体时间轴规范，记录增益稳定、相对证据、共享所有者和安全回退规则。

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_cut_acoustic_boundaries.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_cut_draft.py tests/app/test_cut_rendering.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m py_compile server/app.py
git diff --check
```

## Risk And Rollback Points

- `refine_shared_character_boundary` 同时服务删除起点和终点，必须保留双向现有测试并检查真实边界差异。
- 不加入文本、时间戳或真实草稿专用分支；若现有绝对阈值参与候选资格，必须服从统一相对证据和增益稳定契约。
- 用户已有前端未提交修改与本任务文件不重叠；实现和检查不得覆盖这些修改。
