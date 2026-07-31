from __future__ import annotations

import os
import shutil
import stat
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "video-text-editor-mac-8888"
BUILD_DIR = ROOT / "build" / PACKAGE_NAME
DIST_DIR = ROOT / "dist"
ZIP_PATH = DIST_DIR / f"{PACKAGE_NAME}.zip"

PROJECT_FILES = [
    "server",
    "web",
    "tests",
    "requirements.txt",
    ".env.example",
    "README.md",
    "01-产品需求文档-PRD.md",
    "02-技术开发文档.md",
    "03-功能完善建议.md",
]

RUN_MAC_COMMAND = """#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8888}"
URL="http://${HOST}:${PORT}/"
VENV_DIR="${VENV_DIR:-.venv}"

echo ""
echo "视频文字剪辑 - Mac 一键启动"
echo "项目目录: $(pwd)"
echo "运行地址: ${URL}"
echo ""

if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "端口 ${PORT} 已被占用。请先关闭占用该端口的程序，或用 PORT=其它端口 ./run_mac.command 启动。"
  echo ""
  read -r -p "按回车退出..."
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "${PYTHON_BIN}" ]; then
  for candidate in python3.12 python3.11 python3; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      PYTHON_BIN="${candidate}"
      break
    fi
  done
fi

if [ -z "${PYTHON_BIN}" ]; then
  echo "没有找到 Python 3。请先安装 Python 3.11 或 3.12。"
  echo "推荐: brew install python@3.12"
  echo ""
  read -r -p "按回车退出..."
  exit 1
fi

"${PYTHON_BIN}" - <<'PY'
import sys

if sys.version_info < (3, 11):
    raise SystemExit("需要 Python 3.11 或更高版本。")
PY

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "提醒: 当前 Mac 没有检测到 FFmpeg/FFprobe。"
  echo "视频上传、剪辑、合成需要它们。推荐安装: brew install ffmpeg"
  echo ""
fi

if [ ! -d "${VENV_DIR}" ]; then
  echo "创建 Python 虚拟环境..."
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

echo "安装/检查 Python 依赖..."
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp ".env.example" ".env"
  echo ""
  echo "已创建 .env。需要在线识别/生成能力时，请在 .env 里填写 DASHSCOPE_API_KEY 和 ARK_API_KEY。"
fi

mkdir -p data/jobs data/history data/fonts data/art-templates data/models

echo ""
echo "正在启动服务..."
echo "浏览器将打开: ${URL}"
echo "关闭这个终端窗口即可停止服务。"
echo ""

( sleep 2; open "${URL}" >/dev/null 2>&1 || true ) &
exec "${VENV_DIR}/bin/python" -m uvicorn server.app:app --host "${HOST}" --port "${PORT}"
"""

RUN_MAC_SH = """#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "${DIR}/run_mac.command"
"""

MAC_README = """# Mac 一键运行说明

双击 `run_mac.command` 即可启动项目，默认地址是：

http://127.0.0.1:8888/

首次运行会自动完成：

- 创建 `.venv` 虚拟环境
- 安装 `requirements.txt` 里的 Python 依赖
- 从 `.env.example` 生成本机 `.env`
- 创建干净的 `data/` 工作目录
- 打开浏览器并启动 FastAPI 服务

需要的本机环境：

- macOS
- Python 3.11 或 3.12
- FFmpeg/FFprobe，推荐用 `brew install ffmpeg`

在线语音识别、Seedream、Seedance 需要在 `.env` 填写：

- `DASHSCOPE_API_KEY`
- `ARK_API_KEY`

默认端口是 `8888`。如果要临时换端口，在终端里运行：

```bash
PORT=8899 ./run_mac.command
```

关闭启动脚本打开的终端窗口，服务就会停止。
"""


def ensure_inside(child: Path, parent: Path) -> None:
    child_resolved = child.resolve()
    parent_resolved = parent.resolve()
    if child_resolved != parent_resolved and parent_resolved not in child_resolved.parents:
        raise RuntimeError(f"Refusing to touch path outside workspace: {child_resolved}")


def copy_project_files() -> None:
    if BUILD_DIR.exists():
        ensure_inside(BUILD_DIR, ROOT / "build")
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    for relative in PROJECT_FILES:
        source = ROOT / relative
        target = BUILD_DIR / relative
        if source.is_dir():
            shutil.copytree(
                source,
                target,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
            )
        elif source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        else:
            raise FileNotFoundError(source)

    (BUILD_DIR / "run_mac.command").write_text(RUN_MAC_COMMAND, encoding="utf-8", newline="\n")
    (BUILD_DIR / "run_mac.sh").write_text(RUN_MAC_SH, encoding="utf-8", newline="\n")
    (BUILD_DIR / "README_MAC.md").write_text(MAC_README, encoding="utf-8", newline="\n")

    for executable in (BUILD_DIR / "run_mac.command", BUILD_DIR / "run_mac.sh"):
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def add_to_zip(zip_file: zipfile.ZipFile, path: Path, archive_name: Path) -> None:
    info = zipfile.ZipInfo(str(archive_name).replace(os.sep, "/"))
    info.date_time = (2026, 7, 31, 12, 0, 0)
    info.compress_type = zipfile.ZIP_DEFLATED

    mode = path.stat().st_mode
    if path.name in {"run_mac.command", "run_mac.sh"}:
        mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    info.external_attr = (mode & 0xFFFF) << 16

    with path.open("rb") as source:
        zip_file.writestr(info, source.read())


def build_zip() -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists():
        ensure_inside(ZIP_PATH, DIST_DIR)
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w") as zip_file:
        for path in sorted(BUILD_DIR.rglob("*")):
            if path.is_file():
                archive_name = Path(PACKAGE_NAME) / path.relative_to(BUILD_DIR)
                add_to_zip(zip_file, path, archive_name)


def main() -> None:
    copy_project_files()
    build_zip()
    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"Built {ZIP_PATH} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
