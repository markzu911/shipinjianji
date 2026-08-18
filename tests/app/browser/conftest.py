from __future__ import annotations

import copy
import shutil
import socket
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pytest
import uvicorn
from PIL import Image

import server.app as app_module


ICONIFY_STUB = """
if (!customElements.get("iconify-icon")) {
  customElements.define("iconify-icon", class extends HTMLElement {});
}
"""


class LiveServer:
    def __init__(self) -> None:
        self.host = "127.0.0.1"
        self.port = 0
        self._server: uvicorn.Server | None = None
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def _bind_socket(self) -> socket.socket:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(128)
        self.port = int(server_socket.getsockname()[1])
        return server_socket

    def start(self) -> None:
        self._socket = self._bind_socket()
        config = uvicorn.Config(
            app_module.app,
            host=self.host,
            port=self.port,
            log_config=None,
            access_log=False,
            lifespan="on",
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._server.run,
            kwargs={"sockets": [self._socket]},
            daemon=True,
            name=f"browser-test-uvicorn-{self.port}",
        )
        self._thread.start()
        deadline = time.monotonic() + 10
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                response = httpx.get(f"{self.base_url}/api/health", timeout=1)
                response.raise_for_status()
                return
            except (httpx.HTTPError, OSError) as exc:
                last_error = exc
                time.sleep(0.05)
        self.stop()
        raise RuntimeError(
            f"临时浏览器测试服务未能启动：{last_error or '健康检查超时'}"
        )

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        shutdown_failed = False
        if self._thread is not None:
            self._thread.join(timeout=10)
            if self._thread.is_alive() and self._server is not None:
                self._server.force_exit = True
                if self._socket is not None:
                    try:
                        self._socket.close()
                    except OSError:
                        pass
                    self._socket = None
                self._thread.join(timeout=5)
            if self._thread.is_alive():
                shutdown_failed = True
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
        self._server = None
        self._socket = None
        self._thread = None
        if shutdown_failed:
            raise RuntimeError("临时浏览器测试服务未能在超时内关闭。")

    def restart_without_memory_state(self) -> None:
        self.stop()
        with app_module.JOBS_LOCK:
            app_module.JOBS.clear()
            app_module.JOB_FILES.clear()
        self.start()


@dataclass(frozen=True)
class SeededEditorJob:
    job_id: str
    video_path: Path
    art_overlay: dict[str, object]
    pip_overlay: dict[str, object]
    pip_asset_id: str


@dataclass
class BrowserSession:
    page: object
    context: object
    base_url: str
    diagnostics_dir: Path
    console_errors: list[str] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    failed_requests: list[str] = field(default_factory=list)
    http_errors: list[str] = field(default_factory=list)
    external_requests: list[str] = field(default_factory=list)

    def diagnostics(self) -> list[str]:
        return [
            *(f"console: {message}" for message in self.console_errors),
            *(f"pageerror: {message}" for message in self.page_errors),
            *(f"requestfailed: {message}" for message in self.failed_requests),
            *(f"http: {message}" for message in self.http_errors),
            *(f"external: {message}" for message in self.external_requests),
        ]


@pytest.fixture
def browser_server(isolated_jobs) -> LiveServer:
    server = LiveServer()
    server.start()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture(scope="module")
def chromium_browser():
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError as exc:
        pytest.fail(
            "缺少 Playwright。请先运行："
            ".\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt",
            pytrace=False,
        )

    runtime = sync_playwright().start()
    browser = None
    try:
        try:
            browser = runtime.chromium.launch(headless=True)
        except Error as exc:
            installed_browser = next(
                (
                    path
                    for path in (
                        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
                        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
                        Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
                        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
                    )
                    if path.is_file()
                ),
                None,
            )
            if installed_browser is None:
                pytest.fail(
                    "缺少 Playwright Chromium。请先运行："
                    ".\\.venv\\Scripts\\python.exe -m playwright install chromium\n"
                    f"原始错误：{exc}",
                    pytrace=False,
                )
            browser = runtime.chromium.launch(
                headless=True,
                executable_path=str(installed_browser),
            )
        yield browser
    finally:
        if browser is not None:
            browser.close()
        runtime.stop()


@pytest.fixture
def browser_session(
    chromium_browser,
    browser_server: LiveServer,
    tmp_path: Path,
) -> BrowserSession:
    context = chromium_browser.new_context(
        accept_downloads=False,
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
    )
    session = BrowserSession(
        page=None,
        context=context,
        base_url=browser_server.base_url,
        diagnostics_dir=tmp_path,
    )
    allowed_origin = urlparse(browser_server.base_url)

    def route_request(route) -> None:
        request_url = route.request.url
        parsed = urlparse(request_url)
        if parsed.scheme in {"data", "blob"}:
            route.continue_()
            return
        if (
            parsed.scheme == allowed_origin.scheme
            and parsed.hostname == allowed_origin.hostname
            and parsed.port == allowed_origin.port
        ):
            if parsed.path == "/favicon.ico":
                route.fulfill(status=204, body="")
            else:
                route.continue_()
            return
        if parsed.hostname == "code.iconify.design":
            route.fulfill(
                status=200,
                content_type="application/javascript",
                body=ICONIFY_STUB,
            )
            return
        session.external_requests.append(request_url)
        route.abort("blockedbyclient")

    context.route("**/*", route_request)
    page = context.new_page()
    session.page = page

    page.on("pageerror", lambda error: session.page_errors.append(str(error)))
    page.on(
        "console",
        lambda message: session.console_errors.append(message.text)
        if message.type == "error"
        else None,
    )

    def record_failed_request(request) -> None:
        failure = request.failure or "unknown failure"
        parsed = urlparse(request.url)
        is_local = (
            parsed.scheme == allowed_origin.scheme
            and parsed.hostname == allowed_origin.hostname
            and parsed.port == allowed_origin.port
        )
        if is_local and "ERR_ABORTED" not in failure:
            session.failed_requests.append(f"{request.method} {request.url}: {failure}")

    page.on("requestfailed", record_failed_request)
    page.on(
        "response",
        lambda response: session.http_errors.append(
            f"{response.status} {response.request.method} {response.url}"
        )
        if response.status >= 400
        else None,
    )

    try:
        yield session
        page.wait_for_timeout(50)
        diagnostics = session.diagnostics()
        if diagnostics:
            screenshot_path = tmp_path / "browser-diagnostics.png"
            try:
                page.screenshot(path=str(screenshot_path), full_page=True)
            except Exception:
                pass
            pytest.fail("浏览器出现未预期诊断：\n" + "\n".join(diagnostics))
    finally:
        context.close()


@pytest.fixture
def seeded_editor_job(sample_video: Path) -> SeededEditorJob:
    job_id = "81818181-8181-4181-8181-818181818181"
    job_dir = app_module.jobs_directory() / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    video_path = job_dir / "browser-baseline.mp4"
    shutil.copyfile(sample_video, video_path)
    shutil.copyfile(sample_video, job_dir / "art-text.mp4")
    shutil.copyfile(sample_video, job_dir / "picture-in-picture.mp4")

    asset_id = "browser-baseline-image"
    Image.new("RGB", (160, 90), "#e8c547").save(
        job_dir / f"picture-in-picture-{asset_id}.png",
        "PNG",
    )
    image_url = (
        f"/api/transcriptions/{job_id}/picture-in-picture/images/{asset_id}"
    )
    art_overlay: dict[str, object] = {
        "text": "保留内容",
        "font": "bold",
        "fontSize": 48,
        "color": "#FFD84D",
        "strokeColor": "#071018",
        "strokeWidth": 3,
        "shadow": True,
        "x": 0.5,
        "y": 0.78,
        "start": 0.4,
        "end": 0.85,
        "sourceStart": 0.4,
        "sourceEnd": 0.85,
        "artStyle": "impact",
        "direction": "horizontal",
        "textAlign": "center",
        "charsPerLine": 10,
        "letterSpacing": 0,
        "lineSpacing": 8,
    }
    pip_overlay: dict[str, object] = {
        "assetId": asset_id,
        "start": 0.45,
        "end": 0.8,
        "sourceStart": 0.45,
        "sourceEnd": 0.8,
        "x": 0.76,
        "y": 0.24,
        "width": 0.3,
    }
    segments = [
        {
            "id": 0,
            "start": 0.05,
            "end": 0.3,
            "text": "删除片段",
            "words": [
                {"text": "删除", "start": 0.05, "end": 0.17},
                {"text": "片段", "start": 0.17, "end": 0.3},
            ],
        },
        {
            "id": 1,
            "start": 0.35,
            "end": 0.95,
            "text": "保留内容",
            "words": [
                {"text": "保留", "start": 0.35, "end": 0.58},
                {"text": "内容", "start": 0.58, "end": 0.95},
            ],
        },
    ]
    now = "2026-08-18T05:00:00+00:00"
    job = {
        "id": job_id,
        "filename": video_path.name,
        "duration": 1.0,
        "status": "completed",
        "stage": "文字识别完成",
        "progress": 100,
        "result": {
            "text": "删除片段\n保留内容",
            "duration": 1.0,
            "mediaDuration": 1.0,
            "segments": segments,
            "editableSegments": copy.deepcopy(segments),
            "suggestions": [],
            "suggestionStatus": "completed",
            "noSpeechSuggestions": [],
            "noSpeechStatus": "completed",
            "audioQuietRanges": [],
        },
        "cutDraft": None,
        "edit": None,
        "art": {
            "status": "completed",
            "stage": "艺术字视频生成完成",
            "progress": 100,
            "source": "original",
            "composition": False,
            "overlays": [copy.deepcopy(art_overlay)],
            "outputUrl": f"/api/transcriptions/{job_id}/art-text-video",
            "outputDuration": 1.0,
            "error": None,
            "createdAt": now,
            "updatedAt": now,
        },
        "artSuggestion": None,
        "pictureInPictureImages": [
            {
                "id": asset_id,
                "text": "保留内容",
                "prompt": "确定性的黄色测试画面",
                "source": "art",
                "start": 0.45,
                "end": 0.8,
                "sourceStart": 0.45,
                "sourceEnd": 0.8,
                "aspectRatio": "16:9",
                "imageUrl": image_url,
                "assetUrl": image_url,
                "createdAt": now,
            }
        ],
        "pictureInPictureVideos": [],
        "pictureInPicture": {
            "status": "completed",
            "stage": "画中画视频生成完成",
            "progress": 100,
            "source": "art",
            "overlays": [copy.deepcopy(pip_overlay)],
            "outputUrl": f"/api/transcriptions/{job_id}/picture-in-picture-video",
            "outputDuration": 1.0,
            "error": None,
            "createdAt": now,
            "updatedAt": now,
        },
        "composition": None,
        "createdAt": now,
        "updatedAt": now,
    }
    with app_module.JOBS_LOCK:
        app_module.JOBS[job_id] = job
        app_module.JOB_FILES[job_id] = video_path

    return SeededEditorJob(
        job_id=job_id,
        video_path=video_path,
        art_overlay=art_overlay,
        pip_overlay=pip_overlay,
        pip_asset_id=asset_id,
    )
