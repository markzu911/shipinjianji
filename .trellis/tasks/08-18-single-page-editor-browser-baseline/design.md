# 浏览器行为基线技术设计

## 1. 测试边界

使用 Python Playwright 的同步 API 驱动 Chromium，保持仓库现有 Python/pytest 工具链，不引入 npm、bundler 或前端框架。浏览器测试放在 `tests/app/browser/`，从而继承 `tests/app/conftest.py` 的 `isolated_jobs` 与 `sample_video`，但浏览器专用 fixture 不污染其他应用测试和 Mac 打包测试。

## 2. 运行模型

每个测试由同一 pytest 进程完成以下生命周期：

1. `isolated_jobs` 将 `server.app.DATA_DIR` 指向 `tmp_path`，清空 `JOBS`/`JOB_FILES` 并移除外部服务凭证；
2. fixture 在临时目录建立确定性媒体、transcript、cut draft、art 和 pip 状态；
3. Uvicorn 使用预绑定的 `127.0.0.1:0` socket 启动，避免固定端口竞争；
4. Playwright 启动 Chromium，每个测试创建独立 context/page；
5. 页面只访问该临时 base URL，外部网络通过 context routing 拒绝；
6. 测试结束关闭 context/browser，通知 Uvicorn 退出并等待线程结束。

Playwright runtime 可在测试会话内复用，但 browser context 必须逐测试创建，避免 localStorage、sessionStorage、Cache Storage 和 service worker 状态串扰。

## 3. Fixture 与状态建立

测试不得走真实 ASR 或 AI 生成。建立 job 时复用当前服务端公开字段形状，在 `JOBS_LOCK` 下写入最小可编辑 job，并把视频复制到隔离 job 目录。若前端启动还需要 API 派生字段，应通过测试 helper 集中建立，禁止每个用例散写不同 job 形状。

艺术字/画中画素材使用本地确定性 fixture。需要观察 compose 时，通过 Playwright route 捕获浏览器请求并返回最小 202 响应；断言请求 JSON，不启动后台 FFmpeg 合成。任何未明确允许的非本地请求直接失败。

## 4. 行为场景

### 4.1 刷新恢复

从主编辑器加载 seeded job，执行一次可观察的文字/删除操作，等待保存状态完成，刷新页面，再通过 UI 与 cut-draft API 投影核对文案、删除范围和时间映射。

### 4.2 跨工具切换

建立 art/pip 状态后依次切换文字、艺术字、画中画。断言 iframe/面板可见状态、公共预览图层、选中项和基础视频 `currentTime` 保持当前实现承诺。该用例在 B2/B3 后继续复用，但最终断言会从 iframe 切换为同页面板。

### 4.3 统一生成

从浏览器触发统一生成，捕获 `/compose` 请求，校验 cut、art、pip 的规范化载荷来自当前 UI 状态。测试不等待最终媒体生成。

### 4.4 服务重启

第一阶段以 `pytest.mark.xfail` 记录“同一 job URL 在服务重启后仍可继续编辑”的目标行为，原因包含 Phase A。测试正文必须表达目标结果；Phase A 实现后只移除 xfail，不重写断言。

## 5. 失败诊断

- 未处理 `pageerror`、严重 console error 和非预期失败请求导致用例失败；
- 失败时可将 screenshot/trace 写入 pytest 临时目录，但不得写入仓库固定路径或纳入版本控制；
- fixture 启动应有健康检查超时，关闭应有线程 join 超时，避免测试挂死；
- 浏览器二进制缺失时给出明确的 `playwright install chromium` 提示，不静默跳过整套用例。

## 6. 兼容与回滚

Phase 0 只增加测试依赖、测试 fixture、行为用例和运行说明。测试基础设施与后续业务改造分开提交；若 Playwright 在目标环境不可用，可回滚本任务而不影响产品运行。不得为了让基线通过而修改现有前端行为。
