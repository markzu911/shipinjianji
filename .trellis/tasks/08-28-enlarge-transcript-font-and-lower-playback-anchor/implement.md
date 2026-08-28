# 实施计划

- [x] 调整文案列表五个文字层级为精确 `1.2×` 字号，不改变控件尺寸。
- [x] 在跟随 metrics 中增加三行动态偏移和面板底部 clamp，复用现有动画数据流。
- [x] 提升 `styles.css` 与 `transcript-follow-scroll.js` 资源版本及静态契约。
- [x] 更新 Node 跟随测试的锚点、scrollTop、FLIP/尾部断言，并增加动态行高与底部 clamp 覆盖。
- [x] 更新 Chromium 字号/布局测试，覆盖桌面、`375px`、活动行停靠和无溢出。
- [x] 运行前端契约、相关浏览器工作流、全部 JS 语法检查和 `git diff --check`。

## Verification Evidence

- `tests/app/test_frontend_contracts.py`: `35 passed`。
- Chromium 目标工作流连续稳定验证：`5/5 passed`；覆盖精确字号、动态三行锚点、reduced-motion 底部 clamp、唯一真实行/按钮及桌面/375px 无溢出。
- 完整 Chromium 浏览器回归：`49 passed`。
- 全部 `web/*.js` 通过 `node --check`；`git diff --check` 通过。
- Python `compileall` 通过；项目未配置独立 linter 或 Python type checker。
