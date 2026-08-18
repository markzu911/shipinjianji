# 测试边界拆分实施计划

1. 保存当前 164 个原测试函数名、两个参数化装饰器和 `168 passed` 基线；以研究迁移矩阵作为唯一分配清单。
2. 创建 `tests/app/conftest.py`，原样移动 `isolated_jobs`、`sample_video` 及其最小 imports；先用一个目标模块和 Mac 测试验证 fixture 作用域。
3. 按连续区域迁移 settings、maintenance/history、asset libraries、transcription/suggestions 和 cut draft 测试；每个模块只保留研究清单所需 imports，并单独运行。
4. 迁移 acoustic boundaries、cut rendering、art text API、composition、picture-in-picture、art track 和 art rendering；把非连续的尾部测试移动到实际功能所有者，把 `_build_track_words` 放入 art track 模块。
5. 将前端 1,037 行综合契约拆为 9 个函数，使用函数级资源请求 helper，按 830 条断言矩阵逐块迁移并核对总数；现有 6 个 Node/前端行为测试原样迁移。
6. 删除 `tests/test_app.py`，运行 AST 完整性检查，确认 163 个不变测试名、9 个替代名、两个参数化装饰器和 176 个收集节点。
7. 逐个运行 13 个 `tests/app/test_*.py`；单独运行 Mac 打包测试并确认 `--setup-show` 不包含 `isolated_jobs`。
8. 运行完整测试、函数行数上限和 diff 门禁；确认没有 `server/`、`web/`、用户数据或临时媒体变更。
9. 更新 `.trellis/spec/testing/index.md` 的测试目录导航与 fixture 作用域约定，派发 `trellis-check` 做最终独立检查。

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q
Get-ChildItem tests/app/test_*.py | ForEach-Object {
  .\.venv\Scripts\python.exe -m pytest -q $_.FullName
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
.\.venv\Scripts\python.exe -m pytest -q tests/test_build_mac_package.py --setup-show
.\.venv\Scripts\python.exe -m pytest -q
git diff --exit-code -- server web
git diff --check
```

使用 `research/test-module-migration.md` 中的 AST 命令检查测试函数不超过 300 行，并将 `--setup-show` 输出中的 `isolated_jobs` 视为 Mac fixture 隔离失败。

## Risk And Rollback Points

- 前端综合测试包含跨页面临时切片变量；必须按研究给出的断言区块连同局部变量迁移，不能只复制 `assert` 行。
- 两个参数化测试若遗漏 decorator，pytest 仍可能全绿但少收集 3 个节点，因此收集数 176 是硬门禁。
- `isolated_jobs` 不得简化为只清理 `JOBS`；模型设置和 DashScope URL 恢复是顺序独立的必要条件。
- 拆分期间不要同时修改产品代码或清理既有测试逻辑；若一个目标模块不能独立通过，先修复其 imports/fixture 所有权再继续。
