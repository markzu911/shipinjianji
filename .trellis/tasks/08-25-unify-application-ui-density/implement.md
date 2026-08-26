# 统一全应用 UI 密度实施计划

## Phase 0: Baseline And Failure Tests

- [x] 在 1912px 与 375px 的 seeded editor 中记录 preview pane/panel/stage/video/canvas、inspector、公共时间轴及独立图层时间轴的 computed rect。
- [x] 新增失败测试，锁定预览几何不变、页面无横向溢出、radio 等宽等高、时间轴目标高度和资源 cache-buster。
- [x] 记录无效果、一行效果和多行效果轨的当前动态高度，以及 seek/split/drag 的 source time 基线。

Rollback point：只增加测试和基线记录，不改运行时样式。

## Phase 1: Shared Density Tokens And Main Editor

- [x] 在 `styles.css` 建立 compact density token，按主导航、上传/处理、右侧 inspector、卡片、表单和按钮分组应用。
- [x] 保持 `.text-editor-workspace`、art/pip workspace 的预览列约束，不改 preview panel/stage/video/canvas 的 zoom、transform、width/height 和 contain/cover。
- [x] 保留 `.segment-item` 紧凑行/22px 控件并提高正文、时间、状态、空白说明及图标字号；将 `.editor-pip-tool-panel` 保持为 `zoom: 0.6`，增加防止二次压缩、radio 扭曲、中文小字发虚的字体/500/700 字重，以及覆盖初始表单和生成素材卡的 15/16/17px 字号下限。
- [x] 将 PiP 文案片段时间列扩展到 64px，与正文保留 12px gap；验证最长时间完整显示、正文 ellipsis、radio 完整和桌面/375px 无重叠溢出。
- [x] 核对文字、艺术字和画中画 inspector 的滚动高度、sticky 工具栏和选择项自动滚动。

Rollback point：密度规则集中在独立 CSS section，可整体撤回且不触及业务状态。

## Phase 2: Timeline 15% Compact Geometry

- [x] 将公共时间轴 ruler/text/base track 调整为 15/26/78px，并同步缩略图、clip、range、playhead 和 label 纵向几何。
- [x] 将 `editor-timeline-controller.js` 的动态效果行高调整为 26px、effect base 调整为 63px；统一 CSS fallback 与运行时一行/多行高度。
- [x] 将艺术字/画中画独立图层时间轴总高调整为 63px，并同步 clip 和 ruler。
- [x] 保持 track 宽度、scroll、left/width 百分比、source/edited 映射、分割和 resize 横向命中不变。

Rollback point：时间轴 token 与 controller 常量成对恢复，禁止只回滚一侧。

## Phase 3: Settings And Asset Libraries

- [x] 将设置页标题、provider card、字段、状态、帮助文字和动作区接入 compact token；移动端主要输入和按钮保留约 44px 命中区。
- [x] 将字体管理和艺术字模板库的 toolbar、filter、card、metadata、dialog 和间距统一为相同密度。
- [x] 保留字体/艺术字真实样式预览的内容尺度，避免把素材样式当作 UI 字号缩小。
- [x] 验证桌面多列与 375px 单列的滚动、焦点、弹窗和无横向溢出。

Rollback point：独立页面 profile 可分别撤回，不影响主编辑器。

## Phase 4: Cache, Integration And Regression

- [x] 更新 `styles.css` 及实际变更脚本在全部引用页面中的 cache-buster，并同步静态契约。
- [x] 运行 CSS/HTML/JS 契约测试及完整 Python 定向测试。
- [x] 真实浏览器验证 1912px/375px、普通/抖音预览、cut/art/pip 切换、文案播放、时间轴缩略帧、split、drag/resize 和设置/素材库页面。
- [x] 检查 console/pageerror/失败请求、基础 video identity、`srcWrites/loadCalls`、页面 scrollWidth 和所有时间轴子层实际高度。
- [x] 运行 Trellis quality check，处理所有 P0/P1/P2 后再更新规格与提交。

## Validation Commands

```powershell
node --check web/app.js
node --check web/editor-suite.js
node --check web/editor-timeline-controller.js
py -3 -m pytest tests/app/test_frontend_contracts.py -q
py -3 -m pytest tests/app/browser/test_editor_workflows.py -k "ui_density or timeline or preview or editor_tool" -q
py -3 -m pytest tests/app/browser -q
py -3 -m pytest -q
```

浏览器验收必须保存改动前后同 viewport 的几何数据；不能只凭截图判断预览未变或时间轴已缩小。
