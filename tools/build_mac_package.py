from __future__ import annotations

import os
import shutil
import stat
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "video-text-editor-mac-8003"
FONT_PACKAGE_NAME = "video-text-editor-fonts-builtin"
BUILD_DIR = ROOT / "build" / PACKAGE_NAME
DIST_DIR = ROOT / "dist"
ZIP_PATH = DIST_DIR / f"{PACKAGE_NAME}.zip"
FONT_ZIP_PATH = DIST_DIR / f"{FONT_PACKAGE_NAME}.zip"
WINDOWS_FONT_DIR = Path(os.getenv("WINDIR", r"C:\Windows")) / "Fonts"
BUILTIN_FONT_FILENAMES = (
    "msyh.ttc",
    "msyhbd.ttc",
    "simhei.ttf",
    "simsun.ttc",
    "simkai.ttf",
    "simfang.ttf",
)

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
PORT="${PORT:-8003}"
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

CERTIFI_BUNDLE="$("${VENV_DIR}/bin/python" - <<'PY'
import certifi
print(certifi.where())
PY
)"
export SSL_CERT_FILE="${SSL_CERT_FILE:-${CERTIFI_BUNDLE}}"
export REQUESTS_CA_BUNDLE="${REQUESTS_CA_BUNDLE:-${CERTIFI_BUNDLE}}"

if [ ! -f ".env" ]; then
  cp ".env.example" ".env"
  echo ""
  echo "已创建 .env。需要在线识别/生成能力时，请在 .env 里填写 DASHSCOPE_API_KEY 和 ARK_API_KEY。"
fi

mkdir -p data/jobs data/history data/fonts/builtin data/art-templates data/art-position-presets data/models

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

http://127.0.0.1:8003/

安装包只包含程序代码、内置字体和空白数据目录，不包含打包电脑上的任务视频、历史记录、模型缓存或自定义模板。

首次在语音附近保存剪辑边界时，程序会按需下载固定版本的 FunASR `fa-zh` 模型到 `data/models`。模型权重约 159 MB，Python 运行时和依赖还会占用更多磁盘与内存；模型下载、校验、加载或推理失败时会安全降级，不会阻断草稿保存。

首次运行会自动完成：

- 创建 `.venv` 虚拟环境
- 安装 `requirements.txt` 里的 Python 依赖
- 从 `.env.example` 生成本机 `.env`
- 初始化本机的任务、历史、字体和模板目录
- 打开浏览器并启动 FastAPI 服务

需要的本机环境：

- macOS
- Python 3.11 或 3.12
- FFmpeg/FFprobe，推荐用 `brew install ffmpeg`
- 首次使用声学边界校准时可访问模型下载服务；离线使用前请先完成模型缓存和真实语音剪辑验证

在线语音识别、Seedream、Seedance 需要在 `.env` 填写：

- `DASHSCOPE_API_KEY`
- `ARK_API_KEY`

默认端口是 `8003`。如果要临时换端口，在终端里运行：

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


def clean_previous_outputs() -> None:
    for path in (ROOT / "build", DIST_DIR):
        if not path.exists():
            continue
        ensure_inside(path, ROOT)
        shutil.rmtree(path)


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
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".DS_Store"),
            )
        elif source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        else:
            raise FileNotFoundError(source)

    clean_data_files = {
        "jobs/.gitkeep": "\n",
        "history/.gitkeep": "\n",
        "models/.gitkeep": "\n",
        "fonts/manifest.json": "[]\n",
        "art-templates/manifest.json": "[]\n",
        "art-templates/hidden.json": "[]\n",
        "art-position-presets/manifest.json": "[]\n",
    }
    for relative, content in clean_data_files.items():
        path = BUILD_DIR / "data" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    (BUILD_DIR / "run_mac.command").write_text(RUN_MAC_COMMAND, encoding="utf-8", newline="\n")
    (BUILD_DIR / "run_mac.sh").write_text(RUN_MAC_SH, encoding="utf-8", newline="\n")
    (BUILD_DIR / "README_MAC.md").write_text(MAC_README, encoding="utf-8", newline="\n")

    for executable in (BUILD_DIR / "run_mac.command", BUILD_DIR / "run_mac.sh"):
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    bundled_font_dir = BUILD_DIR / "data" / "fonts" / "builtin"
    bundled_font_dir.mkdir(parents=True, exist_ok=True)
    for filename in BUILTIN_FONT_FILENAMES:
        source = WINDOWS_FONT_DIR / filename
        if not source.is_file():
            raise FileNotFoundError(
                f"Missing built-in font {source}. Set WINDIR to a Windows installation containing the font files."
            )
        shutil.copy2(source, bundled_font_dir / filename)


def add_to_zip(zip_file: zipfile.ZipFile, path: Path, archive_name: Path) -> None:
    info = zipfile.ZipInfo(str(archive_name).replace(os.sep, "/"))
    info.date_time = (2026, 7, 31, 12, 0, 0)
    if path.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm", ".mp3", ".wav", ".jpg", ".jpeg", ".png"}:
        info.compress_type = zipfile.ZIP_STORED
    else:
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


def build_font_zip() -> None:
    if FONT_ZIP_PATH.exists():
        ensure_inside(FONT_ZIP_PATH, DIST_DIR)
        FONT_ZIP_PATH.unlink()

    readme = (
        "Font files for the video text editor.\n\n"
        "Merge the data/fonts/builtin/ directory from this archive into the same path in the Mac package.\n"
    ).encode("utf-8")
    with zipfile.ZipFile(FONT_ZIP_PATH, "w") as zip_file:
        info = zipfile.ZipInfo("README.txt")
        info.date_time = (2026, 7, 31, 12, 0, 0)
        info.compress_type = zipfile.ZIP_DEFLATED
        zip_file.writestr(info, readme)
        font_dir = BUILD_DIR / "data" / "fonts" / "builtin"
        for path in sorted(font_dir.iterdir()):
            add_to_zip(zip_file, path, Path("data") / "fonts" / "builtin" / path.name)


def main() -> None:
    clean_previous_outputs()
    copy_project_files()
    build_zip()
    build_font_zip()
    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    font_size_mb = FONT_ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"Built {ZIP_PATH} ({size_mb:.2f} MB)")
    print(f"Built {FONT_ZIP_PATH} ({font_size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
