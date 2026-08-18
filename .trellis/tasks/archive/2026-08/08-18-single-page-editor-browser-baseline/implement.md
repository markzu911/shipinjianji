# 浏览器行为基线实施计划

## Dependency

- 父任务：`08-13-project-optimization-audit`。
- 本任务是父任务 Phase 0，必须在 B0 单一状态与 revision 契约之前完成。
- 本任务不得实现或提前修改 B0-B4 的产品行为。

## Step 1：工具与运行入口

- [x] 在 Python 依赖中加入有上限的 Playwright 版本，不引入 pytest 插件或 npm。
- [x] 记录 `python -m playwright install chromium` 与聚焦 pytest 命令。
- [x] 增加 browser marker 或目录级选择方式，保证完整 pytest 默认仍运行浏览器基线。

## Step 2：隔离服务与浏览器 fixture

- [x] 在 `tests/app/browser/` 建立 Uvicorn 临时 socket、健康等待和可靠关闭 fixture。
- [x] 建立 Playwright runtime/browser/context/page fixture；每测试隔离存储并拒绝外部网络。
- [x] 集中建立确定性 job/transcript/cut/art/pip fixture，复用真实一秒媒体，不调用外部服务。
- [x] 捕获 page error、严重 console error 和非预期失败请求；诊断产物只写 `tmp_path`。

## Step 3：核心工作流

- [x] 实现文字/删除草稿保存后刷新恢复用例。
- [x] 实现文字、艺术字、画中画切换后状态与播放位置保持用例。
- [x] 实现从 UI 触发 compose 并校验三类状态载荷的用例，不执行最终渲染。
- [x] 实现服务重启继续编辑的目标断言，并以注明 Phase A 的 xfail 标记当前缺口。

## Step 4：验证与文档

- [x] 运行聚焦浏览器测试，确认重复两次不受端口、存储和测试顺序影响。
- [x] 运行全部 `web/*.js` 的 `node --check`。
- [x] 运行完整 `pytest -q`，确认既有测试无回归。
- [x] 运行 `git diff --check`，确认没有浏览器产物、真实数据或秘密进入变更。

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser
Get-ChildItem web -Filter *.js | ForEach-Object { node --check $_.FullName }
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

## Rollback Point

本任务的依赖、浏览器 fixture、浏览器用例和运行说明作为一个独立交付；不包含业务代码。发生环境兼容问题时可整体移除，不影响当前编辑器运行。
