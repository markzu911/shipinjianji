from __future__ import annotations

import json
import re
import statistics
import time

import pytest

import server.app as app_module


def open_editor(session, job):
    page = session.page
    page.goto(f"{session.base_url}/?job={job.job_id}")
    page.locator("#resultCard").wait_for(state="visible")
    page.locator("#segmentList .segment-item").first.wait_for(state="visible")
    return page


def delete_first_text_segment(page) -> dict[str, object]:
    delete_button = page.get_by_role(
        "button",
        name=re.compile(r"删除文字：删除片段"),
    )
    delete_button.click()
    page.locator("#cutDraftSaveStatus").filter(
        has_text="剪辑草稿已保存"
    ).wait_for()
    return page.evaluate(
        """async () => {
          const response = await fetch(
            `/api/transcriptions/${new URLSearchParams(location.search).get("job")}/cut-draft`
          );
          return response.json();
        }"""
    )["cutDraft"]


def wait_for_preview_time(page, expected: float) -> None:
    page.wait_for_function(
        """expected => {
          const video = document.querySelector("#cutPreviewVideo");
          return video && Math.abs(video.currentTime - expected) <= 0.06;
        }""",
        arg=expected,
    )


def install_base_media_mutation_probe(page) -> None:
    page.locator("#cutPreviewVideo").evaluate(
        """video => {
          const descriptor = Object.getOwnPropertyDescriptor(
            HTMLMediaElement.prototype,
            'src',
          );
          const originalLoad = video.load;
          window.__b1MediaMutationProbe = { srcWrites: 0, loadCalls: 0 };
          Object.defineProperty(video, 'src', {
            configurable: true,
            get() { return descriptor.get.call(this); },
            set(value) {
              window.__b1MediaMutationProbe.srcWrites += 1;
              descriptor.set.call(this, value);
            },
          });
          video.load = function loadWithProbe() {
            window.__b1MediaMutationProbe.loadCalls += 1;
            return originalLoad.call(this);
          };
        }"""
    )


def base_media_mutations(page) -> dict[str, int]:
    return page.evaluate("window.__b1MediaMutationProbe")


def install_cut_performance_probe(page) -> None:
    page.add_init_script(
        """(() => {
          const originalCreateElement = Document.prototype.createElement;
          const originalSetItem = Storage.prototype.setItem;
          const originalFetch = window.fetch.bind(window);
          window.__cutPerformanceProbe = {
            createdVideos: 0,
            historyWrites: 0,
            putCalls: 0,
            putInFlight: 0,
            putMaxInFlight: 0,
            storeActions: [],
            longTasks: [],
          };
          if (PerformanceObserver.supportedEntryTypes?.includes('longtask')) {
            new PerformanceObserver(list => {
              window.__cutPerformanceProbe.longTasks.push(
                ...list.getEntries().map(entry => entry.duration),
              );
            }).observe({ type: 'longtask', buffered: true });
          }
          Document.prototype.createElement = function createElementWithProbe(
            name,
            options,
          ) {
            const element = originalCreateElement.call(this, name, options);
            if (String(name).toLowerCase() === 'video') {
              window.__cutPerformanceProbe.createdVideos += 1;
            }
            return element;
          };
          Storage.prototype.setItem = function setItemWithProbe(key, value) {
            if (String(key).startsWith('video-editor:cut-history:')) {
              window.__cutPerformanceProbe.historyWrites += 1;
            }
            return originalSetItem.call(this, key, value);
          };
          window.fetch = async (...args) => {
            const input = args[0];
            const options = args[1] || {};
            const url = String(input?.url || input || '');
            const isDraftPut = options.method === 'PUT'
              && url.includes('/cut-draft');
            if (isDraftPut) {
              window.__cutPerformanceProbe.putCalls += 1;
              window.__cutPerformanceProbe.putInFlight += 1;
              window.__cutPerformanceProbe.putMaxInFlight = Math.max(
                window.__cutPerformanceProbe.putMaxInFlight,
                window.__cutPerformanceProbe.putInFlight,
              );
            }
            try {
              return await originalFetch(...args);
            } finally {
              if (isDraftPut) window.__cutPerformanceProbe.putInFlight -= 1;
            }
          };
        })()"""
    )


def reset_cut_performance_probe(page) -> None:
    page.evaluate(
        """() => {
          const probe = window.__cutPerformanceProbe;
          probe.createdVideos = 0;
          probe.historyWrites = 0;
          probe.putCalls = 0;
          probe.putInFlight = 0;
          probe.putMaxInFlight = 0;
          probe.storeActions = [];
          probe.longTasks = [];
          probe.commitCount = 0;
          probe.commitBreakdowns = [];
          probe.unsubscribe?.();
          probe.unsubscribe = window.EditorSuite.subscribeProject(
            (_next, _previous, action) => probe.storeActions.push(action.type),
          );
        }"""
    )


def route_cut_draft_echo(page, job_id: str) -> None:
    revision = {"value": 1}

    def fulfill(route) -> None:
        request = json.loads(route.request.post_data or "{}")
        revision["value"] += 1
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "cutDraft": {
                        "schemaVersion": 1,
                        **request,
                        "revision": revision["value"],
                        "boundaryDiagnostics": [],
                        "acousticAlignment": {"status": "unavailable"},
                        "updatedAt": "2026-08-21T00:00:01+00:00",
                    }
                },
                ensure_ascii=False,
            ),
        )

    page.route(
        re.compile(rf".*/api/transcriptions/{job_id}/cut-draft$"),
        fulfill,
    )


def route_cut_draft_recording(
    page,
    job_id: str,
    *,
    delay_first: float = 0.0,
    fail_first: bool = False,
) -> list[dict[str, object]]:
    revision = {"value": 1}
    requests: list[dict[str, object]] = []

    def fulfill(route) -> None:
        request = json.loads(route.request.post_data or "{}")
        requests.append(request)
        if len(requests) == 1 and delay_first > 0:
            time.sleep(delay_first)
        if len(requests) == 1 and fail_first:
            route.fulfill(
                status=500,
                content_type="application/json",
                body=json.dumps({"detail": "模拟草稿保存失败"}, ensure_ascii=False),
            )
            return
        revision["value"] += 1
        response_draft = {**request, "revision": revision["value"]}
        if len(requests) == 1 and request.get("textRanges"):
            response_draft["textRanges"] = [
                {
                    **item,
                    "start": max(0.0, float(item["start"]) - 0.02),
                    "end": float(item["end"]) + 0.02,
                }
                for item in request["textRanges"]
            ]
        response_draft.update(
            {
                "schemaVersion": 1,
                "boundaryDiagnostics": [],
                "acousticAlignment": {"status": "unavailable"},
                "updatedAt": "2026-08-21T00:00:01+00:00",
            }
        )
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"cutDraft": response_draft}, ensure_ascii=False),
        )

    page.route(
        re.compile(rf".*/api/transcriptions/{job_id}/cut-draft$"),
        fulfill,
    )
    return requests


def test_cut_interaction_long_fixture_performance_and_work_counts(
    browser_session,
    seeded_performance_editor_job,
):
    page = browser_session.page
    install_cut_performance_probe(page)
    route_cut_draft_echo(page, seeded_performance_editor_job.job_id)
    open_editor(browser_session, seeded_performance_editor_job)
    page.wait_for_function(
        """() => {
          const items = [...document.querySelectorAll(
            '#cutFrameTimelineThumbnails .frame-timeline-thumb'
          )];
          return items.length >= 8
            && items.every(item => !item.classList.contains('is-loading'));
        }"""
    )
    thumbnail_projection = page.evaluate(
        """() => {
          const duration = 60;
          const layer = document.querySelector('#cutFrameTimelineThumbnails');
          const layerHeight = layer.getBoundingClientRect().height;
          const items = [...document.querySelectorAll(
            '#cutFrameTimelineThumbnails .frame-timeline-thumb'
          )].filter(item => !item.hidden);
          const positions = items.map(item => ({
            left: Number.parseFloat(item.style.left),
            right: Number.parseFloat(item.style.left)
              + Number.parseFloat(item.style.width),
          })).sort((left, right) => left.left - right.left);
          return {
            allPositioned: items.every(
              item => item.style.position === 'absolute'
                && Number.parseFloat(item.style.width) > 0
            ),
            allVisible: items.length > 0 && items.every(item => {
              const height = item.getBoundingClientRect().height;
              return height > 0 && Math.abs(height - layerHeight) <= 0.5;
            }),
            allHaveFrames: items.every(
              item => item.style.backgroundImage.startsWith('url(')
            ),
            remapped: items.some(item => {
              const sourcePercent = Number(item.dataset.sourceTime) / duration * 100;
              return Math.abs(Number.parseFloat(item.style.left) - sourcePercent) > 0.1;
            }),
            continuousCoverage: positions.length > 0
              && Math.abs(positions[0].left) <= 0.1
              && Math.abs(positions.at(-1).right - 100) <= 0.1
              && positions.slice(1).every((position, index) =>
                Math.abs(position.left - positions[index].right) <= 0.1
              ),
          };
        }"""
    )
    assert thumbnail_projection == {
        "allPositioned": True,
        "allVisible": True,
        "allHaveFrames": True,
        "remapped": True,
        "continuousCoverage": True,
    }
    assert page.locator("#segmentList .segment-item").count() >= 60
    assert len(page.locator("#segmentList").inner_text().replace("\n", "")) >= 600
    install_base_media_mutation_probe(page)
    reset_cut_performance_probe(page)

    durations = page.evaluate(
        """async () => {
          const values = [];
          const states = [];
          for (let index = 0; index < 10; index += 1) {
            const item = [...document.querySelectorAll(
              '.segment-item[data-segment-index]'
            )].find(candidate => candidate.dataset.displayText.includes(
              '性能回归00测试文本'
            ));
            const button = item?.querySelector('.segment-toggle');
            const before = button?.getAttribute('aria-label');
            const started = performance.now();
            button?.click();
            const afterClick = performance.now();
            await new Promise(resolve => requestAnimationFrame(resolve));
            const afterFirstFrame = performance.now();
            await new Promise(resolve => requestAnimationFrame(resolve));
            const afterSecondFrame = performance.now();
            const after = [...document.querySelectorAll(
              '.segment-item[data-segment-index]'
            )].find(candidate => candidate.dataset.displayText.includes(
              '性能回归00测试文本'
            ))?.querySelector('.segment-toggle')?.getAttribute('aria-label');
            states.push({ before, after });
            values.push({
              sync: afterClick - started,
              firstFrame: afterFirstFrame - afterClick,
              secondFrame: afterSecondFrame - afterFirstFrame,
              total: afterSecondFrame - started,
            });
          }
          return { states, values };
        }"""
    )
    page.wait_for_timeout(900)
    probe = page.evaluate("window.__cutPerformanceProbe")
    media_probe = base_media_mutations(page)
    assert all(
        state["before"] and state["after"] and state["before"] != state["after"]
        for state in durations["states"]
    ), durations["states"]
    ordered = sorted(value["total"] for value in durations["values"])
    p50 = statistics.median(ordered)
    p95 = ordered[max(0, int(len(ordered) * 0.95) - 1)]
    print(
        "cut-performance-baseline",
        {
            "rawMs": [
                {key: round(value[key], 3) for key in value}
                for value in durations["values"]
            ],
            "p50Ms": round(p50, 3),
            "p95Ms": round(p95, 3),
            "maxMs": round(max(ordered), 3),
            "probe": probe,
            "media": media_probe,
        },
    )

    assert p95 <= 100
    assert probe["createdVideos"] == 0
    assert probe["putCalls"] <= 1
    assert probe["putMaxInFlight"] <= 1
    assert probe["historyWrites"] <= 1
    assert all(duration <= 200 for duration in probe["longTasks"])
    assert media_probe == {"srcWrites": 0, "loadCalls": 0}


def test_cut_draft_burst_uses_one_trailing_save(
    browser_session,
    seeded_performance_editor_job,
):
    page = browser_session.page
    install_cut_performance_probe(page)
    requests = route_cut_draft_recording(
        page,
        seeded_performance_editor_job.job_id,
    )
    open_editor(browser_session, seeded_performance_editor_job)
    reset_cut_performance_probe(page)
    page.evaluate(
        """() => {
          const original = window.EditorSuite.setCutDraft.bind(window.EditorSuite);
          window.__cutDraftSyncCalls = 0;
          window.EditorSuite.setCutDraft = value => {
            window.__cutDraftSyncCalls += 1;
            return original(value);
          };
        }"""
    )

    page.evaluate(
        """() => {
          for (const segmentIndex of [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]) {
            document.querySelector(
              `.segment-item[data-segment-index="${segmentIndex}"] `
                + '.segment-toggle'
            )?.click();
          }
        }"""
    )
    page.locator("#cutDraftSaveStatus").filter(
        has_text="剪辑草稿已保存"
    ).wait_for()
    page.wait_for_timeout(450)

    probe = page.evaluate("window.__cutPerformanceProbe")
    assert len(requests) == 1
    assert probe["putCalls"] == 1
    assert probe["putMaxInFlight"] == 1
    assert page.evaluate("window.__cutDraftSyncCalls") == 2


def test_cut_draft_in_flight_edit_rebases_one_latest_request(
    browser_session,
    seeded_performance_editor_job,
):
    page = browser_session.page
    install_cut_performance_probe(page)
    requests = route_cut_draft_recording(
        page,
        seeded_performance_editor_job.job_id,
        delay_first=1.0,
    )
    open_editor(browser_session, seeded_performance_editor_job)
    reset_cut_performance_probe(page)

    page.evaluate(
        """() => {
          const clickSegment = segmentIndex => document.querySelector(
            `.segment-item[data-segment-index="${segmentIndex}"] `
              + '.segment-toggle'
          )?.click();
          clickSegment(1);
          setTimeout(() => clickSegment(3), 700);
        }"""
    )
    page.wait_for_function(
        """() => window.__cutPerformanceProbe.putCalls === 2
          && window.__cutPerformanceProbe.putInFlight === 0""",
        timeout=10_000,
    )

    probe = page.evaluate("window.__cutPerformanceProbe")
    assert len(requests) == 2
    assert probe["putMaxInFlight"] == 1
    assert requests[0]["revision"] == 1
    assert requests[1]["revision"] == 2
    assert len(requests[1]["textRanges"]) == len(requests[0]["textRanges"]) + 1
    first_request_range = next(
        item
        for item in requests[0]["textRanges"]
        if item["originalStart"] == pytest.approx(1.0)
    )
    latest_first_range = next(
        item
        for item in requests[1]["textRanges"]
        if item["originalStart"] == pytest.approx(1.0)
    )
    assert latest_first_range["start"] == pytest.approx(first_request_range["start"])
    assert latest_first_range["end"] == pytest.approx(first_request_range["end"])


def test_cut_draft_failed_save_retries_on_next_edit(
    browser_session,
    seeded_performance_editor_job,
):
    page = browser_session.page
    install_cut_performance_probe(page)
    requests = route_cut_draft_recording(
        page,
        seeded_performance_editor_job.job_id,
        fail_first=True,
    )
    open_editor(browser_session, seeded_performance_editor_job)
    reset_cut_performance_probe(page)

    page.locator('.segment-item[data-segment-index="1"] .segment-toggle').click()
    page.locator("#cutDraftSaveStatus").filter(
        has_text="模拟草稿保存失败"
    ).wait_for()
    expected_errors = [
        message
        for message in browser_session.http_errors
        if message.startswith("500 PUT ") and message.endswith("/cut-draft")
    ]
    assert len(expected_errors) == 1
    browser_session.http_errors.remove(expected_errors[0])
    expected_console_errors = [
        message
        for message in browser_session.console_errors
        if "server responded with a status of 500" in message
    ]
    assert len(expected_console_errors) == 1
    browser_session.console_errors.remove(expected_console_errors[0])
    page.locator('.segment-item[data-segment-index="3"] .segment-toggle').click()
    page.locator("#cutDraftSaveStatus").filter(
        has_text="剪辑草稿已保存"
    ).wait_for()

    probe = page.evaluate("window.__cutPerformanceProbe")
    assert len(requests) == 2
    assert requests[0]["revision"] == 1
    assert requests[1]["revision"] == 1
    assert probe["putMaxInFlight"] == 1


def test_cut_draft_synchronous_fetch_error_releases_queue_for_retry(
    browser_session,
    seeded_performance_editor_job,
):
    page = browser_session.page
    route_cut_draft_echo(page, seeded_performance_editor_job.job_id)
    open_editor(browser_session, seeded_performance_editor_job)
    page.evaluate(
        """() => {
          const originalFetch = window.fetch.bind(window);
          window.__synchronousDraftPutCalls = 0;
          window.fetch = (...args) => {
            const input = args[0];
            const options = args[1] || {};
            const url = String(input?.url || input || '');
            if (options.method === 'PUT' && url.includes('/cut-draft')) {
              window.__synchronousDraftPutCalls += 1;
              if (window.__synchronousDraftPutCalls === 1) {
                throw new TypeError('模拟同步请求失败');
              }
            }
            return originalFetch(...args);
          };
        }"""
    )

    page.locator('.segment-item[data-segment-index="1"] .segment-toggle').click()
    page.locator("#cutDraftSaveStatus").filter(
        has_text="模拟同步请求失败"
    ).wait_for()
    page.locator('.segment-item[data-segment-index="3"] .segment-toggle').click()
    page.locator("#cutDraftSaveStatus").filter(
        has_text="剪辑草稿已保存"
    ).wait_for()

    assert page.evaluate("window.__synchronousDraftPutCalls") == 2


def test_cut_undo_cancels_preview_from_superseded_command(
    browser_session,
    seeded_performance_editor_job,
):
    page = browser_session.page
    route_cut_draft_echo(page, seeded_performance_editor_job.job_id)
    open_editor(browser_session, seeded_performance_editor_job)
    page.wait_for_timeout(100)

    seek_calls = page.evaluate(
        """async () => {
          const controller = window.EditorSuite.mediaController();
          const originalSeekSource = controller.seekSource;
          const calls = [];
          controller.seekSource = seconds => calls.push(seconds);
          try {
            document.querySelector(
              '.segment-item[data-segment-index="1"] .segment-toggle'
            )?.click();
            document.dispatchEvent(new KeyboardEvent('keydown', {
              bubbles: true,
              cancelable: true,
              ctrlKey: true,
              key: 'z',
            }));
            await new Promise(resolve => requestAnimationFrame(resolve));
            await new Promise(resolve => requestAnimationFrame(resolve));
            await new Promise(resolve => setTimeout(resolve, 0));
            return calls;
          } finally {
            controller.seekSource = originalSeekSource;
          }
        }"""
    )

    assert seek_calls == []


def test_two_cut_commands_in_one_frame_keep_two_undo_transactions(
    browser_session,
    seeded_performance_editor_job,
):
    page = browser_session.page
    install_cut_performance_probe(page)
    route_cut_draft_echo(page, seeded_performance_editor_job.job_id)
    open_editor(browser_session, seeded_performance_editor_job)
    reset_cut_performance_probe(page)

    page.evaluate(
        """async () => {
          for (const segmentIndex of [0, 2]) {
            document.querySelector(
              `.segment-item[data-segment-index="${segmentIndex}"] `
                + '.segment-toggle'
            )?.click();
          }
          window.dispatchEvent(new Event('pagehide'));
          const jobId = new URLSearchParams(location.search).get('job');
          window.__pagehideCutHistory = JSON.parse(
            localStorage.getItem(`video-editor:cut-history:${jobId}`) || 'null'
          );
          await new Promise(resolve => requestAnimationFrame(resolve));
          await new Promise(resolve => requestAnimationFrame(resolve));
        }"""
    )
    page.wait_for_function(
        """() => window.__cutPerformanceProbe.storeActions.filter(
          type => type === 'cutTimingChanged'
        ).length === 1"""
    )
    cut_actions = page.evaluate(
        """window.__cutPerformanceProbe.storeActions.filter(
          type => type === 'cutTimingChanged'
        ).length"""
    )
    assert cut_actions == 1
    assert page.evaluate("window.__pagehideCutHistory.entries.length") == 2
    assert page.evaluate("window.__cutPerformanceProbe.commitCount") == 1
    assert page.evaluate(
        """window.__cutPerformanceProbe.storeActions.filter(
          type => type === 'projectHydrated'
        ).length"""
    ) == 0

    page.keyboard.press("Control+z")
    page.wait_for_function(
        """() => document.querySelector(
          '.segment-item[data-segment-index="2"] .segment-toggle'
        )?.getAttribute('aria-label')?.startsWith('恢复')"""
    )
    assert page.locator(
        '.segment-item[data-segment-index="0"] .segment-toggle'
    ).get_attribute("aria-label").startswith("删除")

    page.keyboard.press("Control+z")
    page.wait_for_function(
        """() => document.querySelector(
          '.segment-item[data-segment-index="0"] .segment-toggle'
        )?.getAttribute('aria-label')?.startsWith('恢复')"""
    )


def test_transcription_completion_loads_and_plays_preview_without_reload(
    browser_session,
    seeded_editor_job,
):
    page = browser_session.page
    job_url = (
        f"{browser_session.base_url}/api/transcriptions/"
        f"{seeded_editor_job.job_id}"
    )
    completed_job = page.request.get(job_url).json()
    response_state = {"completed": False}

    def fulfill_job(route) -> None:
        payload = json.loads(json.dumps(completed_job))
        if not response_state["completed"]:
            payload.update(
                status="transcribing",
                stage="Transcribing",
                progress=65,
                duration=0,
                result=None,
            )
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(payload, ensure_ascii=False),
        )

    page.route(job_url, fulfill_job)
    page.goto(f"{browser_session.base_url}/?job={seeded_editor_job.job_id}")
    page.wait_for_function(
        """() => window.EditorSuite?.projectSnapshot?.().project.job?.status
          === 'transcribing'"""
    )
    video = page.locator("#cutPreviewVideo")
    queued_media = video.evaluate(
        """video => ({
          src: video.getAttribute('src'),
          currentSrc: video.currentSrc,
          frameSource: window.EditorProjectStore.selectEditorFrame(
            window.EditorSuite.projectSnapshot(),
          ).media.sourceUrl,
        })"""
    )
    assert queued_media == {"src": None, "currentSrc": "", "frameSource": ""}

    install_base_media_mutation_probe(page)
    response_state["completed"] = True
    page.locator("#resultCard").wait_for(state="visible", timeout=10_000)
    page.wait_for_function(
        """() => {
          const video = document.querySelector('#cutPreviewVideo');
          return video?.readyState >= 1 && Number.isFinite(video.duration)
            && video.duration > 0;
        }"""
    )
    assert base_media_mutations(page) == {"srcWrites": 1, "loadCalls": 1}

    page.locator("#cutPreviewPlay").click()
    page.wait_for_function(
        """() => {
          const video = document.querySelector('#cutPreviewVideo');
          return video && !video.paused && video.currentTime > 0.02;
        }"""
    )

    page.evaluate("job => window.EditorSuite.update(job)", completed_job)
    assert base_media_mutations(page) == {"srcWrites": 1, "loadCalls": 1}


def install_template_catalog_revision_probe(page) -> None:
    page.add_init_script(
        """(() => {
          const originalFetch = window.fetch.bind(window);
          window.fetch = async (...args) => {
            const response = await originalFetch(...args);
            const requestUrl = new URL(
              typeof args[0] === 'string' ? args[0] : args[0].url,
              window.location.origin,
            );
            if (requestUrl.pathname !== '/api/art-templates') return response;
            const payload = await response.clone().json();
            const query = new URLSearchParams(window.location.search);
            const expectedJobId = query.get('job') || '';
            const expectedTool = query.get('tool') || 'cut';
            let snapshot = null;
            // The template catalog may resolve before the async project
            // hydration/tool handoff. Capture the baseline only after both so
            // navigation revisions are not mistaken for template mutations.
            while (true) {
              snapshot = window.EditorSuite?.projectSnapshot?.() || null;
              if (
                snapshot &&
                (!expectedJobId || snapshot.jobId === expectedJobId) &&
                snapshot.ui?.activeTool === expectedTool
              ) break;
              await new Promise(resolve => window.setTimeout(resolve, 0));
            }
            window.__templateCatalogBaseline = {
              revision: snapshot.revision,
              timingRevision: snapshot.timingRevision,
              selection: snapshot.project.timeline.selection,
              ranges: snapshot.project.art.overlays.map(item => ({
                id: item.id,
                start: item.start,
                end: item.end,
                sourceStart: item.sourceStart ?? null,
                sourceEnd: item.sourceEnd ?? null,
              })),
            };
            return new Response(JSON.stringify(payload), {
              status: response.status,
              statusText: response.statusText,
              headers: response.headers,
            });
          };
        })()"""
    )


def test_cut_draft_survives_refresh(
    browser_session,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
    saved_draft = delete_first_text_segment(page)

    assert saved_draft["revision"] >= 1
    assert saved_draft["textRanges"] == [
        {
            "key": "0.050-0.300",
            "start": 0.05,
            "end": 0.3,
            "text": "删除片段",
            "originalStart": 0.05,
            "originalEnd": 0.3,
            "adjacentSilenceBefore": 0.0,
            "adjacentSilenceAfter": 0.0,
        }
    ]

    page.reload()
    page.locator("#resultCard").wait_for(state="visible")
    restored = page.get_by_role("button", name="恢复已删除文字：删除片段")
    restored.wait_for(state="visible")
    restored_item = restored.locator("xpath=ancestor::li[1]")
    assert restored_item.get_attribute("data-display-start") == "0.05"
    assert restored_item.get_attribute("data-display-end") == "0.3"

    refreshed_draft = page.evaluate(
        """async () => (await fetch(
          `/api/transcriptions/${new URLSearchParams(location.search).get("job")}/cut-draft`
        )).json()"""
    )["cutDraft"]
    assert refreshed_draft == saved_draft


def test_timeline_split_exact_clip_delete_restore_history_and_mobile_layout(
    browser_session,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
    page.wait_for_function(
        """() => {
          const video = document.querySelector('#cutPreviewVideo');
          return video?.readyState >= 1 && Number(video.duration) > 0;
        }"""
    )
    page.wait_for_timeout(900)
    install_base_media_mutation_probe(page)
    page.evaluate(
        """() => {
          const originalCreateElement = Document.prototype.createElement;
          window.__splitVideoCreations = 0;
          Document.prototype.createElement = function createElementWithSplitProbe(
            name,
            options,
          ) {
            const element = originalCreateElement.call(this, name, options);
            if (String(name).toLowerCase() === 'video') {
              window.__splitVideoCreations += 1;
            }
            return element;
          };
        }"""
    )
    page.locator("#cutPreviewVideo").evaluate(
        """video => {
          video.pause();
          video.currentTime = 0.5;
          video.dispatchEvent(new Event('seeking'));
          video.dispatchEvent(new Event('timeupdate'));
        }"""
    )
    split_button = page.get_by_role(
        "button",
        name="在当前播放头位置分割视频",
    )
    page.wait_for_function(
        """() => !document.querySelector('#cutTimelineSplitButton')?.disabled"""
    )
    page.evaluate(
        """() => {
          window.__splitStoreActions = [];
          window.__splitStoreUnsubscribe = window.EditorSuite.subscribeProject(
            (_next, _previous, action) => window.__splitStoreActions.push(action.type),
          );
        }"""
    )
    before = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const video = document.querySelector('#cutPreviewVideo');
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            duration: Number(document.querySelector('#cutPreviewSeek').max),
            currentTime: video.currentTime,
            source: video.currentSrc,
          };
        }"""
    )

    split_button.click()
    page.locator("#cutFrameTimelineClips .cut-timeline-split-clip").nth(1).wait_for()
    page.locator("#cutDraftSaveStatus").filter(
        has_text="剪辑草稿已保存"
    ).wait_for()
    after_split = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const video = document.querySelector('#cutPreviewVideo');
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            duration: Number(document.querySelector('#cutPreviewSeek').max),
            currentTime: video.currentTime,
            source: video.currentSrc,
            splitPoints: snapshot.project.cut.splitPoints,
            actions: window.__splitStoreActions,
          };
        }"""
    )
    assert after_split["actions"].count("cutStructureChanged") == 1
    assert after_split["revision"] == before["revision"] + 1, after_split
    assert after_split["timingRevision"] == before["timingRevision"]
    assert after_split["duration"] == pytest.approx(before["duration"])
    assert after_split["currentTime"] == pytest.approx(before["currentTime"], abs=0.06)
    assert after_split["source"] == before["source"]
    assert len(after_split["splitPoints"]) == 1
    assert after_split["splitPoints"][0]["sourceTime"] == pytest.approx(0.5)
    assert base_media_mutations(page) == {"srcWrites": 0, "loadCalls": 0}

    page.locator("#cutPreviewVideo").evaluate(
        """video => {
          video.currentTime = 0.75;
          video.dispatchEvent(new Event('seeking'));
          video.dispatchEvent(new Event('timeupdate'));
        }"""
    )
    page.wait_for_function(
        """() => !document.querySelector('#cutTimelineSplitButton')?.disabled"""
    )
    split_button.click()
    page.wait_for_function(
        """() => document.querySelectorAll(
          '#cutFrameTimelineClips .cut-timeline-split-clip'
        ).length === 3"""
    )
    page.locator("#cutDraftSaveStatus").filter(
        has_text="剪辑草稿已保存"
    ).wait_for()
    before_split_history = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
          };
        }"""
    )
    page.keyboard.press("Control+z")
    page.wait_for_function(
        """() => document.querySelectorAll(
          '#cutFrameTimelineClips .cut-timeline-split-clip'
        ).length === 2"""
    )
    after_split_undo = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            splitPointCount: snapshot.project.cut.splitPoints.length,
          };
        }"""
    )
    assert after_split_undo == {
        "revision": before_split_history["revision"] + 1,
        "timingRevision": before_split_history["timingRevision"],
        "splitPointCount": 1,
    }
    page.keyboard.press("Control+y")
    page.wait_for_function(
        """() => document.querySelectorAll(
          '#cutFrameTimelineClips .cut-timeline-split-clip'
        ).length === 3"""
    )
    after_split_redo = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            splitPointCount: snapshot.project.cut.splitPoints.length,
          };
        }"""
    )
    assert after_split_redo == {
        "revision": after_split_undo["revision"] + 1,
        "timingRevision": before_split_history["timingRevision"],
        "splitPointCount": 2,
    }
    page.locator("#cutDraftSaveStatus").filter(
        has_text="剪辑草稿已保存"
    ).wait_for()
    page.wait_for_function(
        """async () => {
          const job = new URLSearchParams(location.search).get('job');
          const payload = await (await fetch(
            `/api/transcriptions/${job}/cut-draft`, { cache: 'no-store' }
          )).json();
          return payload.cutDraft?.splitPoints?.length === 2;
        }"""
    )
    page.locator("#cutPreviewVideo").evaluate(
        """video => {
          video.currentTime = 0.5;
          video.dispatchEvent(new Event('seeking'));
          video.dispatchEvent(new Event('timeupdate'));
        }"""
    )
    page.wait_for_function(
        """() => document.querySelector('#cutTimelineSplitButton')?.disabled"""
    )
    assert base_media_mutations(page) == {"srcWrites": 0, "loadCalls": 0}
    assert page.evaluate("window.__splitVideoCreations") == 0

    page.set_viewport_size({"width": 375, "height": 812})
    mobile_layout = page.evaluate(
        """() => {
          const button = document.querySelector('#cutTimelineSplitButton')
            .getBoundingClientRect();
          const actions = document.querySelector('.cut-frame-timeline-actions')
            .getBoundingClientRect();
          const track = document.querySelector('#cutFrameTimelineTrack')
            .getBoundingClientRect();
          return {
            buttonWidth: button.width,
            buttonHeight: button.height,
            buttonRight: button.right,
            actionsBottom: actions.bottom,
            trackTop: track.top,
            viewportWidth: innerWidth,
            documentWidth: document.documentElement.scrollWidth,
          };
        }"""
    )
    assert mobile_layout["buttonWidth"] >= 44
    assert mobile_layout["buttonHeight"] >= 44
    assert mobile_layout["buttonRight"] <= mobile_layout["viewportWidth"]
    assert mobile_layout["trackTop"] >= mobile_layout["actionsBottom"]
    assert mobile_layout["documentWidth"] <= mobile_layout["viewportWidth"]

    first_clip = page.locator("#cutFrameTimelineClips .cut-timeline-split-clip").first
    first_clip.focus()
    first_clip.press("Delete")
    page.locator("#appDialogConfirm").filter(has_text="删除片段").click()
    page.wait_for_function(
        """() => document.querySelectorAll(
          '#cutFrameTimelineClips .cut-timeline-split-clip'
        ).length === 2"""
    )
    assert page.locator(
        "#cutFrameTimelineClips .cut-timeline-deleted-marker"
    ).count() == 0
    assert page.locator(
        '#cutFrameTimelineClips [data-deleted="true"]'
    ).count() == 0
    page.locator("#cutDraftSaveStatus").filter(
        has_text="剪辑草稿已保存"
    ).wait_for()
    deleted_draft = page.evaluate(
        """async () => (await fetch(
          `/api/transcriptions/${new URLSearchParams(location.search).get('job')}/cut-draft`
        )).json()"""
    )["cutDraft"]
    assert deleted_draft["timelineRanges"] == [
        {
            "key": "split-delete-1",
            "start": 0.0,
            "end": 0.5,
            "originalStart": 0.0,
            "originalEnd": 0.5,
            "boundaryMode": "split_exact",
            "splitClipKey": (
                "split-clip:source-start:"
                + deleted_draft["splitPoints"][0]["key"]
            ),
        }
    ]
    assert {
        item["fallbackReason"]
        for item in deleted_draft["boundaryDiagnostics"]
    } == {"split_boundary_exact"}

    page.keyboard.press("Control+z")
    page.wait_for_function(
        """() => document.querySelectorAll(
          '#cutFrameTimelineClips .cut-timeline-split-clip'
        ).length === 3"""
    )
    page.keyboard.press("Control+y")
    page.wait_for_function(
        """() => document.querySelectorAll(
          '#cutFrameTimelineClips .cut-timeline-split-clip'
        ).length === 2"""
    )
    assert page.locator(
        "#cutFrameTimelineClips .cut-timeline-deleted-marker"
    ).count() == 0
    page.keyboard.press("Control+z")
    page.wait_for_function(
        """() => document.querySelectorAll(
          '#cutFrameTimelineClips .cut-timeline-split-clip'
        ).length === 3"""
    )
    page.wait_for_function(
        """async () => {
          const job = new URLSearchParams(location.search).get('job');
          const payload = await (await fetch(
            `/api/transcriptions/${job}/cut-draft`, { cache: 'no-store' }
          )).json();
          return payload.cutDraft?.timelineRanges?.length === 0;
        }"""
    )

    page.reload()
    page.locator("#resultCard").wait_for(state="visible")
    page.locator("#cutFrameTimelineClips .cut-timeline-split-clip").nth(1).wait_for()
    install_base_media_mutation_probe(page)
    page.evaluate(
        """() => {
          const originalCreateElement = Document.prototype.createElement;
          window.__splitVideoCreations = 0;
          Document.prototype.createElement = function createElementWithSplitProbe(
            name,
            options,
          ) {
            const element = originalCreateElement.call(this, name, options);
            if (String(name).toLowerCase() === 'video') {
              window.__splitVideoCreations += 1;
            }
            return element;
          };
        }"""
    )
    assert page.locator("#cutFrameTimelineClips .cut-timeline-split-clip").count() == 3
    assert page.locator("#cutFrameTimelineClips .cut-timeline-deleted-marker").count() == 0
    page.wait_for_function(
        """async () => {
          const job = new URLSearchParams(location.search).get('job');
          const payload = await (await fetch(
            `/api/transcriptions/${job}/cut-draft`, { cache: 'no-store' }
          )).json();
          return payload.cutDraft?.timelineRanges?.length === 0;
        }"""
    )

    reloaded_first_clip = page.locator(
        "#cutFrameTimelineClips .cut-timeline-split-clip"
    ).first
    reloaded_first_clip.click()
    selected_focus = page.evaluate(
        """() => ({
          selected: document.querySelector(
            '#cutFrameTimelineClips .cut-timeline-split-clip.is-selected'
          )?.dataset.splitClipKey || '',
          focused: document.activeElement?.dataset?.splitClipKey || '',
          storeClipId:
            window.EditorSuite.projectSnapshot().project.timeline.selection?.clipId || '',
        })"""
    )
    assert selected_focus["selected"]
    assert selected_focus["focused"] == selected_focus["selected"]
    assert selected_focus["storeClipId"] == f"cut:split:{selected_focus['selected']}"

    # Splitting must not take over the existing free-drag delete workflow.
    # Start the gesture on the ruler (outside the clip buttons) and prove that
    # the ordinary pending range remains available and independently cancellable.
    page.evaluate(
        """() => {
          const track = document.querySelector('#cutFrameTimelineTrack');
          const ruler = document.querySelector('#cutFrameTimelineRuler');
          const bounds = track.getBoundingClientRect();
          const startX = bounds.left + bounds.width * 0.78;
          const endX = bounds.left + bounds.width * 0.92;
          ruler.dispatchEvent(new PointerEvent('pointerdown', {
            bubbles: true, button: 0, buttons: 1, clientX: startX,
          }));
          window.dispatchEvent(new PointerEvent('pointermove', {
            bubbles: true, button: 0, buttons: 1, clientX: endX,
          }));
          window.dispatchEvent(new PointerEvent('pointerup', {
            bubbles: true, button: 0, clientX: endX,
          }));
        }"""
    )
    pending_range = page.locator(
        "#cutFrameTimelineRanges .cut-timeline-range-body"
    )
    pending_range.wait_for()
    pending_range.evaluate("body => body.focus()")
    assert "待确认删除区间" in pending_range.get_attribute("aria-label")
    page.locator(
        "#cutFrameTimelineRanges .cut-timeline-range-cancel"
    ).dispatch_event("click")
    page.wait_for_function(
        """() => document.querySelectorAll(
          '#cutFrameTimelineRanges .cut-timeline-delete-range'
        ).length === 0"""
    )

    # Deleting every clip keeps the internal split structure and history, but
    # the timeline must not render a restore marker, placeholder, or focus target.
    for expected_remaining in range(2, -1, -1):
        clip = page.locator(
            "#cutFrameTimelineClips .cut-timeline-split-clip"
        ).first
        clip.focus()
        clip.press("Delete")
        page.locator("#appDialogConfirm").filter(has_text="删除片段").click()
        page.wait_for_function(
            """expected => document.querySelectorAll(
              '#cutFrameTimelineClips .cut-timeline-split-clip'
            ).length === expected""",
            arg=expected_remaining,
        )
        assert page.locator(
            "#cutFrameTimelineClips .cut-timeline-deleted-marker"
        ).count() == 0

    all_deleted = page.evaluate(
        """() => {
          const timeline = document.querySelector('#cutFrameTimeline');
          const clipLayer = document.querySelector('#cutFrameTimelineClips');
          return {
            timelineHidden: timeline.hidden,
            renderedChildren: clipLayer.children.length,
            focusTargets: clipLayer.querySelectorAll(
              'button, [tabindex], [data-deleted="true"]'
            ).length,
            storeMarkers: window.EditorSuite.projectSnapshot().project.timeline.tracks
              .find(item => item.id === 'cut:split-structure')?.clips
              .filter(item => item.payload.deleted) || [],
          };
        }"""
    )
    assert all_deleted["timelineHidden"] is False
    assert all_deleted["renderedChildren"] == 0
    assert all_deleted["focusTargets"] == 0
    assert len(all_deleted["storeMarkers"]) == 3
    assert all(item["payload"]["markerEditedTime"] == 0 for item in all_deleted["storeMarkers"])

    page.keyboard.press("Control+z")
    page.wait_for_function(
        """() => document.querySelectorAll(
          '#cutFrameTimelineClips .cut-timeline-split-clip'
        ).length === 1"""
    )
    restored_history = page.evaluate(
        """() => ({
          timelineRanges:
            window.EditorSuite.projectSnapshot().project.cut.ranges.length,
          storeDeleted:
            window.EditorSuite.projectSnapshot().project.timeline.tracks
              .find(item => item.id === 'cut:split-structure')?.clips
              .filter(item => item.payload.deleted).length,
          markerCount: document.querySelectorAll(
            '#cutFrameTimelineClips .cut-timeline-deleted-marker'
          ).length,
        })"""
    )
    assert restored_history == {
        "timelineRanges": 1,
        "storeDeleted": 2,
        "markerCount": 0,
    }
    page.keyboard.press("Control+y")
    page.wait_for_function(
        """() => document.querySelectorAll(
          '#cutFrameTimelineClips .cut-timeline-split-clip'
        ).length === 0"""
    )
    assert page.locator("#cutFrameTimelineClips").locator("button").count() == 0
    assert page.locator("iframe").count() == 0
    assert base_media_mutations(page) == {"srcWrites": 0, "loadCalls": 0}
    assert page.evaluate("window.__splitVideoCreations") == 0


def test_transcript_rows_use_half_scale_geometry_without_horizontal_overflow(
    browser_session,
    seeded_editor_job,
):
    long_text = "这是一段用于验证窄屏换行且不产生横向溢出的较长中文文案。" * 8
    with app_module.JOBS_LOCK:
        result = app_module.JOBS[seeded_editor_job.job_id]["result"]
        for field in ("segments", "editableSegments"):
            segment = result[field][1]
            segment["text"] = long_text
            segment["words"] = [
                {
                    "text": long_text,
                    "start": segment["start"],
                    "end": segment["end"],
                }
            ]
        result["text"] = f'删除片段\n{long_text}'
        result["noSpeechSuggestions"] = [
            {
                "id": "browser-middle-gap",
                "start": 0.3,
                "end": 0.35,
                "duration": 0.05,
                "originalGapDuration": 0.05,
                "kind": "middle",
                "protected": False,
                "deletable": True,
                "audioState": "quiet",
                "quietRatio": 1.0,
                "confidence": 0.98,
                "reason": "浏览器布局回归空白。",
            }
        ]
    app_module.persist_job_snapshot(seeded_editor_job.job_id, raise_on_error=True)

    page = browser_session.page
    page.set_viewport_size({"width": 1280, "height": 900})
    open_editor(browser_session, seeded_editor_job)
    page.locator(
        '.segment-item[data-segment-index="0"] .segment-toggle'
    ).click()
    page.locator(
        '.segment-item.is-delete-fragment[data-segment-index="0"]'
    ).wait_for()

    def transcript_geometry():
        return page.evaluate(
            """() => {
              const deleted = document.querySelector(
                '.segment-item.is-delete-fragment[data-segment-index="0"]'
              );
              const normal = document.querySelector(
                '.segment-item[data-segment-index="1"]'
              );
              const noSpeech = document.querySelector(
                '.segment-item[data-no-speech-id]'
              );
              const toggle = deleted.querySelector('.segment-toggle');
              const play = deleted.querySelector('.segment-play-button');
              const time = deleted.querySelector('.segment-time');
              const text = deleted.querySelector('.segment-text');
              const textRun = deleted.querySelector('.segment-text-run');
              const badge = deleted.querySelector('.segment-current-badge');
              const noSpeechButton = noSpeech.querySelector(
                '.segment-no-speech-button'
              );
              const noSpeechTitle = noSpeechButton.querySelector('strong');
              const noSpeechMeta = noSpeechButton.querySelector(
                '.segment-no-speech-meta'
              );
              const list = document.querySelector('#segmentList');
              const summary = document.querySelector('.cut-summary strong');
              const timelineButton = document.querySelector(
                '#cutTimelineSplitButton'
              );
              const style = element => getComputedStyle(element);
              const bounds = element => element.getBoundingClientRect();
              const allItems = [...list.querySelectorAll('.segment-item')];
              return {
                row: bounds(deleted).height,
                minHeight: style(deleted).minHeight,
                paddingTop: style(deleted).paddingTop,
                paddingRight: style(deleted).paddingRight,
                columns: style(deleted).gridTemplateColumns,
                columnGap: style(deleted).columnGap,
                toggle: [bounds(toggle).width, bounds(toggle).height],
                circle: {
                  width: getComputedStyle(toggle, '::before').width,
                  height: getComputedStyle(toggle, '::before').height,
                  border: getComputedStyle(toggle, '::before').borderTopWidth,
                  font: getComputedStyle(toggle, '::before').fontSize,
                },
                play: [bounds(play).width, bounds(play).height],
                playIcon: style(play.querySelector('iconify-icon')).fontSize,
                timeFont: style(time).fontSize,
                textFont: style(text).fontSize,
                textLineHeight: style(text).lineHeight,
                textMinHeight: style(text).minHeight,
                textRunMinHeight: style(textRun).minHeight,
                textRunPaddingTop: style(textRun).paddingTop,
                textRunGap: style(textRun).gap,
                badgeFont: style(badge).fontSize,
                noSpeechMinHeight: style(noSpeechButton).minHeight,
                noSpeechIcon: style(
                  noSpeechButton.querySelector('iconify-icon')
                ).fontSize,
                noSpeechTitleFont: style(noSpeechTitle).fontSize,
                noSpeechMetaFont: style(noSpeechMeta).fontSize,
                normalHeight: bounds(normal).height,
                noSpeechHeight: bounds(noSpeech).height,
                fullWidth: allItems.every(
                  item => Math.abs(bounds(item).width - bounds(list).width) <= 1
                ),
                itemOverflow: allItems.some(
                  item => item.scrollWidth > item.clientWidth + 1
                ),
                rowClipping: allItems.some(
                  item => item.scrollHeight > item.clientHeight + 1
                ),
                textOverflow:
                  normal.querySelector('.segment-text').scrollWidth
                    > normal.querySelector('.segment-text').clientWidth + 1,
                summaryFont: style(summary).fontSize,
                timelineButton: [
                  bounds(timelineButton).width,
                  bounds(timelineButton).height,
                ],
                documentOverflow:
                  document.documentElement.scrollWidth
                    - document.documentElement.clientWidth,
              };
            }"""
        )

    desktop = transcript_geometry()
    assert desktop["row"] == pytest.approx(32, abs=0.1)
    assert desktop["minHeight"] == "32px"
    assert desktop["paddingTop"] == "4px"
    assert desktop["paddingRight"] == "3px"
    assert desktop["columns"].startswith("22px 26px ")
    assert desktop["columns"].endswith(" 22px")
    assert desktop["columnGap"] == "4px"
    assert desktop["toggle"] == [22, 22]
    assert desktop["circle"] == {
        "width": "12px",
        "height": "12px",
        "border": "0px",
        "font": "10px",
    }
    assert desktop["play"] == [22, 22]
    assert desktop["playIcon"] == "11px"
    assert desktop["timeFont"] == "9px"
    assert desktop["textFont"] == "10px"
    assert desktop["textLineHeight"] == "13.5px"
    assert desktop["textMinHeight"] == "22px"
    assert desktop["textRunMinHeight"] == "22px"
    assert desktop["textRunPaddingTop"] == "2px"
    assert desktop["textRunGap"] == "2.5px"
    assert desktop["badgeFont"] == "7px"
    assert desktop["noSpeechMinHeight"] == "22px"
    assert desktop["noSpeechIcon"] == "10px"
    assert desktop["noSpeechTitleFont"] == "9px"
    assert desktop["noSpeechMetaFont"] == "8px"
    assert desktop["normalHeight"] > desktop["row"]
    assert desktop["noSpeechHeight"] >= desktop["row"]
    assert desktop["fullWidth"] is True
    assert desktop["itemOverflow"] is False
    assert desktop["rowClipping"] is False
    assert desktop["textOverflow"] is False
    assert desktop["summaryFont"] == "15px"
    assert desktop["timelineButton"][0] >= 44
    assert desktop["timelineButton"][1] >= 44
    assert desktop["documentOverflow"] <= 1

    # Playback-follow must measure the compact row that is actually rendered.
    # It may not retain the legacy 64px placeholder/layer geometry.
    follow_geometry = page.evaluate(
        """() => {
          document.querySelector('#transcriptNowPlayingLayer')
            .dispatchEvent(new WheelEvent('wheel'));
          const item = document.querySelector(
            '#segmentList .segment-item[data-segment-index="1"]'
          );
          const wasActive = item.classList.contains('is-playback-active');
          item.classList.add('is-playback-active');
          const initialHeight = item.getBoundingClientRect().height;
          const controller = window.TranscriptFollowScroll.createController({
            layer: document.querySelector('#transcriptNowPlayingLayer'),
          });
          const followed = controller.follow(item, 'compact-row-review');
          const placeholder = document.querySelector(
            '#segmentList .segment-follow-placeholder'
          );
          const layer = document.querySelector('#transcriptNowPlayingLayer');
          const active = layer.querySelector('.segment-item.is-playback-active');
          const result = {
            activeHeight: active.getBoundingClientRect().height,
            followed,
            initialHeight,
            layerHeight: layer.getBoundingClientRect().height,
            placeholderHeight: placeholder.getBoundingClientRect().height,
            placeholderButtons: placeholder.querySelectorAll('button').length,
            activeButtons: active.querySelectorAll('button').length,
          };
          controller.reset();
          if (!wasActive) item.classList.remove('is-playback-active');
          return result;
        }"""
    )
    assert follow_geometry["followed"] is True
    assert follow_geometry["initialHeight"] == pytest.approx(
        desktop["normalHeight"], abs=0.1
    )
    assert follow_geometry["activeHeight"] == pytest.approx(
        desktop["normalHeight"], abs=0.1
    )
    assert follow_geometry["layerHeight"] == pytest.approx(
        desktop["normalHeight"], abs=0.1
    )
    assert follow_geometry["placeholderHeight"] == pytest.approx(
        desktop["normalHeight"], abs=0.1
    )
    assert follow_geometry["placeholderButtons"] == 0
    assert follow_geometry["activeButtons"] > 0

    page.set_viewport_size({"width": 375, "height": 812})
    mobile = transcript_geometry()
    assert mobile["toggle"] == [22, 22]
    assert mobile["play"] == [22, 22]
    assert mobile["timeFont"] == "9px"
    assert mobile["textFont"] == "10px"
    assert mobile["columns"].startswith("22px ")
    assert mobile["columns"].endswith(" 22px")
    assert mobile["normalHeight"] >= desktop["normalHeight"]
    assert mobile["fullWidth"] is True
    assert mobile["itemOverflow"] is False
    assert mobile["rowClipping"] is False
    assert mobile["textOverflow"] is False
    assert mobile["summaryFont"] == "15px"
    assert mobile["timelineButton"][0] >= 44
    assert mobile["timelineButton"][1] >= 44
    assert mobile["documentOverflow"] <= 1

    page.locator(
        '#segmentList .segment-item.is-delete-fragment[data-segment-index="0"] '
        '.segment-restore-button'
    ).click()
    restored_item = page.locator(
        '#segmentList .segment-item[data-segment-index="0"]'
        ':not(.is-delete-fragment)'
    )
    restored_item.wait_for(state="visible")
    restored_geometry = restored_item.evaluate(
        """item => {
          const bounds = item.getBoundingClientRect();
          const text = item.querySelector('.segment-text');
          return {
            height: bounds.height,
            textFont: getComputedStyle(text).fontSize,
            clipping: item.scrollHeight > item.clientHeight + 1,
            overflow: item.scrollWidth > item.clientWidth + 1,
          };
        }"""
    )
    assert restored_geometry["height"] >= 32
    assert restored_geometry["textFont"] == "10px"
    assert restored_geometry["clipping"] is False
    assert restored_geometry["overflow"] is False

    page.locator(
        '#segmentList .segment-item.is-no-speech-fragment.is-delete-fragment '
        '.segment-toggle'
    ).click()
    restored_no_speech = page.locator(
        '#segmentList .segment-item.is-no-speech-fragment.is-restored-no-speech'
    )
    restored_no_speech.wait_for(state="visible")
    restored_no_speech_geometry = restored_no_speech.evaluate(
        """item => {
          const button = item.querySelector('.segment-no-speech-button');
          return {
            titleFont: getComputedStyle(button.querySelector('strong')).fontSize,
            metaFont: getComputedStyle(
              button.querySelector('.segment-no-speech-meta')
            ).fontSize,
            iconFont: getComputedStyle(
              button.querySelector('iconify-icon')
            ).fontSize,
            clipping: item.scrollHeight > item.clientHeight + 1,
            overflow: item.scrollWidth > item.clientWidth + 1,
          };
        }"""
    )
    assert restored_no_speech_geometry == {
        "titleFont": "9px",
        "metaFont": "8px",
        "iconFont": "10px",
        "clipping": False,
        "overflow": False,
    }


def test_tool_switch_keeps_selection_preview_and_playback_position(
    browser_session,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
    original_title = page.title()
    page.locator("#cutPreviewVideo").evaluate(
        """video => {
          video.pause();
          video.currentTime = 0.5;
          video.dispatchEvent(new Event("seeking"));
          video.dispatchEvent(new Event("timeupdate"));
        }"""
    )
    install_base_media_mutation_probe(page)

    page.locator('[data-editor-tool="art"]').click()
    art_panel = page.locator("#editorArtPanelRoot")
    art_panel.wait_for(state="visible")
    assert art_panel.locator("[data-art-tab]").all_inner_texts() == [
        "选择艺术字",
        "艺术字设置",
        "AI 推荐",
    ]
    assert art_panel.locator('[data-art-tab="settings"]').get_attribute(
        "aria-selected"
    ) == "true"
    assert art_panel.locator('[data-art-panel="selection"]').is_hidden()
    assert art_panel.locator('[data-art-tab="transcript"]').count() == 0
    assert art_panel.locator(
        '[data-art-panel="selection"] [data-art-transcript-section]'
    ).count() == 1
    assert art_panel.locator(
        '[data-art-panel="settings"] [data-art-transcript-section]'
    ).count() == 0
    art_panel.locator('[data-art-tab="selection"]').click()
    transcript_action = art_panel.locator("[data-art-transcript-section]")
    assert transcript_action.get_by_role(
        "button", name="一键添加视频文案", exact=True
    ).count() == 1
    assert transcript_action.locator("textarea").count() == 0
    assert transcript_action.locator("[data-art-transcript-save]").count() == 0
    assert transcript_action.locator("[data-art-transcript-list]").count() == 0
    assert transcript_action.locator("[data-art-add-selected]").count() == 0
    for tab_name in ("selection", "settings", "ai"):
        tab = art_panel.locator(f'[data-art-tab="{tab_name}"]')
        panel = art_panel.locator(f'[data-art-panel="{tab_name}"]')
        assert tab.get_attribute("aria-controls") == panel.get_attribute("id")
        assert panel.get_attribute("aria-labelledby") == tab.get_attribute("id")
    selection_tab = art_panel.locator('[data-art-tab="selection"]')
    settings_tab = art_panel.locator('[data-art-tab="settings"]')
    ai_tab = art_panel.locator('[data-art-tab="ai"]')
    selection_tab.focus()
    selection_tab.press("ArrowRight")
    assert settings_tab.get_attribute("aria-selected") == "true"
    settings_tab.press("ArrowRight")
    assert ai_tab.get_attribute("aria-selected") == "true"
    assert art_panel.locator('[data-art-panel="settings"]').is_hidden()
    assert art_panel.locator('[data-art-panel="ai"]').is_visible()
    ai_tab.press("End")
    assert ai_tab.get_attribute("aria-selected") == "true"
    ai_tab.press("Home")
    assert selection_tab.get_attribute("aria-selected") == "true"
    selection_tab.press("ArrowLeft")
    assert ai_tab.get_attribute("aria-selected") == "true"
    ai_tab.press("Home")
    assert art_panel.locator('[data-art-panel="ai"]').is_hidden()
    assert art_panel.locator('[data-art-panel="ai"] :focus').count() == 0
    tab_tops = art_panel.locator("[data-art-tab]").evaluate_all(
        "tabs => tabs.map(tab => Math.round(tab.getBoundingClientRect().top))"
    )
    assert len(set(tab_tops)) == 1
    art_panel.locator(".editor-art-tool").evaluate(
        "panel => { panel.scrollTop = panel.scrollHeight; }"
    )
    art_panel.locator('[data-art-tab="ai"]').click()
    assert art_panel.locator(".editor-art-tool").evaluate(
        "panel => panel.scrollTop"
    ) == 0
    selection_tab.click()
    assert page.locator('iframe[title="艺术字设置"]').count() == 0
    selected_art = art_panel.locator(
        "[data-art-list] .overlay-list-item.is-selected"
    )
    selected_art.wait_for()
    assert selected_art.count() == 1
    assert "保留内容" in selected_art.inner_text()
    assert art_panel.evaluate("panel => panel.inert") is False
    art_panel.locator("[data-art-add-text]").focus()
    assert page.evaluate(
        "() => document.querySelector('#editorArtPanelRoot').contains(document.activeElement)"
    ) is True
    assert page.locator('[data-editor-suite-panel="art"]').get_attribute(
        "aria-hidden"
    ) == "false"
    page.locator("#editorSuitePreviewOverlay .is-art").wait_for(state="visible")

    page.locator('[data-editor-tool="pip"]').click()
    pip_panel = page.locator("#editorPipPanelRoot")
    pip_panel.wait_for(state="visible")
    assert page.locator('iframe[title="画中画设置"]').count() == 0
    preview_button = pip_panel.get_by_role(
        "button",
        name="选择画中画素材：保留内容",
    )
    preview_button.click()
    selected_card = pip_panel.locator(
        f'.pip-generated-card[data-picture-id="{seeded_editor_job.pip_asset_id}"]'
    )
    assert "is-selected" in (selected_card.get_attribute("class") or "")
    assert page.locator('[data-editor-suite-panel="pip"]').get_attribute(
        "aria-hidden"
    ) == "false"
    page.locator("#editorSuitePreviewOverlay .is-pip").wait_for(state="visible")
    assert art_panel.evaluate("panel => panel.inert") is True
    assert pip_panel.evaluate("panel => panel.inert") is False
    assert page.evaluate(
        "() => document.querySelector('#editorArtPanelRoot').contains(document.activeElement)"
    ) is False
    selected_time = page.locator("#cutPreviewVideo").evaluate(
        "video => video.currentTime"
    )

    page.locator('[data-editor-tool="cut"]').click()
    assert page.locator(".text-editor-panel-stack").is_visible()
    wait_for_preview_time(page, selected_time)
    page.locator('[data-editor-tool="art"]').click()
    wait_for_preview_time(page, selected_time)
    assert art_panel.evaluate("panel => panel.inert") is False
    assert pip_panel.evaluate("panel => panel.inert") is True
    page.locator('[data-editor-tool="pip"]').click()
    wait_for_preview_time(page, selected_time)

    assert page.title() == original_title
    assert selected_art.count() == 0
    assert "is-selected" in (selected_card.get_attribute("class") or "")
    current_time = page.locator("#cutPreviewVideo").evaluate(
        "video => video.currentTime"
    )
    assert current_time == pytest.approx(selected_time, abs=0.06)
    assert page.locator("#editorSuitePreviewOverlay .is-art").count() == 1
    assert page.locator("#editorSuitePreviewOverlay .is-pip").count() == 1
    assert "tool=pip" in page.url
    assert base_media_mutations(page) == {"srcWrites": 0, "loadCalls": 0}


def test_empty_art_settings_survives_unrelated_project_updates(
    browser_session,
    seeded_editor_job_without_art,
):
    page = open_editor(browser_session, seeded_editor_job_without_art)
    page.locator('[data-editor-tool="art"]').click()
    panel = page.locator("#editorArtPanelRoot")
    panel.wait_for(state="visible")

    selection_tab = panel.locator('[data-art-tab="selection"]')
    settings_tab = panel.locator('[data-art-tab="settings"]')
    assert selection_tab.get_attribute("aria-selected") == "true"
    settings_tab.click()
    before_revision = page.evaluate("window.EditorSuite.projectSnapshot().revision")
    page.evaluate(
        """() => {
          const cut = window.EditorSuite.projectSnapshot().project.cut;
          window.EditorSuite.setCutDraft({
            ...cut,
            cutDraftRevision: Number(cut.cutDraftRevision || 0) + 1,
          });
        }"""
    )
    page.wait_for_function(
        "revision => window.EditorSuite.projectSnapshot().revision > revision",
        arg=before_revision,
    )

    assert settings_tab.get_attribute("aria-selected") == "true"
    assert panel.locator('[data-art-panel="settings"]').is_visible()
    assert panel.locator("[data-art-selection-empty]").is_visible()


def test_portrait_preview_canvas_matches_video_fit_and_pointer_geometry(
    browser_session,
    seeded_portrait_editor_job,
):
    page = open_editor(browser_session, seeded_portrait_editor_job)
    page.locator("#cutPreviewVideo").evaluate(
        """video => {
          video.pause();
          video.currentTime = 0.5;
          video.dispatchEvent(new Event('seeking'));
          video.dispatchEvent(new Event('timeupdate'));
        }"""
    )
    page.locator('[data-editor-tool="art"]').click()
    art = page.locator(
        "#editorSuitePreviewOverlay .preview-overlay:not(.is-ai-draft)"
    ).first
    art.wait_for(state="visible")
    stage = page.locator("#cutVideoStage")
    stage.evaluate(
        """node => {
          node.style.setProperty('width', '600px', 'important');
          node.style.setProperty('height', '400px', 'important');
          node.style.setProperty('max-width', 'none', 'important');
          node.style.setProperty('max-height', 'none', 'important');
          node.style.setProperty('aspect-ratio', 'auto', 'important');
        }"""
    )
    page.evaluate("window.dispatchEvent(new Event('resize'))")
    page.locator(".editor-suite-preview-canvas").evaluate(
        """node => new Promise(resolve => requestAnimationFrame(
          () => requestAnimationFrame(() => resolve(node.dataset.previewFit))
        ))"""
    )

    contain = page.evaluate(
        """() => {
          const video = document.querySelector('#cutPreviewVideo');
          const host = document.querySelector('#editorSuitePreviewOverlay');
          const canvas = host.querySelector('.editor-suite-preview-canvas');
          const art = canvas.querySelector('.preview-overlay:not(.is-ai-draft)');
          const hostRect = host.getBoundingClientRect();
          const canvasRect = canvas.getBoundingClientRect();
          const artRect = art.getBoundingClientRect();
          return {
            videoWidth: video.videoWidth,
            videoHeight: video.videoHeight,
            objectFit: getComputedStyle(video).objectFit,
            host: { left: hostRect.left, top: hostRect.top, width: hostRect.width, height: hostRect.height },
            canvas: { left: canvasRect.left, top: canvasRect.top, width: canvasRect.width, height: canvasRect.height },
            artX: (artRect.left + artRect.width / 2 - canvasRect.left) / canvasRect.width,
            artY: (artRect.top + artRect.height / 2 - canvasRect.top) / canvasRect.height,
            fontSize: art.style.fontSize,
            canvasWidth: canvas.style.width,
            canvasHeight: canvas.style.height,
          };
        }"""
    )
    assert (contain["videoWidth"], contain["videoHeight"]) == (720, 1280)
    assert contain["objectFit"] == "contain"
    assert contain["canvasWidth"] == "720px"
    assert contain["canvasHeight"] == "1280px"
    contain_scale = min(
        contain["host"]["width"] / contain["videoWidth"],
        contain["host"]["height"] / contain["videoHeight"],
    )
    assert contain["canvas"]["width"] == pytest.approx(
        contain["videoWidth"] * contain_scale,
        abs=1,
    )
    assert contain["canvas"]["height"] == pytest.approx(
        contain["videoHeight"] * contain_scale,
        abs=1,
    )
    assert contain["canvas"]["left"] == pytest.approx(
        contain["host"]["left"]
        + (contain["host"]["width"] - contain["canvas"]["width"]) / 2,
        abs=1,
    )
    assert contain["canvas"]["top"] == pytest.approx(contain["host"]["top"], abs=1)
    assert contain["artX"] == pytest.approx(0.5, abs=0.01)
    assert contain["artY"] == pytest.approx(0.78, abs=0.01)
    assert contain["fontSize"] == "48px"

    def drag_art_to(x: float, y: float) -> None:
        geometry = page.evaluate(
            """({ x, y }) => {
              const canvas = document.querySelector('.editor-suite-preview-canvas');
              const art = canvas.querySelector('.preview-overlay:not(.is-ai-draft)');
              const canvasRect = canvas.getBoundingClientRect();
              const artRect = art.getBoundingClientRect();
              return {
                startX: artRect.left + artRect.width / 2,
                startY: artRect.top + artRect.height / 2,
                endX: canvasRect.left + canvasRect.width * x,
                endY: canvasRect.top + canvasRect.height * y,
              };
            }""",
            {"x": x, "y": y},
        )
        page.mouse.move(geometry["startX"], geometry["startY"])
        page.mouse.down()
        page.mouse.move(geometry["endX"], geometry["endY"], steps=4)
        page.mouse.up()
        page.wait_for_function(
            """({ x, y }) => {
              const overlay = window.EditorSuite.projectSnapshot().project.art.overlays[0];
              return Math.abs(overlay.x - x) <= 0.01 && Math.abs(overlay.y - y) <= 0.01;
            }""",
            arg={"x": x, "y": y},
        )

    drag_art_to(0.55, 0.45)

    stage.evaluate(
        """node => {
          for (const name of ['width', 'height', 'max-width', 'max-height', 'aspect-ratio']) {
            node.style.removeProperty(name);
          }
        }"""
    )
    page.locator("[data-douyin-preview-toggle]").click()
    page.wait_for_function(
        """() => document.querySelector('.editor-suite-preview-canvas')
          ?.dataset.previewFit === 'cover'"""
    )
    cover = page.evaluate(
        """() => {
          const host = document.querySelector('#editorSuitePreviewOverlay');
          const canvas = host.querySelector('.editor-suite-preview-canvas');
          const art = canvas.querySelector('.preview-overlay:not(.is-ai-draft)');
          const chrome = document.querySelector('.editor-suite-douyin-chrome');
          const hostRect = host.getBoundingClientRect();
          const canvasRect = canvas.getBoundingClientRect();
          return {
            host: { left: hostRect.left, top: hostRect.top, width: hostRect.width, height: hostRect.height },
            canvas: { left: canvasRect.left, top: canvasRect.top, width: canvasRect.width, height: canvasRect.height },
            pointerEvents: getComputedStyle(art).pointerEvents,
            chromeIsCanvasChild: canvas.contains(chrome),
          };
        }"""
    )
    cover_scale = max(
        cover["host"]["width"] / 720,
        cover["host"]["height"] / 1280,
    )
    assert cover["canvas"]["width"] == pytest.approx(720 * cover_scale, abs=1)
    assert cover["canvas"]["height"] == pytest.approx(1280 * cover_scale, abs=1)
    assert cover["canvas"]["left"] == pytest.approx(
        cover["host"]["left"]
        + (cover["host"]["width"] - cover["canvas"]["width"]) / 2,
        abs=1,
    )
    assert cover["canvas"]["top"] == pytest.approx(
        cover["host"]["top"]
        + (cover["host"]["height"] - cover["canvas"]["height"]) / 2,
        abs=1,
    )
    assert cover["pointerEvents"] == "auto"
    assert cover["chromeIsCanvasChild"] is False
    drag_art_to(0.48, 0.6)

    pip = page.locator("#editorSuitePreviewOverlay .pip-preview-item").first
    pip.wait_for(state="visible")
    pip.click()
    handle = pip.locator('[data-pip-resize="e"]')
    handle.wait_for(state="visible")
    handle_state = handle.evaluate(
        """node => ({
          display: getComputedStyle(node).display,
          pointerEvents: getComputedStyle(node).pointerEvents,
        })"""
    )
    assert handle_state == {"display": "block", "pointerEvents": "auto"}
    width_before = page.evaluate(
        "window.EditorSuite.projectSnapshot().project.pip.overlays[0].width"
    )
    handle_box = handle.bounding_box()
    assert handle_box is not None
    page.mouse.move(
        handle_box["x"] + handle_box["width"] / 2,
        handle_box["y"] + handle_box["height"] / 2,
    )
    page.mouse.down()
    page.mouse.move(
        handle_box["x"] + handle_box["width"] / 2 + 20,
        handle_box["y"] + handle_box["height"] / 2,
        steps=4,
    )
    page.mouse.up()
    page.wait_for_function(
        """width => window.EditorSuite.projectSnapshot()
          .project.pip.overlays[0].width > width""",
        arg=width_before,
    )


def test_top_level_art_panel_edits_once_and_recovers_versioned_draft(
    browser_session,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
    install_base_media_mutation_probe(page)
    page.locator('[data-editor-tool="art"]').click()
    panel = page.locator("#editorArtPanelRoot")
    panel.wait_for(state="visible")
    assert page.locator('iframe[title="艺术字设置"]').count() == 0

    before = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          window.__b2ArtVideo = document.querySelector('#cutPreviewVideo');
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            id: snapshot.project.art.overlays[0].id,
          };
        }"""
    )
    text_field = panel.locator('[data-art-field="text"]')
    text_field.fill("刷新后保留的重点")
    text_field.press("Tab")
    page.wait_for_function(
        """text => window.EditorSuite.projectSnapshot().project.art.overlays[0].text === text""",
        arg="刷新后保留的重点",
    )
    after_text = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            composition: window.EditorSuite.compositionRequest(),
            sameVideo: window.__b2ArtVideo === document.querySelector('#cutPreviewVideo'),
          };
        }"""
    )
    assert after_text["revision"] == before["revision"] + 1
    assert after_text["timingRevision"] == before["timingRevision"]
    assert after_text["composition"]["artOverlays"][0]["text"] == (
        "刷新后保留的重点"
    )
    assert after_text["sameVideo"] is True

    start_field = panel.locator('[data-art-range="start"]')
    start_field.fill("0.42")
    start_field.press("Tab")
    page.wait_for_function(
        """() => Math.abs(
          window.EditorSuite.projectSnapshot().project.art.overlays[0].start - 0.42
        ) < 0.001"""
    )
    after_range = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            draft: JSON.parse(sessionStorage.getItem(
              `editor-suite:project-draft:${snapshot.jobId}`
            )),
          };
        }"""
    )
    assert after_range["revision"] == after_text["revision"] + 1
    assert after_range["timingRevision"] == after_text["timingRevision"] + 1
    assert after_range["draft"]["schemaVersion"] == 2
    assert after_range["draft"]["jobId"] == seeded_editor_job.job_id
    assert after_range["draft"]["art"]["overlays"][0]["id"] == before["id"]
    assert after_range["draft"]["pip"]["overlays"][0]["assetId"] == (
        seeded_editor_job.pip_asset_id
    )

    x_field = panel.locator('[data-art-coordinate="x"]')
    x_field.fill("105")
    x_field.press("Tab")
    page.wait_for_function(
        """() => Math.abs(
          window.EditorSuite.projectSnapshot().project.art.overlays[0].x - 0.95
        ) < 0.001"""
    )
    assert float(x_field.input_value()) == pytest.approx(95.0)

    end_field = panel.locator('[data-art-range="end"]')
    end_field.fill("5")
    end_field.press("Tab")
    page.wait_for_function(
        """() => Math.abs(
          window.EditorSuite.projectSnapshot().project.art.overlays[0].end - 1
        ) < 0.001"""
    )
    assert float(end_field.input_value()) == pytest.approx(1.0)
    assert base_media_mutations(page) == {"srcWrites": 0, "loadCalls": 0}

    page.reload()
    page.locator("#resultCard").wait_for(state="visible")
    page.locator("#editorArtPanelRoot").wait_for(state="visible")
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays[0]?.text ===
          '刷新后保留的重点'"""
    )
    restored = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            id: snapshot.project.art.overlays[0].id,
                text: snapshot.project.art.overlays[0].text,
                start: snapshot.project.art.overlays[0].start,
                end: snapshot.project.art.overlays[0].end,
                x: snapshot.project.art.overlays[0].x,
                selection: snapshot.project.timeline.selection?.clipId || null,
            composition: window.EditorSuite.compositionRequest(),
          };
        }"""
    )
    assert restored["id"] == before["id"]
    assert restored["text"] == "刷新后保留的重点"
    assert restored["start"] == pytest.approx(0.42, abs=0.001)
    assert restored["end"] == pytest.approx(1.0, abs=0.001)
    assert restored["x"] == pytest.approx(0.95, abs=0.001)
    assert restored["selection"] == f'art:{before["id"]}'
    assert restored["composition"]["artOverlays"][0]["text"] == restored["text"]


def test_top_level_art_track_and_ai_draft_commit_atomically(
    browser_session,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
    page.locator("#cutDraftSaveStatus").filter(
        has_text="剪辑草稿已保存"
    ).wait_for()
    page.locator('[data-editor-tool="art"]').click()
    panel = page.locator("#editorArtPanelRoot")
    panel.wait_for(state="visible")

    track_url = re.compile(
        rf".*/api/transcriptions/{seeded_editor_job.job_id}/art-text/transcript-track$"
    )
    page.route(
        track_url,
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=(
                '{"trackId":"browser-full","trackType":"transcript",'
                '"fontSize":54,"cueCount":2,"cues":['
                '{"text":"删除片段","start":0.05,"end":0.3,'
                '"sourceStart":0.05,"sourceEnd":0.3},'
                '{"text":"保留内容","start":0.35,"end":0.95,'
                '"sourceStart":0.35,"sourceEnd":0.95}]}'
            ),
        ),
    )
    page.evaluate(
        """() => {
          window.__b2TrackActions = [];
          window.EditorSuite.subscribeProject((next, previous, action) => {
            window.__b2TrackActions.push({
              type: action.type,
              revision: next.revision,
              previousRevision: previous.revision,
              timingRevision: next.timingRevision,
              previousTimingRevision: previous.timingRevision,
            });
          });
        }"""
    )
    panel.locator('[data-art-tab="selection"]').click()
    with page.expect_response(track_url) as track_response:
        panel.locator("[data-art-full-track]").click()
    assert track_response.value.status == 200
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays
          .filter(item => item.trackType === 'transcript').length === 2"""
    )
    assert panel.locator('[data-art-tab="settings"]').get_attribute(
        "aria-selected"
    ) == "true"
    track_state = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            actions: window.__b2TrackActions,
            overlays: snapshot.project.art.overlays,
            request: window.EditorSuite.compositionRequest(),
          };
        }"""
    )
    assert len(track_state["actions"]) == 1
    assert track_state["actions"][0]["type"] == "artStateChanged"
    assert track_state["actions"][0]["revision"] == (
        track_state["actions"][0]["previousRevision"] + 1
    )
    assert track_state["actions"][0]["timingRevision"] == (
        track_state["actions"][0]["previousTimingRevision"] + 1
    )
    assert len(track_state["request"]["artOverlays"]) == 3
    transcript_ids = [
        item["id"]
        for item in track_state["overlays"]
        if item.get("trackType") == "transcript"
    ]
    page.evaluate(
        """() => window.EditorSuite.setCutDraft({
          active: true,
          ranges: [{ start: 0.05, end: 0.3 }],
          sourceDuration: 1,
          duration: 0.75,
          transcript: {
            text: '保留内容',
            segments: [{
              id: 'retained', text: '保留内容', start: 0.1, end: 0.7,
              sourceStart: 0.35, sourceEnd: 0.95,
              words: [{
                text: '保留内容', start: 0.1, end: 0.7,
                sourceStart: 0.35, sourceEnd: 0.95,
              }],
            }],
          },
        })"""
    )
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays
          .filter(item => item.trackType === 'transcript').length === 1"""
    )
    cut_frame = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const frame = window.EditorProjectStore.selectEditorFrame(snapshot);
          return {
            activeTranscript: snapshot.project.art.overlays
              .filter(item => item.trackType === 'transcript')
              .map(item => ({ id: item.id, text: item.text })),
            suppressed: snapshot.project.art.suppressedOverlays.map(item => item.id),
            timeline: frame.timeline.tracks.filter(track => track.kind === 'art')
              .flatMap(track => track.clips.map(clip => clip.sourceId)),
            preview: frame.preview.art.overlays.map(item => item.id),
            composition: frame.composition.artOverlays.map(item => item.text),
          };
        }"""
    )
    assert cut_frame["activeTranscript"] == [
        {"id": transcript_ids[1], "text": "保留内容"}
    ]
    assert cut_frame["suppressed"] == [transcript_ids[0]]
    assert sorted(cut_frame["timeline"]) == sorted(cut_frame["preview"])
    assert "删除片段" not in cut_frame["composition"]

    page.evaluate(
        """() => window.EditorSuite.setCutDraft({
          active: false,
          ranges: [],
          sourceDuration: 1,
          duration: 1,
          transcript: {
            text: '删除片段 保留内容',
            segments: [
              {
                id: 'first', text: '删除片段', start: 0.05, end: 0.3,
                sourceStart: 0.05, sourceEnd: 0.3,
                words: [{
                  text: '删除片段', start: 0.05, end: 0.3,
                  sourceStart: 0.05, sourceEnd: 0.3,
                }],
              },
              {
                id: 'second', text: '保留内容', start: 0.35, end: 0.95,
                sourceStart: 0.35, sourceEnd: 0.95,
                words: [{
                  text: '保留内容', start: 0.35, end: 0.95,
                  sourceStart: 0.35, sourceEnd: 0.95,
                }],
              },
            ],
          },
        })"""
    )
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays
          .filter(item => item.trackType === 'transcript').length === 2"""
    )
    restored_track = page.evaluate(
        """() => ({
          ids: window.EditorSuite.projectSnapshot().project.art.overlays
            .filter(item => item.trackType === 'transcript').map(item => item.id),
          suppressed: window.EditorSuite.projectSnapshot().project.art.suppressedOverlays,
        })"""
    )
    assert sorted(restored_track["ids"]) == sorted(transcript_ids)
    assert restored_track["suppressed"] == []

    suggestion_requests: list[dict[str, object]] = []
    suggestion_url = re.compile(
        rf".*/api/transcriptions/{seeded_editor_job.job_id}/art-text/suggestions$"
    )
    job_url = re.compile(
        rf".*/api/transcriptions/{seeded_editor_job.job_id}$"
    )

    def suggestion_route(route) -> None:
        if route.request.method == "DELETE":
            route.fulfill(status=204, body="")
        else:
            suggestion_requests.append(
                json.loads(route.request.post_data or "{}")
            )
            route.fulfill(
                status=202,
                content_type="application/json",
                body=(
                    '{"source":"original","status":"queued",'
                    '"stage":"正在分析","progress":5}'
                ),
            )

    page.route(suggestion_url, suggestion_route)
    page.route(
        job_url,
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=(
                '{"id":"81818181-8181-4181-8181-818181818181",'
                '"artSuggestion":{"source":"original","status":"completed",'
                '"progress":100,"suggestions":[{"text":"AI 重点",'
                '"start":0.2,"end":0.5,"x":0.5,"y":0.2,'
                '"artStyle":"neon","color":"#A9E7CF",'
                '"strokeColor":"#173A31"}]}}'
            ),
        ),
    )
    panel.locator('[data-art-tab="ai"]').click()
    before_ai = page.evaluate(
        "window.EditorSuite.projectSnapshot().revision"
    )
    with page.expect_response(suggestion_url) as suggestion_response:
        panel.locator("[data-art-ai-request]").click()
    assert suggestion_response.value.status == 202
    assert suggestion_requests[0]["draftDuration"] == pytest.approx(1.0)
    assert suggestion_requests[0]["draftTranscript"]["segments"]
    panel.locator("[data-art-ai-list] .ai-suggestion-card").wait_for()
    assert page.evaluate("window.EditorSuite.projectSnapshot().revision") == before_ai
    before_preview_request = page.evaluate(
        "window.EditorSuite.compositionRequest()"
    )
    panel.locator("[data-art-ai-preview]").click()
    preview_draft = page.locator(
        "#editorSuitePreviewOverlay .preview-overlay.is-ai-draft"
    )
    preview_draft.wait_for(state="visible")
    assert "AI 重点" in preview_draft.get_attribute("aria-label")
    assert page.evaluate("window.EditorSuite.projectSnapshot().revision") == before_ai
    assert page.evaluate(
        "window.EditorSuite.compositionRequest()"
    ) == before_preview_request
    page.evaluate("window.__b2TrackActions = []")
    page.evaluate(
        """() => {
          const originalFetch = window.fetch.bind(window);
          window.__b2AiDeletePending = false;
          window.__b2AiDeleteResolve = null;
          window.__b2NewSuggestionPosts = 0;
          window.fetch = (input, options = {}) => {
            const url = String(input?.url || input || '');
            if (url.endsWith('/art-text/suggestions') && options.method === 'DELETE') {
              window.__b2AiDeletePending = true;
              return new Promise(resolve => {
                window.__b2AiDeleteResolve = () => resolve(new Response(
                  JSON.stringify({ status: 'cleared' }),
                  { status: 200, headers: { 'Content-Type': 'application/json' } },
                ));
              });
            }
            if (url.endsWith('/art-text/suggestions') && options.method === 'POST') {
              window.__b2NewSuggestionPosts += 1;
            }
            return originalFetch(input, options);
          };
        }"""
    )
    panel.locator("[data-art-ai-confirm]").click()
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays
          .some(item => item.text === 'AI 重点')"""
    )
    after_ai = page.evaluate(
        """() => ({
          actions: window.__b2TrackActions,
          request: window.EditorSuite.compositionRequest(),
        })"""
    )
    assert len(after_ai["actions"]) == 1
    assert after_ai["actions"][0]["type"] == "artStateChanged"
    assert any(
        item["text"] == "AI 重点"
        for item in after_ai["request"]["artOverlays"]
    )
    confirmed_ai = next(
        item
        for item in after_ai["request"]["artOverlays"]
        if item["text"] == "AI 重点"
    )
    assert confirmed_ai["sourceStart"] == pytest.approx(0.2)
    assert confirmed_ai["sourceEnd"] == pytest.approx(0.5)
    page.wait_for_function("window.__b2AiDeletePending === true")
    assert panel.locator("[data-art-ai-request]").is_disabled()
    panel.locator("[data-art-ai-request]").evaluate("button => button.click()")
    assert page.evaluate("window.__b2NewSuggestionPosts") == 0
    page.evaluate("window.__b2AiDeleteResolve()")
    page.wait_for_function(
        "() => !document.querySelector('[data-art-ai-request]').disabled"
    )
    panel.locator("[data-art-ai-request]").evaluate("button => button.click()")
    page.wait_for_function("window.__b2NewSuggestionPosts === 1")


def test_top_level_art_deactivation_rejects_late_track_response(
    browser_session,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
    page.locator('[data-editor-tool="art"]').click()
    panel = page.locator("#editorArtPanelRoot")
    panel.wait_for(state="visible")
    page.evaluate(
        """() => {
          const originalFetch = window.fetch.bind(window);
          window.__b2LateTrackRequests = [];
          window.fetch = (input, options) => {
            const url = String(input?.url || input || '');
            if (!url.endsWith('/art-text/transcript-track')) {
              return originalFetch(input, options);
            }
            return new Promise(resolve => {
              window.__b2LateTrackRequests.push({
                resolve(trackId) {
                  resolve(new Response(JSON.stringify({
                    trackId,
                    trackType: 'transcript',
                    fontSize: 54,
                    cueCount: 1,
                    cues: [{
                      text: trackId,
                      start: 0.1,
                      end: 0.8,
                      sourceStart: 0.1,
                      sourceEnd: 0.8,
                    }],
                  }), {
                    status: 200,
                    headers: { 'Content-Type': 'application/json' },
                  }));
                },
              });
            });
          };
        }"""
    )
    panel.locator('[data-art-tab="selection"]').click()
    panel.locator("[data-art-full-track]").click()
    page.wait_for_function("() => window.__b2LateTrackRequests.length === 1")
    page.locator('[data-editor-tool="pip"]').click()
    page.locator('[data-editor-tool="art"]').click()
    panel.wait_for(state="visible")
    panel.locator('[data-art-tab="selection"]').click()
    panel.locator("[data-art-full-track]").click()
    page.wait_for_function("() => window.__b2LateTrackRequests.length === 2")
    before_old_resolution = page.evaluate(
        "window.EditorSuite.projectSnapshot().revision"
    )

    page.evaluate(
        """async () => {
          window.__b2LateTrackRequests[0].resolve('late-old-track');
          await Promise.resolve();
          await new Promise(resolve => requestAnimationFrame(resolve));
        }"""
    )
    after_old = page.evaluate(
        """() => ({
          revision: window.EditorSuite.projectSnapshot().revision,
          hasOld: window.EditorSuite.projectSnapshot().project.art.overlays
            .some(item => item.trackId === 'late-old-track'),
        })"""
    )
    assert after_old == {
        "revision": before_old_resolution,
        "hasOld": False,
    }

    page.evaluate(
        """() => window.__b2LateTrackRequests[1].resolve('current-track')"""
    )
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays
          .some(item => item.trackId === 'current-track')"""
    )
    after_current = page.evaluate(
        """() => ({
          revision: window.EditorSuite.projectSnapshot().revision,
          overlays: window.EditorSuite.projectSnapshot().project.art.overlays,
        })"""
    )
    assert after_current["revision"] == before_old_resolution + 1
    assert not any(
        item.get("trackId") == "late-old-track"
        for item in after_current["overlays"]
    )


def test_top_level_pip_prompt_image_controls_and_schema_v2_recovery(
    browser_session,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
    page.locator("#cutDraftSaveStatus").filter(
        has_text="剪辑草稿已保存"
    ).wait_for()
    job_url = (
        f"{browser_session.base_url}/api/transcriptions/"
        f"{seeded_editor_job.job_id}"
    )
    job_payload = page.request.get(job_url).json()
    prompt_requests: list[dict[str, object]] = []
    image_requests: list[dict[str, object]] = []
    generated_id = "browser-generated-image"
    asset_url = (
        f"/api/transcriptions/{seeded_editor_job.job_id}/"
        f"picture-in-picture/images/{seeded_editor_job.pip_asset_id}"
    )
    generated_asset = {
        "id": generated_id,
        "type": "image",
        "text": "保留内容",
        "prompt": "金色城市天际线",
        "source": "art",
        "start": 0.35,
        "end": 0.95,
        "sourceStart": 0.35,
        "sourceEnd": 0.95,
        "aspectRatio": "16:9",
        "status": "completed",
        "imageUrl": asset_url,
        "assetUrl": asset_url,
    }

    def fulfill_prompt(route) -> None:
        prompt_requests.append(json.loads(route.request.post_data or "{}"))
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {"prompt": "AI 生成的金色城市天际线", "model": "browser-mock"},
                ensure_ascii=False,
            ),
        )

    def fulfill_image(route) -> None:
        image_requests.append(json.loads(route.request.post_data or "{}"))
        route.fulfill(
            status=201,
            content_type="application/json",
            body=json.dumps(generated_asset, ensure_ascii=False),
        )

    page.route(
        re.compile(
            rf".*/api/transcriptions/{seeded_editor_job.job_id}/"
            r"picture-in-picture/prompt$"
        ),
        fulfill_prompt,
    )
    page.route(
        re.compile(
            rf".*/api/transcriptions/{seeded_editor_job.job_id}/"
            r"picture-in-picture/images$"
        ),
        fulfill_image,
    )

    page.locator('[data-editor-tool="pip"]').click()
    panel = page.locator("#editorPipPanelRoot")
    panel.wait_for(state="visible")
    compact_geometry = panel.evaluate(
        """host => {
          const tool = host.querySelector('.editor-pip-tool');
          const content = host.querySelector('.editor-pip-tool-panel');
          const segment = host.querySelector('.pip-segment-option');
          const radio = segment?.querySelector('input');
          const segmentText = segment?.querySelector('strong');
          const segmentTime = segment?.querySelector('time');
          const mode = host.querySelector('.pip-mode-option');
          const modeRadio = mode?.querySelector('input[type="radio"]');
          const modeHelp = mode?.querySelector('small');
          const title = host.querySelector('#editorPipTitle');
          const legend = host.querySelector('legend');
          const aspect = host.querySelector('[data-pip-aspect]');
          const action = host.querySelector('[data-pip-generate]');
          const numberInput = host.querySelector('[data-pip-range="start"]');
          const prompt = host.querySelector('[data-pip-prompt]');
          const resultCount = host.querySelector('[data-pip-count]');
          const sectionStatus = host.querySelector('[data-pip-segment-time]');
          const sectionTitle = host.querySelector('.pip-section-title-row h3');
          const emptyState = host.querySelector('[data-pip-empty]');
          const toolRect = tool.getBoundingClientRect();
          const contentRect = content.getBoundingClientRect();
          const segmentRect = segment.getBoundingClientRect();
          const radioRect = radio.getBoundingClientRect();
          const timeRect = segmentTime.getBoundingClientRect();
          const textRect = segmentText.getBoundingClientRect();
          const contentStyle = getComputedStyle(content);
          const segmentTextStyle = getComputedStyle(segmentText);
          return {
            toolWidth: toolRect.width,
            contentWidth: contentRect.width,
            zoom: Number.parseFloat(contentStyle.zoom),
            fontFamily: contentStyle.fontFamily,
            fontWeight: contentStyle.fontWeight,
            titleFontWeight: getComputedStyle(title).fontWeight,
            legendFontWeight: getComputedStyle(legend).fontWeight,
            strongFontWeight: getComputedStyle(segmentText).fontWeight,
            helperFontWeight: getComputedStyle(modeHelp).fontWeight,
            resultCountFontSize: getComputedStyle(resultCount).fontSize,
            sectionStatusFontSize: getComputedStyle(sectionStatus).fontSize,
            sectionTitleFontSize: getComputedStyle(sectionTitle).fontSize,
            segmentTimeFontSize: getComputedStyle(segmentTime).fontSize,
            segmentStrongFontSize: getComputedStyle(segmentText).fontSize,
            helperFontSize: getComputedStyle(modeHelp).fontSize,
            legendFontSize: getComputedStyle(legend).fontSize,
            selectFontSize: getComputedStyle(aspect).fontSize,
            buttonFontSize: getComputedStyle(action).fontSize,
            inputFontSize: getComputedStyle(numberInput).fontSize,
            textareaFontSize: getComputedStyle(prompt).fontSize,
            emptyFontSize: getComputedStyle(emptyState).fontSize,
            selectFontFamily: getComputedStyle(aspect).fontFamily,
            buttonFontFamily: getComputedStyle(action).fontFamily,
            inputFontFamily: getComputedStyle(numberInput).fontFamily,
            radioFontFamily: getComputedStyle(radio).fontFamily,
            textareaFontFamily: getComputedStyle(prompt).fontFamily,
            segmentHeight: segment.getBoundingClientRect().height,
            radioWidth: radio.getBoundingClientRect().width,
            radioHeight: radio.getBoundingClientRect().height,
            radioLeftInset: radioRect.left - segmentRect.left,
            radioFullyVisible: radioRect.left >= segmentRect.left &&
              radioRect.right <= segmentRect.right,
            timeTextGap: textRect.left - timeRect.right,
            timeBeforeText: timeRect.right < textRect.left,
            timeOverflow: segmentTime.scrollWidth > segmentTime.clientWidth + 1,
            strongEllipsis: {
              overflow: segmentTextStyle.overflow,
              textOverflow: segmentTextStyle.textOverflow,
              whiteSpace: segmentTextStyle.whiteSpace,
            },
            modeHeight: mode.getBoundingClientRect().height,
            modeRadioWidth: modeRadio.getBoundingClientRect().width,
            modeRadioHeight: modeRadio.getBoundingClientRect().height,
            rowClipping: [...host.querySelectorAll('.pip-segment-option')].some(
              item => item.scrollHeight > item.clientHeight + 1
            ),
            horizontalOverflow: tool.scrollWidth > tool.clientWidth + 1,
          };
        }"""
    )
    assert compact_geometry["contentWidth"] == pytest.approx(
        compact_geometry["toolWidth"] - 16,
        abs=1.5,
    )
    assert compact_geometry["zoom"] == pytest.approx(0.6)
    assert "Microsoft YaHei UI" in compact_geometry["fontFamily"]
    for control in ("button", "input", "radio", "select", "textarea"):
        assert compact_geometry[f"{control}FontFamily"] == compact_geometry["fontFamily"]
    assert compact_geometry["fontWeight"] == "500"
    assert compact_geometry["titleFontWeight"] == "700"
    assert compact_geometry["legendFontWeight"] == "700"
    assert compact_geometry["strongFontWeight"] == "700"
    assert compact_geometry["helperFontWeight"] == "500"
    assert compact_geometry["resultCountFontSize"] == "16px"
    assert compact_geometry["sectionStatusFontSize"] == "16px"
    assert compact_geometry["sectionTitleFontSize"] == "18px"
    assert compact_geometry["segmentTimeFontSize"] == "15px"
    assert compact_geometry["segmentStrongFontSize"] == "17px"
    assert compact_geometry["helperFontSize"] == "15px"
    assert compact_geometry["legendFontSize"] == "16px"
    assert compact_geometry["selectFontSize"] == "16px"
    assert compact_geometry["buttonFontSize"] == "16px"
    assert compact_geometry["inputFontSize"] == "16px"
    assert compact_geometry["textareaFontSize"] == "16px"
    assert compact_geometry["emptyFontSize"] == "16px"
    assert compact_geometry["segmentHeight"] == pytest.approx(38.4, abs=0.75)
    assert compact_geometry["radioWidth"] == pytest.approx(15.6, abs=0.75)
    assert compact_geometry["radioHeight"] == pytest.approx(15.6, abs=0.75)
    assert compact_geometry["radioLeftInset"] >= 8
    assert compact_geometry["radioFullyVisible"] is True
    assert compact_geometry["timeTextGap"] == pytest.approx(7.2, abs=0.5)
    assert compact_geometry["timeBeforeText"] is True
    assert compact_geometry["timeOverflow"] is False
    assert compact_geometry["strongEllipsis"] == {
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "whiteSpace": "nowrap",
    }
    assert compact_geometry["modeHeight"] == pytest.approx(39.6, abs=0.75)
    assert compact_geometry["modeRadioWidth"] == pytest.approx(15.6, abs=0.75)
    assert compact_geometry["modeRadioHeight"] == pytest.approx(15.6, abs=0.75)
    assert compact_geometry["rowClipping"] is False
    assert compact_geometry["horizontalOverflow"] is False

    original_viewport = page.viewport_size
    page.set_viewport_size({"width": 375, "height": 812})
    mobile_geometry = panel.evaluate(
        """host => {
          const tool = host.querySelector('.editor-pip-tool');
          const content = host.querySelector('.editor-pip-tool-panel');
          const segment = host.querySelector('.pip-segment-option');
          const radio = segment?.querySelector('input[type="radio"]');
          const segmentText = segment?.querySelector('strong');
          const segmentTime = segment?.querySelector('time');
          const modeRadio = host.querySelector('.pip-mode-option input[type="radio"]');
          const aspect = host.querySelector('[data-pip-aspect]');
          const action = host.querySelector('[data-pip-generate]');
          const numberInput = host.querySelector('[data-pip-range="start"]');
          const prompt = host.querySelector('[data-pip-prompt]');
          const contentStyle = getComputedStyle(content);
          const segmentRect = segment.getBoundingClientRect();
          const radioRect = radio.getBoundingClientRect();
          const timeRect = segmentTime.getBoundingClientRect();
          const textRect = segmentText.getBoundingClientRect();
          const segmentTextStyle = getComputedStyle(segmentText);
          return {
            toolWidth: tool.getBoundingClientRect().width,
            contentWidth: content.getBoundingClientRect().width,
            zoom: Number.parseFloat(contentStyle.zoom),
            fontFamily: contentStyle.fontFamily,
            fontWeight: contentStyle.fontWeight,
            strongFontWeight: getComputedStyle(segmentText).fontWeight,
            segmentTimeFontSize: getComputedStyle(segmentTime).fontSize,
            segmentStrongFontSize: getComputedStyle(segmentText).fontSize,
            buttonFontSize: getComputedStyle(action).fontSize,
            buttonFontFamily: getComputedStyle(action).fontFamily,
            inputFontFamily: getComputedStyle(numberInput).fontFamily,
            radioFontFamily: getComputedStyle(radio).fontFamily,
            selectFontFamily: getComputedStyle(aspect).fontFamily,
            textareaFontFamily: getComputedStyle(prompt).fontFamily,
            segmentHeight: segment.getBoundingClientRect().height,
            radioWidth: radio.getBoundingClientRect().width,
            radioHeight: radio.getBoundingClientRect().height,
            radioLeftInset: radioRect.left - segmentRect.left,
            radioFullyVisible: radioRect.left >= segmentRect.left &&
              radioRect.right <= segmentRect.right,
            timeTextGap: textRect.left - timeRect.right,
            timeBeforeText: timeRect.right < textRect.left,
            timeOverflow: segmentTime.scrollWidth > segmentTime.clientWidth + 1,
            strongEllipsis: {
              overflow: segmentTextStyle.overflow,
              textOverflow: segmentTextStyle.textOverflow,
              whiteSpace: segmentTextStyle.whiteSpace,
            },
            modeRadioWidth: modeRadio.getBoundingClientRect().width,
            modeRadioHeight: modeRadio.getBoundingClientRect().height,
            rowClipping: [...host.querySelectorAll('.pip-segment-option')].some(
              item => item.scrollHeight > item.clientHeight + 1
            ),
            horizontalOverflow: tool.scrollWidth > tool.clientWidth + 1,
          };
        }"""
    )
    assert mobile_geometry["contentWidth"] == pytest.approx(
        mobile_geometry["toolWidth"] - 12,
        abs=1.5,
    )
    assert mobile_geometry["zoom"] == pytest.approx(0.6)
    assert "Microsoft YaHei UI" in mobile_geometry["fontFamily"]
    for control in ("button", "input", "radio", "select", "textarea"):
        assert mobile_geometry[f"{control}FontFamily"] == mobile_geometry["fontFamily"]
    assert mobile_geometry["fontWeight"] == "500"
    assert mobile_geometry["strongFontWeight"] == "700"
    assert mobile_geometry["segmentTimeFontSize"] == "15px"
    assert mobile_geometry["segmentStrongFontSize"] == "17px"
    assert mobile_geometry["buttonFontSize"] == "16px"
    assert mobile_geometry["segmentHeight"] == pytest.approx(38.4, abs=0.75)
    assert mobile_geometry["radioWidth"] == pytest.approx(15.6, abs=0.75)
    assert mobile_geometry["radioHeight"] == pytest.approx(15.6, abs=0.75)
    assert mobile_geometry["radioLeftInset"] >= 8
    assert mobile_geometry["radioFullyVisible"] is True
    assert mobile_geometry["timeTextGap"] == pytest.approx(7.2, abs=0.5)
    assert mobile_geometry["timeBeforeText"] is True
    assert mobile_geometry["timeOverflow"] is False
    assert mobile_geometry["strongEllipsis"] == {
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "whiteSpace": "nowrap",
    }
    assert mobile_geometry["modeRadioWidth"] == pytest.approx(15.6, abs=0.75)
    assert mobile_geometry["modeRadioHeight"] == pytest.approx(15.6, abs=0.75)
    assert mobile_geometry["rowClipping"] is False
    assert mobile_geometry["horizontalOverflow"] is False
    page.set_viewport_size(original_viewport)

    segment_list = panel.locator("[data-pip-segments]")
    outer_scroll = panel.locator(".editor-pip-tool").evaluate(
        "tool => tool.scrollTop"
    )
    segment_list.locator("label", has_text="保留内容").locator("input").check()
    segment_list.evaluate(
        "list => { list.style.height = '80px'; list.scrollTop = list.scrollHeight; }"
    )
    segment_list.locator("label", has_text="删除片段").locator("input").check()
    selected_bounds = segment_list.evaluate(
        """list => {
          const item = list.querySelector('.is-selected');
          const listRect = list.getBoundingClientRect();
          const itemRect = item.getBoundingClientRect();
          const selectedText = item.querySelector('strong').textContent;
          const expected = window.EditorSuite.projectSnapshot().project.cut
            .transcript.segments.find(segment => segment.text === selectedText);
          const start = Number(document.querySelector('[data-pip-range="start"]').value);
          const end = Number(document.querySelector('[data-pip-range="end"]').value);
          return {
            visible: itemRect.top >= listRect.top - 1 &&
              itemRect.bottom <= listRect.bottom + 1,
            rangeMatches: Math.abs(start - expected.start) < 0.001 &&
              Math.abs(end - expected.end) < 0.001,
          };
        }"""
    )
    assert selected_bounds == {"visible": True, "rangeMatches": True}
    assert panel.locator(".editor-pip-tool").evaluate(
        "tool => tool.scrollTop"
    ) == outer_scroll
    panel.locator("[data-pip-segments] label", has_text="保留内容").locator(
        "input"
    ).check()
    panel.locator("[data-pip-write-prompt]").click()
    page.wait_for_function(
        """() => document.querySelector('#editorPipPanelRoot [data-pip-prompt]')
          ?.value === 'AI 生成的金色城市天际线'"""
    )
    assert prompt_requests[0]["text"] == "保留内容"
    assert prompt_requests[0]["assetType"] == "image"
    assert prompt_requests[0]["source"] == "art"

    panel.locator("[data-pip-prompt]").fill("金色城市天际线")
    panel.locator("[data-pip-generate]").click()
    generated_card = panel.locator(
        f'.pip-generated-card[data-picture-id="{generated_id}"]'
    )
    generated_card.wait_for(state="visible")
    asset_typography = generated_card.evaluate(
        """card => {
          const style = element => getComputedStyle(element);
          const time = card.querySelector('time');
          const toggle = card.querySelector('.pip-enabled-toggle');
          const copy = card.querySelector('.pip-generated-content > p');
          const label = card.querySelector('.pip-item-controls label');
          const select = card.querySelector('.pip-item-controls select');
          return {
            timeFontSize: style(time).fontSize,
            toggleFontSize: style(toggle).fontSize,
            copyFontSize: style(copy).fontSize,
            labelFontSize: style(label).fontSize,
            selectFontSize: style(select).fontSize,
            horizontalOverflow: card.scrollWidth > card.clientWidth + 1,
            verticalClipping: card.scrollHeight > card.clientHeight + 1,
          };
        }"""
    )
    assert asset_typography == {
        "timeFontSize": "15px",
        "toggleFontSize": "16px",
        "copyFontSize": "16px",
        "labelFontSize": "16px",
        "selectFontSize": "16px",
        "horizontalOverflow": False,
        "verticalClipping": False,
    }
    page.set_viewport_size({"width": 375, "height": 812})
    mobile_asset_typography = generated_card.evaluate(
        """card => {
          const style = element => getComputedStyle(element);
          const tool = card.closest('.editor-pip-tool');
          return {
            timeFontSize: style(card.querySelector('time')).fontSize,
            toggleFontSize: style(card.querySelector('.pip-enabled-toggle')).fontSize,
            copyFontSize: style(card.querySelector('.pip-generated-content > p')).fontSize,
            labelFontSize: style(card.querySelector('.pip-item-controls label')).fontSize,
            selectFontSize: style(card.querySelector('.pip-item-controls select')).fontSize,
            horizontalOverflow: card.scrollWidth > card.clientWidth + 1,
            verticalClipping: card.scrollHeight > card.clientHeight + 1,
            toolOverflow: tool.scrollWidth > tool.clientWidth + 1,
            documentOverflow:
              document.documentElement.scrollWidth
                - document.documentElement.clientWidth,
          };
        }"""
    )
    assert mobile_asset_typography == {
        "timeFontSize": "15px",
        "toggleFontSize": "16px",
        "copyFontSize": "16px",
        "labelFontSize": "16px",
        "selectFontSize": "16px",
        "horizontalOverflow": False,
        "verticalClipping": False,
        "toolOverflow": False,
        "documentOverflow": 0,
    }
    page.set_viewport_size(original_viewport)
    page.wait_for_function(
        """id => window.EditorSuite.projectSnapshot().project.pip.overlays
          .some(item => String(item.assetId) === id)""",
        arg=generated_id,
    )
    assert image_requests[0]["mode"] == "custom"
    assert image_requests[0]["prompt"] == "金色城市天际线"

    enabled = generated_card.get_by_role(
        "checkbox", name=re.compile(r"使用画中画：保留内容")
    )
    enabled.set_checked(False)
    page.wait_for_function(
        """id => !window.EditorSuite.projectSnapshot().project.pip.overlays
          .some(item => String(item.assetId) === id)""",
        arg=generated_id,
    )
    generated_card.get_by_role(
        "checkbox", name=re.compile(r"使用画中画：保留内容")
    ).set_checked(True)
    page.wait_for_function(
        """id => window.EditorSuite.projectSnapshot().project.pip.overlays
          .some(item => String(item.assetId) === id)""",
        arg=generated_id,
    )

    generated_card = panel.locator(
        f'.pip-generated-card[data-picture-id="{generated_id}"]'
    )
    generated_card.locator("select").select_option("center")
    width_input = generated_card.locator(f'[data-pip-width="{generated_id}"]')
    assert width_input.get_attribute("max") is None
    width_input.fill("175")
    width_input.press("Tab")
    panel.locator('[data-pip-range="start"]').fill("0.38")
    panel.locator('[data-pip-range="start"]').press("Tab")
    panel.locator('[data-pip-range="end"]').fill("0.90")
    panel.locator('[data-pip-range="end"]').press("Tab")
    page.wait_for_function(
        """id => {
          const item = window.EditorSuite.projectSnapshot().project.pip.overlays
            .find(overlay => String(overlay.assetId) === id);
          return item && Math.abs(item.width - 1.75) < 0.0001 &&
            Math.abs(item.x - 0.5) < 0.0001 &&
            Math.abs(item.y - 0.5) < 0.0001 &&
            Math.abs(item.start - 0.38) < 0.0001 &&
            Math.abs(item.end - 0.9) < 0.0001;
        }""",
        arg=generated_id,
    )
    stored = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const draft = JSON.parse(sessionStorage.getItem(
            `editor-suite:project-draft:${snapshot.jobId}`
          ));
          return { snapshot, draft, composition: window.EditorSuite.compositionRequest() };
        }"""
    )
    draft_overlay = next(
        item
        for item in stored["draft"]["pip"]["overlays"]
        if item["assetId"] == generated_id
    )
    compose_overlay = next(
        item
        for item in stored["composition"]["pictureInPictureOverlays"]
        if item["assetId"] == generated_id
    )
    assert stored["draft"]["schemaVersion"] == 2
    assert "assets" not in stored["draft"]["pip"]
    assert stored["draft"]["selection"] == {"clipId": f"pip:{generated_id}"}
    assert draft_overlay["width"] == pytest.approx(1.75)
    assert compose_overlay["width"] == pytest.approx(1.75)

    job_payload["pictureInPictureImages"].append(generated_asset)
    page.route(
        re.compile(
            rf".*/api/transcriptions/{seeded_editor_job.job_id}$"
        ),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(job_payload, ensure_ascii=False),
        ),
    )
    page.reload()
    page.locator("#editorPipPanelRoot").wait_for(state="visible")
    page.wait_for_function(
        """id => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const item = snapshot.project.pip.overlays
            .find(overlay => String(overlay.assetId) === id);
          return item && Math.abs(item.width - 1.75) < 0.0001 &&
            snapshot.project.timeline.selection?.clipId === `pip:${id}`;
        }""",
        arg=generated_id,
    )

    page.evaluate(
        """id => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const key = `editor-suite:project-draft:${snapshot.jobId}`;
          const draft = JSON.parse(sessionStorage.getItem(key));
          draft.selection = { clipId: 'pip:missing-asset' };
          draft.pip.overlays.find(item => item.assetId === id).width = 2.25;
          sessionStorage.setItem(key, JSON.stringify(draft));
        }""",
        generated_id,
    )
    page.reload()
    page.locator("#editorPipPanelRoot").wait_for(state="visible")
    rejected = page.evaluate(
        """id => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            generatedEnabled: snapshot.project.pip.overlays
              .some(item => String(item.assetId) === id),
            baselineWidth: snapshot.project.pip.overlays
              .find(item => String(item.assetId) === 'browser-baseline-image')?.width,
            selection: snapshot.project.timeline.selection?.clipId || null,
          };
        }""",
        generated_id,
    )
    assert rejected["generatedEnabled"] is False
    assert rejected["baselineWidth"] == pytest.approx(0.3)
    assert rejected["selection"] != "pip:missing-asset"

    page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const key = `editor-suite:project-draft:${snapshot.jobId}`;
          const draft = JSON.parse(sessionStorage.getItem(key));
          draft.selection = {};
          draft.pip.overlays.find(
            item => item.assetId === 'browser-baseline-image'
          ).width = 2.25;
          sessionStorage.setItem(key, JSON.stringify(draft));
        }"""
    )
    page.reload()
    page.locator("#editorPipPanelRoot").wait_for(state="visible")
    malformed_selection = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return snapshot.project.pip.overlays.find(
            item => item.assetId === 'browser-baseline-image'
          )?.width;
        }"""
    )
    assert malformed_selection == pytest.approx(0.3)


def test_top_level_pip_video_polling_completes_and_preserves_failed_asset(
    browser_session,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
    job_url = (
        f"{browser_session.base_url}/api/transcriptions/"
        f"{seeded_editor_job.job_id}"
    )
    base_job = page.request.get(job_url).json()
    created_ids: list[str] = []
    create_requests: list[dict[str, object]] = []
    completed_id = "browser-video-completed"
    failed_id = "browser-video-failed"

    def fulfill_video_create(route) -> None:
        request = json.loads(route.request.post_data or "{}")
        create_requests.append(request)
        asset_id = completed_id if not created_ids else failed_id
        created_ids.append(asset_id)
        route.fulfill(
            status=202,
            content_type="application/json",
            body=json.dumps(
                {
                    "id": asset_id,
                    "type": "video",
                    "text": request["text"],
                    "prompt": request["prompt"],
                    "source": request["source"],
                    "start": request["start"],
                    "end": request["end"],
                    "aspectRatio": request["aspectRatio"],
                    "status": "queued",
                    "progress": 5,
                },
                ensure_ascii=False,
            ),
        )

    def fulfill_video_poll(route) -> None:
        payload = json.loads(json.dumps(base_job))
        videos = []
        if completed_id in created_ids:
            videos.append(
                {
                    "id": completed_id,
                    "type": "video",
                    "text": "删除片段",
                    "prompt": "动态城市镜头",
                    "source": "art",
                    "start": 0.05,
                    "end": 0.3,
                    "sourceStart": 0.05,
                    "sourceEnd": 0.3,
                    "aspectRatio": "16:9",
                    "status": "completed",
                    "progress": 100,
                    "assetUrl": (
                        f"/api/transcriptions/{seeded_editor_job.job_id}/original-video"
                    ),
                }
            )
        if failed_id in created_ids:
            videos.append(
                {
                    "id": failed_id,
                    "type": "video",
                    "text": "删除片段",
                    "prompt": "失败的动态镜头",
                    "source": "art",
                    "start": 0.05,
                    "end": 0.3,
                    "aspectRatio": "16:9",
                    "status": "failed",
                    "progress": 100,
                    "error": "浏览器 mock 视频生成失败",
                }
            )
        payload["pictureInPictureVideos"] = videos
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(payload, ensure_ascii=False),
        )

    page.locator('[data-editor-tool="pip"]').click()
    panel = page.locator("#editorPipPanelRoot")
    panel.wait_for(state="visible")
    page.route(
        re.compile(
            rf".*/api/transcriptions/{seeded_editor_job.job_id}/"
            r"picture-in-picture/videos$"
        ),
        fulfill_video_create,
    )
    page.route(
        re.compile(rf".*/api/transcriptions/{seeded_editor_job.job_id}$"),
        fulfill_video_poll,
    )
    panel.locator('[data-pip-asset-type][value="video"]').check()
    panel.locator("[data-pip-prompt]").fill("动态城市镜头")
    before = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return { revision: snapshot.revision, timingRevision: snapshot.timingRevision };
        }"""
    )
    panel.locator("[data-pip-generate]").click()
    completed_card = panel.locator(
        f'.pip-generated-card[data-picture-id="{completed_id}"]'
    )
    completed_card.wait_for(state="visible")
    page.wait_for_function(
        """id => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const asset = snapshot.project.pip.assets.find(item => item.id === id);
          return asset?.status === 'completed' && snapshot.project.pip.overlays
            .some(item => item.assetId === id);
        }""",
        arg=completed_id,
    )
    completed_typography = completed_card.evaluate(
        """card => ({
          badgeFontSize: getComputedStyle(
            card.querySelector('.pip-video-badge')
          ).fontSize,
          timeFontSize: getComputedStyle(card.querySelector('time')).fontSize,
          toggleFontSize: getComputedStyle(
            card.querySelector('.pip-enabled-toggle')
          ).fontSize,
          copyFontSize: getComputedStyle(
            card.querySelector('.pip-generated-content > p')
          ).fontSize,
          horizontalOverflow: card.scrollWidth > card.clientWidth + 1,
          verticalClipping: card.scrollHeight > card.clientHeight + 1,
        })"""
    )
    assert completed_typography == {
        "badgeFontSize": "15px",
        "timeFontSize": "15px",
        "toggleFontSize": "16px",
        "copyFontSize": "16px",
        "horizontalOverflow": False,
        "verticalClipping": False,
    }
    completed = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return { revision: snapshot.revision, timingRevision: snapshot.timingRevision };
        }"""
    )
    assert completed["revision"] >= before["revision"] + 2
    assert completed["timingRevision"] == before["timingRevision"] + 1
    assert create_requests[0]["mode"] == "custom"

    panel.locator("[data-pip-prompt]").fill("失败的动态镜头")
    panel.locator("[data-pip-generate]").click()
    failed_card = panel.locator(
        f'.pip-generated-card[data-picture-id="{failed_id}"]'
    )
    page.wait_for_function(
        """id => window.EditorSuite.projectSnapshot().project.pip.assets
          .find(item => item.id === id)?.status === 'failed'""",
        arg=failed_id,
    )
    assert "is-failed" in (failed_card.get_attribute("class") or "")
    assert "浏览器 mock 视频生成失败" in failed_card.inner_text()
    assert failed_card.get_by_role("checkbox").is_disabled()
    failed_typography = failed_card.evaluate(
        """card => ({
          placeholderFontSize: getComputedStyle(
            card.querySelector('.pip-asset-placeholder')
          ).fontSize,
          timeFontSize: getComputedStyle(card.querySelector('time')).fontSize,
          toggleFontSize: getComputedStyle(
            card.querySelector('.pip-enabled-toggle')
          ).fontSize,
          copyFontSize: getComputedStyle(
            card.querySelector('.pip-generated-content > p')
          ).fontSize,
          horizontalOverflow: card.scrollWidth > card.clientWidth + 1,
          verticalClipping: card.scrollHeight > card.clientHeight + 1,
        })"""
    )
    assert failed_typography == {
        "placeholderFontSize": "16px",
        "timeFontSize": "15px",
        "toggleFontSize": "16px",
        "copyFontSize": "16px",
        "horizontalOverflow": False,
        "verticalClipping": False,
    }
    failed = page.evaluate(
        """id => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            timingRevision: snapshot.timingRevision,
            enabled: snapshot.project.pip.overlays.some(item => item.assetId === id),
          };
        }""",
        failed_id,
    )
    assert failed["timingRevision"] == completed["timingRevision"]
    assert failed["enabled"] is False


def test_top_level_pip_deactivation_rejects_late_asset_response(
    browser_session,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
    page.locator("#cutDraftSaveStatus").filter(
        has_text="剪辑草稿已保存"
    ).wait_for()
    page.locator('[data-editor-tool="pip"]').click()
    panel = page.locator("#editorPipPanelRoot")
    panel.wait_for(state="visible")
    before_revision = page.evaluate("window.EditorSuite.projectSnapshot().revision")
    page.evaluate(
        """() => {
          const originalFetch = window.fetch.bind(window);
          window.__b3LatePipCreate = {
            requested: false,
            aborted: false,
            resolve: null,
          };
          window.fetch = (input, options = {}) => {
            const url = String(input?.url || input || '');
            if (url.endsWith('/picture-in-picture/images') && options.method === 'POST') {
              window.__b3LatePipCreate.requested = true;
              options.signal?.addEventListener('abort', () => {
                window.__b3LatePipCreate.aborted = true;
              }, { once: true });
              return new Promise(resolve => {
                window.__b3LatePipCreate.resolve = () => resolve(new Response(
                  JSON.stringify({
                    id: 'browser-late-image',
                    type: 'image',
                    text: '迟到素材',
                    source: 'art',
                    start: 0.05,
                    end: 0.3,
                    status: 'completed',
                    assetUrl: '/late-image.png',
                  }),
                  { status: 201, headers: { 'Content-Type': 'application/json' } },
                ));
              });
            }
            return originalFetch(input, options);
          };
        }"""
    )
    panel.locator("[data-pip-prompt]").fill("迟到素材")
    panel.locator("[data-pip-generate]").click()
    page.wait_for_function("window.__b3LatePipCreate.requested === true")
    page.locator('[data-editor-tool="cut"]').click()
    page.wait_for_function("window.__b3LatePipCreate.aborted === true")
    assert panel.locator("[data-pip-prompt]").input_value() == ""
    page.evaluate(
        """async () => {
          window.__b3LatePipCreate.resolve();
          await Promise.resolve();
          await new Promise(resolve => requestAnimationFrame(
            () => requestAnimationFrame(resolve)
          ));
        }"""
    )
    after = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            revision: snapshot.revision,
            hasLateAsset: snapshot.project.pip.assets
              .some(item => item.id === 'browser-late-image'),
          };
        }"""
    )
    assert after == {
        "revision": before_revision + 1,
        "hasLateAsset": False,
    }


def test_schema_v1_art_draft_remains_compatible(
    browser_session,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
    page.locator('[data-editor-tool="art"]').click()
    panel = page.locator("#editorArtPanelRoot")
    panel.wait_for(state="visible")
    panel.locator('[data-art-field="text"]').fill("schema v1 仍可恢复")
    panel.locator('[data-art-field="text"]').press("Tab")
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays[0]
          ?.text === 'schema v1 仍可恢复'"""
    )
    page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const key = `editor-suite:project-draft:${snapshot.jobId}`;
          const draft = JSON.parse(sessionStorage.getItem(key));
          draft.schemaVersion = 1;
          delete draft.pip;
          sessionStorage.setItem(key, JSON.stringify(draft));
        }"""
    )
    page.reload()
    page.locator("#editorArtPanelRoot").wait_for(state="visible")
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays[0]
          ?.text === 'schema v1 仍可恢复'"""
    )
    restored = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            artText: snapshot.project.art.overlays[0]?.text,
            pipIds: snapshot.project.pip.overlays.map(item => item.assetId),
          };
        }"""
    )
    assert restored["artText"] == "schema v1 仍可恢复"
    assert restored["pipIds"] == [seeded_editor_job.pip_asset_id]


def test_legacy_pip_url_redirects_to_single_top_level_runtime(
    browser_session,
    seeded_editor_job,
):
    page = browser_session.page
    page.goto(
        f"{browser_session.base_url}/picture-in-picture"
        f"?job={seeded_editor_job.job_id}&source=art&embedded=1&tool=cut"
    )
    page.locator("#editorPipPanelRoot").wait_for(state="visible")
    page.wait_for_function("() => window.EditorSuite?.activeTool() === 'pip'")

    destination = page.evaluate(
        """() => ({
          path: location.pathname,
          job: new URLSearchParams(location.search).get('job'),
          source: new URLSearchParams(location.search).get('source'),
          tool: new URLSearchParams(location.search).get('tool'),
          hasEmbedded: new URLSearchParams(location.search).has('embedded'),
          iframeCount: document.querySelectorAll('iframe').length,
          videoCount: document.querySelectorAll('#cutPreviewVideo').length,
          pipInert: document.querySelector('#editorPipPanelRoot').inert,
          cutInert: document.querySelector('.text-editor-panel-stack').inert,
        })"""
    )
    assert destination == {
        "path": "/",
        "job": seeded_editor_job.job_id,
        "source": "art",
        "tool": "pip",
        "hasEmbedded": False,
        "iframeCount": 0,
        "videoCount": 1,
        "pipInert": False,
        "cutInert": True,
    }

    size = page.locator(
        f'.pip-generated-card[data-picture-id="{seeded_editor_job.pip_asset_id}"] '
        'input[type="number"]'
    )
    assert size.get_attribute("max") is None
    size.fill("175")
    size.press("Tab")
    page.wait_for_function(
        """id => Math.abs(
          window.EditorSuite.projectSnapshot().project.pip.overlays
            .find(item => item.assetId === id)?.width - 1.75
        ) < 0.0001""",
        arg=seeded_editor_job.pip_asset_id,
    )


@pytest.mark.parametrize("playing", [False, True], ids=["paused", "playing"])
def test_version_save_preserves_base_media_identity_and_playback(
    browser_session,
    seeded_editor_job,
    playing,
):
    page = open_editor(browser_session, seeded_editor_job)
    page.locator('[data-editor-tool="art"]').click()
    page.locator("#editorArtPanelRoot").wait_for(state="visible")
    save_button = page.locator("[data-editor-suite-save]")
    save_button.wait_for(state="visible")
    install_base_media_mutation_probe(page)

    before = page.locator("#cutPreviewVideo").evaluate(
        """async (video, playing) => {
          video.pause();
          video.currentTime = 0.35;
          video.dispatchEvent(new Event('seeking'));
          video.dispatchEvent(new Event('timeupdate'));
          if (playing) await video.play();
          window.__b1VersionSaveVideo = video;
          return {
            src: video.currentSrc || video.src,
            currentTime: video.currentTime,
            paused: video.paused,
          };
        }""",
        playing,
    )
    history_url = re.compile(
        rf".*/api/transcriptions/{seeded_editor_job.job_id}/history$"
    )
    page.route(
        history_url,
        lambda route: route.fulfill(
            status=201,
            content_type="application/json",
            body=json.dumps(
                {"id": "b1-version", "name": "B1 测试版本"},
                ensure_ascii=True,
            ),
        ),
    )
    with page.expect_response(history_url) as response_info:
        save_button.click()
    assert response_info.value.status == 201
    page.locator("[data-editor-suite-status]").filter(
        has_text="已保存“B1 测试版本”"
    ).wait_for(state="attached")

    after = page.locator("#cutPreviewVideo").evaluate(
        """video => ({
          sameNode: video === window.__b1VersionSaveVideo,
          src: video.currentSrc || video.src,
          currentTime: video.currentTime,
          paused: video.paused,
        })"""
    )
    assert after["sameNode"] is True
    assert after["src"] == before["src"]
    assert after["paused"] is before["paused"]
    if playing:
        assert after["currentTime"] >= before["currentTime"] - 0.06
    else:
        assert after["currentTime"] == pytest.approx(before["currentTime"], abs=0.06)
    assert base_media_mutations(page) == {"srcWrites": 0, "loadCalls": 0}


def test_unified_generate_posts_current_cut_art_and_pip_state(
    browser_session,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
    draft = delete_first_text_segment(page)

    page.locator('[data-editor-tool="art"]').click()
    art_panel = page.locator("#editorArtPanelRoot")
    art_panel.wait_for(state="visible")
    page.locator("#editorSuitePreviewOverlay .is-art").wait_for(state="visible")
    page.locator('[data-editor-tool="pip"]').click()
    pip_panel = page.locator("#editorPipPanelRoot")
    pip_panel.wait_for(state="visible")
    pip_panel.get_by_role(
        "button",
        name="选择画中画素材：保留内容",
    ).click()
    page.locator("#editorSuitePreviewOverlay .is-art").wait_for(state="visible")
    page.locator("#editorSuitePreviewOverlay .is-pip").wait_for(state="visible")

    compose_url = re.compile(
        rf".*/api/transcriptions/{seeded_editor_job.job_id}/compose$"
    )

    def fulfill_compose(route) -> None:
        route.fulfill(
            status=202,
            content_type="application/json",
            body='{"status":"queued","stage":"测试已捕获合成请求","progress":5}',
        )

    page.route(compose_url, fulfill_compose)
    generate = page.locator("[data-editor-suite-generate]")
    generate.wait_for(state="visible")
    assert generate.is_enabled()
    with page.expect_response(compose_url) as response_info:
        generate.click()

    response = response_info.value
    assert response.status == 202
    payload = response.request.post_data_json
    expected_art_start = float(
        art_panel.locator('[data-art-range="start"]').input_value()
    )
    expected_art_end = float(
        art_panel.locator('[data-art-range="end"]').input_value()
    )
    expected_pip = page.evaluate(
        "window.EditorSuite.projectSnapshot().project.pip.overlays[0]"
    )
    assert payload["target"] == "all"
    assert payload["ranges"] == [
        {
            "start": draft["textRanges"][0]["start"],
            "end": draft["textRanges"][0]["end"],
        }
    ]
    assert payload["cutDraftRevision"] == draft["revision"]
    assert payload["artSource"] == "original"
    assert len(payload["artOverlays"]) == 1
    for key in seeded_editor_job.art_overlay.keys() - {
        "start",
        "end",
        "sourceStart",
        "sourceEnd",
    }:
        assert payload["artOverlays"][0][key] == seeded_editor_job.art_overlay[key]
    assert payload["artOverlays"][0]["start"] == pytest.approx(
        expected_art_start,
        abs=0.001,
    )
    assert payload["artOverlays"][0]["end"] == pytest.approx(
        expected_art_end,
        abs=0.001,
    )
    assert payload["pictureInPictureSource"] == "art"
    assert len(payload["pictureInPictureOverlays"]) == 1
    for key in seeded_editor_job.pip_overlay.keys() - {
        "start",
        "end",
        "sourceStart",
        "sourceEnd",
    }:
        assert (
            payload["pictureInPictureOverlays"][0][key]
            == seeded_editor_job.pip_overlay[key]
        )
    assert payload["pictureInPictureOverlays"][0]["start"] == pytest.approx(
        expected_pip["start"],
        abs=0.001,
    )
    assert payload["pictureInPictureOverlays"][0]["end"] == pytest.approx(
        expected_pip["end"],
        abs=0.001,
    )
    assert payload["historyName"] is None


@pytest.mark.parametrize("playing", [False, True], ids=["paused", "playing"])
def test_text_edit_preserves_single_page_runtime_and_effect_timing(
    browser_session,
    seeded_transcript_track_editor_job,
    playing,
):
    page = open_editor(browser_session, seeded_transcript_track_editor_job)

    page.locator("#cutPreviewVideo").evaluate(
        """video => {
          video.pause();
          video.currentTime = 0.5;
          video.dispatchEvent(new Event('seeking'));
          video.dispatchEvent(new Event('timeupdate'));
        }"""
    )
    page.locator('[data-editor-tool="art"]').click()
    page.locator("#editorArtPanelRoot").wait_for(state="visible")
    page.locator("#editorSuitePreviewOverlay .is-art").wait_for(state="visible")
    page.locator('[data-editor-tool="pip"]').click()
    page.locator("#editorPipPanelRoot").wait_for(state="visible")
    page.locator('[data-editor-tool="cut"]').click()
    install_base_media_mutation_probe(page)
    page.locator("#cutPreviewVideo").evaluate(
        """video => {
          video.pause();
          video.currentTime = 0;
          video.dispatchEvent(new Event('seeking'));
          video.dispatchEvent(new Event('timeupdate'));
        }"""
    )
    page.get_by_role("button", name="编辑文字段：保留内容").click()
    assert page.locator("#segmentEditDialog").is_visible()
    page.locator("#segmentEditText").fill("全新文案")

    before = page.evaluate(
        """async playing => {
          const video = document.querySelector('#cutPreviewVideo');
          video.pause();
          video.currentTime = 0.42;
          video.dispatchEvent(new Event('seeking'));
          video.dispatchEvent(new Event('timeupdate'));
          if (playing) await video.play();
          const snapshot = window.EditorSuite.projectSnapshot();
          const times = overlays => overlays.map(item => ({
            start: item.start,
            end: item.end,
            sourceStart: item.sourceStart ?? null,
            sourceEnd: item.sourceEnd ?? null,
          }));
          window.__b0TextEditIdentity = {
            document,
            video,
            artPanel: document.querySelector('#editorArtPanelRoot'),
            pipPanel: document.querySelector('#editorPipPanelRoot'),
          };
          window.__b4TranscriptUpdates = [];
          document.addEventListener('editor-suite:transcript-updated', event => {
            window.__b4TranscriptUpdates.push(event.detail);
          });
          return {
            src: video.currentSrc || video.src,
            currentTime: video.currentTime,
            paused: video.paused,
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            artTimes: times(snapshot.project.art.overlays),
            pipTimes: times(snapshot.project.pip.overlays),
          };
        }""",
        playing,
    )

    page.locator("#saveSegmentTextButton").click()
    page.locator("#segmentStructureStatus").filter(
        has_text="项目预览已同步"
    ).wait_for()

    after = page.evaluate(
        """() => {
          const identity = window.__b0TextEditIdentity;
          const video = document.querySelector('#cutPreviewVideo');
          const snapshot = window.EditorSuite.projectSnapshot();
          const times = overlays => overlays.map(item => ({
            start: item.start,
            end: item.end,
            sourceStart: item.sourceStart ?? null,
            sourceEnd: item.sourceEnd ?? null,
          }));
          const request = window.EditorSuite.compositionRequest();
          return {
            identitySurvived: Boolean(identity),
            sameDocument: identity?.document === document,
            sameVideo: identity?.video === video,
            sameArtPanel:
              identity?.artPanel === document.querySelector('#editorArtPanelRoot'),
            samePipPanel:
              identity?.pipPanel === document.querySelector('#editorPipPanelRoot'),
            iframeCount: document.querySelectorAll('iframe').length,
            src: video.currentSrc || video.src,
            currentTime: video.currentTime,
            paused: video.paused,
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            artTimes: times(snapshot.project.art.overlays),
            pipTimes: times(snapshot.project.pip.overlays),
            artTexts: snapshot.project.art.overlays.map(item => item.text || ''),
            composeArtTexts: request.artOverlays.map(item => item.text || ''),
            transcriptUpdates: window.__b4TranscriptUpdates,
          };
        }"""
    )

    assert after["identitySurvived"] is True
    assert after["sameDocument"] is True
    assert after["sameVideo"] is True
    assert after["sameArtPanel"] is True
    assert after["samePipPanel"] is True
    assert after["iframeCount"] == 0
    assert after["src"] == before["src"]
    assert after["timingRevision"] == before["timingRevision"]
    assert after["revision"] > before["revision"]
    assert after["artTimes"] == before["artTimes"]
    assert after["pipTimes"] == before["pipTimes"]
    assert "全新文案" in after["artTexts"]
    assert "全新文案" in after["composeArtTexts"]
    assert after["transcriptUpdates"] == [{"jobId": seeded_transcript_track_editor_job.job_id}]
    if playing:
        assert after["paused"] is False
        assert after["currentTime"] >= before["currentTime"] - 0.05
    else:
        assert after["paused"] is True
        assert after["currentTime"] == pytest.approx(
            before["currentTime"], abs=0.06
        )
    assert base_media_mutations(page) == {"srcWrites": 0, "loadCalls": 0}


def test_b1_atomic_timeline_transaction_and_narrow_workspace(
    browser_session,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
    page.locator('[data-editor-tool="art"]').click()
    page.locator("#editorArtPanelRoot").wait_for(state="visible")
    page.locator("#editorSuitePreviewOverlay .is-art").wait_for(state="visible")
    page.locator('[data-editor-tool="pip"]').click()
    page.locator("#editorPipPanelRoot").wait_for(state="visible")
    page.locator('[data-editor-tool="cut"]').click()
    install_base_media_mutation_probe(page)

    cut_cancel = page.evaluate(
        """() => {
          const beforeRevision = window.EditorSuite.projectSnapshot().revision;
          const track = document.querySelector('#cutFrameTimelineTrack');
          const bounds = track.getBoundingClientRect();
          const startX = bounds.left + bounds.width * 0.62;
          track.dispatchEvent(new PointerEvent('pointerdown', {
            bubbles: true, button: 0, buttons: 1, clientX: startX,
          }));
          window.dispatchEvent(new PointerEvent('pointermove', {
            bubbles: true, button: 0, buttons: 1, clientX: startX + 28,
          }));
          window.dispatchEvent(new PointerEvent('pointercancel', {
            bubbles: true, button: 0, clientX: startX + 28,
          }));
          return {
            beforeRevision,
            afterRevision: window.EditorSuite.projectSnapshot().revision,
            pendingRanges: document.querySelectorAll(
              '#cutFrameTimelineRanges .cut-timeline-delete-range'
            ).length,
          };
        }"""
    )
    assert cut_cancel == {
        "beforeRevision": cut_cancel["beforeRevision"],
        "afterRevision": cut_cancel["beforeRevision"],
        "pendingRanges": 0,
    }

    page.set_viewport_size({"width": 1912, "height": 948})
    wide_layout = page.evaluate(
        """() => {
          const bounds = selector => document.querySelector(selector)
            .getBoundingClientRect();
          const header = bounds('.header-inner');
          const shell = bounds('.page-shell');
          const result = bounds('#resultCard');
          return {
            viewportWidth: document.documentElement.clientWidth,
            headerLeft: header.left,
            headerRight: header.right,
            shellLeft: shell.left,
            shellRight: shell.right,
            resultLeft: result.left,
            resultRight: result.right,
            horizontalOverflow: document.documentElement.scrollWidth
              > document.documentElement.clientWidth + 1,
          };
        }"""
    )
    assert wide_layout["headerLeft"] == pytest.approx(0, abs=0.75)
    assert wide_layout["headerRight"] == pytest.approx(
        wide_layout["viewportWidth"], abs=0.75
    )
    assert wide_layout["shellLeft"] == pytest.approx(0, abs=0.75)
    assert wide_layout["shellRight"] == pytest.approx(
        wide_layout["viewportWidth"], abs=0.75
    )
    assert wide_layout["resultLeft"] == pytest.approx(0, abs=0.75)
    assert wide_layout["resultRight"] == pytest.approx(
        wide_layout["viewportWidth"], abs=0.75
    )
    assert wide_layout["horizontalOverflow"] is False

    preview_selectors = (
        "#cutVideoStage",
        "#cutPreviewVideo",
        "#editorSuitePreviewOverlay",
        ".editor-suite-preview-canvas",
    )
    preview_geometry = page.evaluate(
        """selectors => Object.fromEntries(selectors.map(selector => {
          const rect = document.querySelector(selector).getBoundingClientRect();
          return [selector, {
            left: rect.left,
            top: rect.top,
            width: rect.width,
            height: rect.height,
          }];
        }))""",
        preview_selectors,
    )
    for tool in ("art", "pip", "cut"):
        page.locator(f'[data-editor-tool="{tool}"]').click()
        current_geometry = page.evaluate(
            """selectors => Object.fromEntries(selectors.map(selector => {
              const rect = document.querySelector(selector).getBoundingClientRect();
              return [selector, {
                left: rect.left,
                top: rect.top,
                width: rect.width,
                height: rect.height,
              }];
            }))""",
            preview_selectors,
        )
        for selector in preview_selectors:
            for dimension in ("left", "top", "width", "height"):
                assert current_geometry[selector][dimension] == pytest.approx(
                    preview_geometry[selector][dimension], abs=0.75
                )

    timeline_geometry = page.evaluate(
        """() => {
          const track = document.querySelector('#cutFrameTimelineTrack');
          const layer = document.querySelector('#editorSuiteTimelineLayer');
          const thumbnails = document.querySelector('#cutFrameTimelineThumbnails');
          const text = document.querySelector('#cutFrameTimelineText');
          const visibleThumb = [...thumbnails.children].find(item => !item.hidden);
          const style = getComputedStyle(track);
          return {
            trackHeight: track.getBoundingClientRect().height,
            layerHeight: layer.getBoundingClientRect().height,
            rulerHeight: Number.parseFloat(
              style.getPropertyValue('--frame-timeline-ruler-height')
            ),
            textHeight: text.getBoundingClientRect().height,
            thumbnailHeight: visibleThumb?.getBoundingClientRect().height || 0,
            layerRows: Number.parseFloat(layer.style.height) / 26,
          };
        }"""
    )
    assert timeline_geometry["rulerHeight"] == pytest.approx(15, abs=0.75)
    assert timeline_geometry["textHeight"] == pytest.approx(26, abs=0.75)
    assert timeline_geometry["layerRows"] >= 1
    assert timeline_geometry["layerRows"] == pytest.approx(
        round(timeline_geometry["layerRows"]), abs=0.01
    )
    assert timeline_geometry["layerHeight"] == pytest.approx(
        timeline_geometry["layerRows"] * 26, abs=0.75
    )
    assert timeline_geometry["trackHeight"] == pytest.approx(
        63 + timeline_geometry["layerRows"] * 26, abs=0.75
    )
    assert timeline_geometry["thumbnailHeight"] > 0

    page.set_viewport_size({"width": 375, "height": 812})
    for tool in ("art", "pip", "cut"):
        page.locator(f'[data-editor-tool="{tool}"]').click()
        overflow = page.evaluate(
            """() => ({
              document: document.documentElement.scrollWidth -
                document.documentElement.clientWidth,
              body: document.body.scrollWidth - document.body.clientWidth,
            })"""
        )
        assert overflow["document"] <= 1
        assert overflow["body"] <= 1

    art_segment = page.locator(
        '#editorSuiteTimelineLayer [data-effect-kind="art"]'
    ).first
    art_segment.wait_for(state="visible")
    assert page.locator(
        '#editorSuiteTimelineLayer [data-effect-kind="cut"]'
    ).count() == 0
    page.locator(
        '#editorSuiteTimelineLayer [data-effect-kind="pip"]'
    ).first.click()
    clip_id = art_segment.get_attribute("data-timeline-clip-id")
    source_id = art_segment.get_attribute("data-source-id")
    assert clip_id
    assert source_id
    before = page.evaluate(
        """({ clipId, sourceId }) => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const overlay = snapshot.project.art.overlays.find(
            item => String(item.id) === sourceId,
          );
          const clip = snapshot.project.timeline.tracks
            .flatMap(track => track.clips)
            .find(item => String(item.id) === clipId);
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            start: overlay.start,
            end: overlay.end,
            clipStart: clip.start,
            clipEnd: clip.end,
            selectedClipId: snapshot.project.timeline.selection?.clipId || null,
          };
        }""",
        {"clipId": clip_id, "sourceId": source_id},
    )
    assert before["selectedClipId"] != clip_id
    page.evaluate(
        """() => {
          window.__b1ProjectActions = [];
          window.EditorSuite.subscribeProject((next, previous, action) => {
            window.__b1ProjectActions.push({
              type: action.type,
              previousRevision: previous.revision,
              previousTimingRevision: previous.timingRevision,
              revision: next.revision,
              timingRevision: next.timingRevision,
            });
          });
        }"""
    )

    def dispatch_drag(finish_event: str) -> None:
        art_segment.evaluate(
            """(segment, finishEvent) => {
              const segmentRect = segment.getBoundingClientRect();
              const track = document.querySelector('#cutFrameTimelineTrack');
              const trackRect = track.getBoundingClientRect();
              const startX = segmentRect.left + segmentRect.width / 2;
              const delta = Math.max(8, Math.min(40, trackRect.width * 0.08));
              segment.dispatchEvent(new PointerEvent('pointerdown', {
                bubbles: true, button: 0, buttons: 1, clientX: startX,
              }));
              window.dispatchEvent(new PointerEvent('pointermove', {
                bubbles: true, button: 0, buttons: 1, clientX: startX + delta,
              }));
              window.dispatchEvent(new PointerEvent(finishEvent, {
                bubbles: true, button: 0, clientX: startX + delta,
              }));
            }""",
            finish_event,
        )

    dispatch_drag("pointercancel")
    after_cancel = page.evaluate(
        """sourceId => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const overlay = snapshot.project.art.overlays.find(
            item => String(item.id) === sourceId,
          );
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            start: overlay.start,
            end: overlay.end,
            actions: window.__b1ProjectActions,
          };
        }""",
        source_id,
    )
    assert after_cancel == {
        "revision": before["revision"],
        "timingRevision": before["timingRevision"],
        "start": before["start"],
        "end": before["end"],
        "actions": [],
    }

    page.evaluate("window.__b1ProjectActions = []")
    dispatch_drag("pointerup")
    committed = page.evaluate(
        """sourceId => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const overlay = snapshot.project.art.overlays.find(
            item => String(item.id) === sourceId,
          );
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            start: overlay.start,
            end: overlay.end,
            actions: window.__b1ProjectActions,
          };
        }""",
        source_id,
    )
    assert len(committed["actions"]) == 1, committed["actions"]
    commit_action = committed["actions"][0]
    assert commit_action["type"] == "timelineClipRangeChanged", commit_action
    assert commit_action["revision"] == commit_action["previousRevision"] + 1
    assert (
        commit_action["timingRevision"]
        == commit_action["previousTimingRevision"] + 1
    )
    assert committed["timingRevision"] == before["timingRevision"] + 1
    assert committed["start"] > before["start"]
    assert committed["end"] > before["end"]
    page.keyboard.press("Control+z")
    page.wait_for_function(
        """({ sourceId, start }) => {
          const overlay = window.EditorSuite.projectSnapshot().project.art.overlays
            .find(item => String(item.id) === sourceId);
          return Math.abs(Number(overlay?.start) - start) < 0.0001;
        }""",
        arg={"sourceId": source_id, "start": before["start"]},
    )
    undone = page.evaluate("window.EditorSuite.projectSnapshot().revision")
    assert undone == committed["revision"] + 1

    page.keyboard.press("Control+Shift+z")
    page.wait_for_function(
        """({ sourceId, start }) => {
          const overlay = window.EditorSuite.projectSnapshot().project.art.overlays
            .find(item => String(item.id) === sourceId);
          return Math.abs(Number(overlay?.start) - start) < 0.0001;
        }""",
        arg={"sourceId": source_id, "start": committed["start"]},
    )
    final = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const expectedComposition = window.EditorProjectStore
            .selectCompositionRequest(snapshot);
          const revisions = [
            document.querySelector('#cutPreviewVideo').dataset.projectRevision,
            document.querySelector('#editorSuitePreviewOverlay').dataset.projectRevision,
            document.querySelector('#editorSuiteTimelineLayer').dataset.projectRevision,
          ].map(Number);
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            revisions,
            request: window.EditorSuite.compositionRequest(),
            expectedComposition,
          };
        }"""
    )
    assert final["revision"] == undone + 1
    assert final["timingRevision"] == committed["timingRevision"] + 2
    assert final["revisions"] == [final["revision"]] * 3
    assert final["request"] == final["expectedComposition"]
    page.locator('[data-editor-tool="art"]').click()
    page.wait_for_function(
        """expected => {
          const input = document.querySelector('[data-art-range="start"]');
          return input && Math.abs(Number(input.value) - expected) < 0.001;
        }""",
        arg=committed["start"],
    )
    assert base_media_mutations(page) == {"srcWrites": 0, "loadCalls": 0}


@pytest.mark.parametrize("route", ("/settings", "/fonts", "/font-manager"))
def test_compact_support_pages_remain_responsive_without_overflow(
    browser_session,
    route,
):
    page = browser_session.page
    for viewport in (
        {"width": 1912, "height": 948},
        {"width": 375, "height": 812},
    ):
        page.set_viewport_size(viewport)
        page.goto(f"{browser_session.base_url}{route}")
        page.locator("#main").wait_for(state="visible")
        geometry = page.evaluate(
            """() => {
              const main = document.querySelector('#main').getBoundingClientRect();
              return {
                mainWidth: main.width,
                viewportWidth: document.documentElement.clientWidth,
                documentOverflow: document.documentElement.scrollWidth
                  - document.documentElement.clientWidth,
                bodyOverflow: document.body.scrollWidth - document.body.clientWidth,
              };
            }"""
        )
        assert geometry["mainWidth"] <= geometry["viewportWidth"] + 1
        assert geometry["documentOverflow"] <= 1
        assert geometry["bodyOverflow"] <= 1


def test_template_deep_link_applies_to_selected_manual_overlay_once(
    browser_session,
    seeded_editor_job,
):
    page = browser_session.page
    install_template_catalog_revision_probe(page)
    page.goto(
        f"{browser_session.base_url}/?job={seeded_editor_job.job_id}"
        "&tool=art&template=neon&templateColor=%2312ab34"
        "&templateStroke=%23abcdef&templateFont=modern&templateSize=72"
    )
    page.locator("#editorArtPanelRoot").wait_for(state="visible")
    page.wait_for_function(
        """() => {
          const overlay = window.EditorSuite.projectSnapshot().project.art.overlays[0];
          return overlay?.artStyle === 'neon' && overlay.fontSize === 72;
        }"""
    )

    result = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            baseline: window.__templateCatalogBaseline,
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            ranges: snapshot.project.art.overlays.map(item => ({
              id: item.id,
              start: item.start,
              end: item.end,
              sourceStart: item.sourceStart ?? null,
              sourceEnd: item.sourceEnd ?? null,
            })),
            overlay: snapshot.project.art.overlays[0],
            iframeCount: document.querySelectorAll('iframe').length,
          };
        }"""
    )
    assert result["revision"] == result["baseline"]["revision"] + 1
    assert result["timingRevision"] == result["baseline"]["timingRevision"]
    assert result["ranges"] == result["baseline"]["ranges"]
    assert result["iframeCount"] == 0
    assert result["overlay"]["artStyle"] == "neon"
    assert result["overlay"]["color"] == "#12AB34"
    assert result["overlay"]["strokeColor"] == "#ABCDEF"
    assert result["overlay"]["font"] == "modern"
    assert result["overlay"]["fontSize"] == 72


def test_template_library_handoff_opens_the_top_level_art_tool(
    browser_session,
    seeded_editor_job,
):
    page = browser_session.page
    page.goto(
        f"{browser_session.base_url}/fonts?job={seeded_editor_job.job_id}"
        "&source=original"
    )
    neon_card = page.locator('[data-template-id="neon"]')
    neon_card.wait_for(state="visible")
    neon_card.get_by_role("button", name="查看", exact=True).click()
    page.locator("#templateFont").select_option("modern")
    page.locator("#templatePreviewSize").fill("70")
    page.locator("#templatePreviewColor").fill("#345678")
    page.locator("#useTemplateButton").click()

    page.locator("#editorArtPanelRoot").wait_for(state="visible")
    page.wait_for_function(
        """() => {
          const overlay = window.EditorSuite.projectSnapshot().project.art.overlays[0];
          return overlay?.artStyle === 'neon' && overlay.fontSize === 70;
        }"""
    )
    result = page.evaluate(
        """() => {
          const query = new URLSearchParams(location.search);
          const overlay = window.EditorSuite.projectSnapshot().project.art.overlays[0];
          return {
            path: location.pathname,
            job: query.get('job'),
            source: query.get('source'),
            tool: query.get('tool'),
            template: query.get('template'),
            templateColor: query.get('templateColor'),
            templateStroke: query.get('templateStroke'),
            templateFont: query.get('templateFont'),
            templateSize: query.get('templateSize'),
            iframeCount: document.querySelectorAll('iframe').length,
            overlay,
          };
        }"""
    )
    assert result["path"] == "/"
    assert result["job"] == seeded_editor_job.job_id
    assert result["source"] == "original"
    assert result["tool"] == "art"
    assert result["template"] == "neon"
    assert result["templateColor"] == "#345678"
    assert result["templateStroke"]
    assert result["templateFont"] == "modern"
    assert result["templateSize"] == "70"
    assert result["iframeCount"] == 0
    assert result["overlay"]["artStyle"] == "neon"
    assert result["overlay"]["color"] == "#345678".upper()
    assert result["overlay"]["font"] == "modern"
    assert result["overlay"]["fontSize"] == 70


def test_template_deep_link_updates_selected_transcript_track_once(
    browser_session,
    seeded_two_cue_transcript_track_editor_job,
):
    job = seeded_two_cue_transcript_track_editor_job
    page = browser_session.page
    install_template_catalog_revision_probe(page)
    page.goto(
        f"{browser_session.base_url}/?job={job.job_id}"
        "&tool=art&template=clean&templateColor=%23224466"
        "&templateStroke=%23ddeeff&templateFont=song&templateSize=66"
    )
    page.locator("#editorArtPanelRoot").wait_for(state="visible")
    page.wait_for_function(
        """() => {
          const overlays = window.EditorSuite.projectSnapshot().project.art.overlays;
          return overlays.length === 2 && overlays.every(item =>
            item.artStyle === 'clean' && item.fontSize === 66
          );
        }"""
    )

    result = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            baseline: window.__templateCatalogBaseline,
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            ranges: snapshot.project.art.overlays.map(item => ({
              id: item.id,
              start: item.start,
              end: item.end,
              sourceStart: item.sourceStart ?? null,
              sourceEnd: item.sourceEnd ?? null,
            })),
            overlays: snapshot.project.art.overlays,
          };
        }"""
    )
    assert result["revision"] == result["baseline"]["revision"] + 1
    assert result["timingRevision"] == result["baseline"]["timingRevision"]
    assert result["ranges"] == result["baseline"]["ranges"]
    assert len(result["overlays"]) == 2
    assert {item["trackId"] for item in result["overlays"]} == {
        "browser-transcript-track"
    }
    for overlay in result["overlays"]:
        assert overlay["artStyle"] == "clean"
        assert overlay["color"] == "#224466"
        assert overlay["strokeColor"] == "#DDEEFF"
        assert overlay["font"] == "song"
        assert overlay["fontSize"] == 66


def test_art_template_dropdown_supports_keyboard_mouse_and_narrow_layout(
    browser_session,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
    page.locator('[data-editor-tool="art"]').click()
    panel = page.locator("#editorArtPanelRoot")
    panel.wait_for(state="visible")
    page.wait_for_load_state("networkidle")

    trigger = panel.locator("[data-art-template-trigger]")
    listbox = panel.locator("[data-art-templates]")
    assert trigger.is_visible()
    assert "热血立体" in trigger.inner_text()
    assert trigger.get_attribute("aria-haspopup") == "listbox"
    assert trigger.get_attribute("aria-expanded") == "false"
    assert listbox.is_hidden()

    trigger.press("Enter")
    assert trigger.get_attribute("aria-expanded") == "true"
    assert listbox.is_visible()
    options = listbox.locator('[role="option"]')
    assert options.count() >= 3
    assert listbox.locator("small, p").count() == 0
    assert options.locator(":scope > .art-style-sample").count() == options.count()
    assert options.locator(":scope > strong").count() == options.count()
    assert "双层描边与厚重投影" not in listbox.inner_text()
    assert page.locator(":focus").get_attribute("data-art-template") == "impact"

    page.locator(":focus").press("ArrowDown")
    assert page.locator(":focus").get_attribute("data-art-template") == "neon"
    page.locator(":focus").press("ArrowUp")
    assert page.locator(":focus").get_attribute("data-art-template") == "impact"
    page.locator(":focus").press("End")
    assert page.locator(":focus").get_attribute("data-art-template") == (
        options.last.get_attribute("data-art-template")
    )
    page.locator(":focus").press("Home")
    assert page.locator(":focus").get_attribute("data-art-template") == "impact"
    page.locator(":focus").press("Escape")
    assert listbox.is_hidden()
    assert trigger.get_attribute("aria-expanded") == "false"
    assert trigger.evaluate("node => document.activeElement === node") is True

    trigger.click()
    assert listbox.is_visible()
    panel.locator("[data-art-detail-title]").click()
    assert listbox.is_hidden()
    assert trigger.get_attribute("aria-expanded") == "false"

    trigger.press("Space")
    page.locator(":focus").press("Tab")
    assert listbox.is_hidden()
    assert listbox.locator(":focus").count() == 0
    assert panel.locator('[data-art-field="text"]').evaluate(
        "node => document.activeElement === node"
    ) is True

    before = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const overlay = snapshot.project.art.overlays[0];
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            range: {
              start: overlay.start,
              end: overlay.end,
              sourceStart: overlay.sourceStart ?? null,
              sourceEnd: overlay.sourceEnd ?? null,
            },
          };
        }"""
    )
    trigger.press("ArrowDown")
    page.locator(":focus").press("ArrowDown")
    assert page.locator(":focus").get_attribute("data-art-template") == "neon"
    page.locator(":focus").press("Enter")
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays[0]
          ?.artStyle === 'neon'"""
    )
    after = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const overlay = snapshot.project.art.overlays[0];
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            range: {
              start: overlay.start,
              end: overlay.end,
              sourceStart: overlay.sourceStart ?? null,
              sourceEnd: overlay.sourceEnd ?? null,
            },
          };
        }"""
    )
    assert after["revision"] == before["revision"] + 1
    assert after["timingRevision"] == before["timingRevision"]
    assert after["range"] == before["range"]
    assert "霓虹发光" in trigger.inner_text()
    assert listbox.is_hidden()

    mouse_revision = after["revision"]
    trigger.click()
    listbox.locator('[data-art-template="clean"]').click()
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays[0]
          ?.artStyle === 'clean'"""
    )
    assert page.evaluate(
        "window.EditorSuite.projectSnapshot().revision"
    ) == mouse_revision + 1
    assert "清爽描边" in trigger.inner_text()

    page.set_viewport_size({"width": 375, "height": 812})
    trigger.click()
    layout = page.evaluate(
        """() => {
          const root = document.querySelector('#editorArtPanelRoot .editor-art-tool');
          const trigger = document.querySelector('[data-art-template-trigger]');
          const option = document.querySelector('[data-art-template]');
          return {
            documentOverflow: document.documentElement.scrollWidth -
              document.documentElement.clientWidth,
            panelOverflow: root.scrollWidth - root.clientWidth,
            triggerWidth: trigger.getBoundingClientRect().width,
            panelWidth: root.getBoundingClientRect().width,
            optionHeight: option.getBoundingClientRect().height,
          };
        }"""
    )
    assert layout["documentOverflow"] <= 0
    assert layout["panelOverflow"] <= 0
    assert layout["triggerWidth"] <= layout["panelWidth"]
    assert layout["optionHeight"] >= 44


def test_art_template_dropdown_updates_transcript_track_once(
    browser_session,
    seeded_two_cue_transcript_track_editor_job,
):
    page = open_editor(browser_session, seeded_two_cue_transcript_track_editor_job)
    page.locator('[data-editor-tool="art"]').click()
    panel = page.locator("#editorArtPanelRoot")
    panel.wait_for(state="visible")
    page.wait_for_load_state("networkidle")

    before = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            cues: snapshot.project.art.overlays.map(item => ({
              id: item.id,
              text: item.text,
              start: item.start,
              end: item.end,
              sourceStart: item.sourceStart ?? null,
              sourceEnd: item.sourceEnd ?? null,
              characterTimings: item.characterTimings,
              timingRevision: item.timingRevision ?? null,
            })),
          };
        }"""
    )
    panel.locator("[data-art-template-trigger]").click()
    panel.locator('[data-art-template="clean"]').click()
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays
          .every(item => item.artStyle === 'clean')"""
    )
    after = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            cues: snapshot.project.art.overlays.map(item => ({
              id: item.id,
              text: item.text,
              start: item.start,
              end: item.end,
              sourceStart: item.sourceStart ?? null,
              sourceEnd: item.sourceEnd ?? null,
              characterTimings: item.characterTimings,
              timingRevision: item.timingRevision ?? null,
            })),
          };
        }"""
    )
    assert after["revision"] == before["revision"] + 1
    assert after["timingRevision"] == before["timingRevision"]
    assert after["cues"] == before["cues"]
    assert "清爽描边" in panel.locator("[data-art-template-trigger]").inner_text()


def test_art_panel_groups_transcript_track_and_updates_shared_settings(
    browser_session,
    seeded_two_cue_transcript_track_editor_job,
):
    job = seeded_two_cue_transcript_track_editor_job
    page = open_editor(browser_session, job)
    page.locator('[data-editor-tool="art"]').click()
    panel = page.locator("#editorArtPanelRoot")
    panel.wait_for(state="visible")

    for text in ("手动标题一", "手动标题二"):
        panel.locator('[data-art-tab="selection"]').click()
        panel.locator("[data-art-add-text]").fill(text)
        panel.locator("[data-art-add]").click()
        assert panel.locator('[data-art-tab="settings"]').get_attribute(
            "aria-selected"
        ) == "true"
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays.length === 4"""
    )

    panel.locator('[data-art-tab="selection"]').click()
    track_button = panel.locator(
        '[data-art-track-select="browser-transcript-track"]'
    )
    assert track_button.count() == 1
    assert "视频文案艺术字" in track_button.inner_text()
    assert "2 段 · 0.05s - 0.85s" in track_button.inner_text()
    assert panel.locator("[data-art-list] [data-art-select]").count() == 2
    assert panel.locator("[data-art-list] .overlay-list-item").count() == 3

    page.locator("#cutPreviewVideo").evaluate(
        """video => {
          video.currentTime = 0.1;
          video.dispatchEvent(new Event('timeupdate'));
        }"""
    )
    track_button.click()
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.timeline.selection?.clipId
          === 'art:browser-transcript-cue-1'"""
    )
    assert panel.locator(
        "[data-art-list] .overlay-list-item.is-selected"
    ).count() == 1
    assert track_button.get_attribute("aria-pressed") == "true"
    assert panel.locator("[data-art-detail-title]").inner_text() == (
        "视频文案艺术字整轨设置"
    )
    assert panel.locator("[data-art-detail-help]").inner_text() == (
        "统一修改整轨文案艺术字"
    )
    assert panel.locator("[data-art-delete]").inner_text() == (
        "删除视频文案艺术字"
    )
    assert panel.locator("[data-art-manual-only]:visible").count() == 0
    assert panel.locator('[data-art-field="fontSize"]').is_visible()
    assert panel.locator('[data-art-coordinate="x"]').is_visible()

    page.locator("#cutPreviewVideo").evaluate(
        """video => {
          video.currentTime = 0.6;
          video.dispatchEvent(new Event('timeupdate'));
        }"""
    )
    assert page.evaluate(
        """() => window.EditorSuite.projectSnapshot().project.timeline.selection?.clipId"""
    ) == "art:browser-transcript-cue-1"

    before = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const invariant = item => ({
            id: item.id,
            text: item.text,
            start: item.start,
            end: item.end,
            sourceStart: item.sourceStart ?? null,
            sourceEnd: item.sourceEnd ?? null,
            characterTimings: item.characterTimings,
            timingRevision: item.timingRevision ?? null,
          });
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            transcript: snapshot.project.art.overlays
              .filter(item => item.trackType === 'transcript')
              .map(invariant),
            manual: snapshot.project.art.overlays
              .filter(item => item.trackType !== 'transcript')
              .map(item => ({ id: item.id, fontSize: item.fontSize })),
          };
        }"""
    )
    font_size = panel.locator('[data-art-field="fontSize"]')
    font_size.fill("68")
    font_size.press("Tab")
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays
          .filter(item => item.trackType === 'transcript')
          .every(item => item.fontSize === 68)"""
    )
    after = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const frame = window.EditorProjectStore.selectEditorFrame(snapshot);
          const invariant = item => ({
            id: item.id,
            text: item.text,
            start: item.start,
            end: item.end,
            sourceStart: item.sourceStart ?? null,
            sourceEnd: item.sourceEnd ?? null,
            characterTimings: item.characterTimings,
            timingRevision: item.timingRevision ?? null,
          });
          const transcript = snapshot.project.art.overlays
            .filter(item => item.trackType === 'transcript');
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            transcript: transcript.map(invariant),
            manual: snapshot.project.art.overlays
              .filter(item => item.trackType !== 'transcript')
              .map(item => ({ id: item.id, fontSize: item.fontSize })),
            selection: snapshot.project.timeline.selection?.clipId || null,
            timelineTracks: frame.timeline.tracks
              .filter(track => track.id === 'art:transcript:browser-transcript-track')
              .map(track => track.clips.map(clip => clip.sourceId)),
            previewIds: frame.preview.art.overlays
              .filter(item => item.trackType === 'transcript')
              .map(item => item.id),
            previewCues: frame.preview.art.overlays
              .filter(item => item.trackType === 'transcript')
              .map(item => ({ text: item.text, start: item.start, end: item.end })),
            compositionCues: frame.composition.artOverlays
              .filter(item => item.trackId === 'browser-transcript-track')
              .map(item => ({ text: item.text, start: item.start, end: item.end })),
          };
        }"""
    )
    assert after["revision"] == before["revision"] + 1
    assert after["timingRevision"] == before["timingRevision"]
    assert after["transcript"] == before["transcript"]
    assert after["manual"] == before["manual"]
    assert after["selection"] == "art:browser-transcript-cue-1"
    assert after["timelineTracks"] == [
        ["browser-transcript-cue-1", "browser-transcript-cue-2"]
    ]
    assert sorted(after["previewIds"]) == [
        "browser-transcript-cue-1",
        "browser-transcript-cue-2",
    ]
    assert after["previewCues"] == after["compositionCues"]
    assert track_button.get_attribute("aria-pressed") == "true"

    page.set_viewport_size({"width": 375, "height": 812})
    panel.locator('[data-art-tab="selection"]').click()
    layout = page.evaluate(
        """() => {
          const root = document.querySelector('#editorArtPanelRoot .editor-art-tool');
          const track = document.querySelector('[data-art-track-select]');
          return {
            documentOverflow: document.documentElement.scrollWidth
              - document.documentElement.clientWidth,
            panelOverflow: root.scrollWidth - root.clientWidth,
            trackHeight: track.getBoundingClientRect().height,
          };
        }"""
    )
    assert layout["documentOverflow"] <= 0
    assert layout["panelOverflow"] <= 0
    assert layout["trackHeight"] >= 44

    manual_button = panel.locator("[data-art-list] [data-art-select]").first
    manual_button.click()
    assert panel.locator("[data-art-manual-only]:visible").count() == 7
    assert panel.locator("[data-art-detail-title]").inner_text() == "详细设置"
    assert panel.locator("[data-art-delete]").inner_text() == "删除当前艺术字"

    panel.locator('[data-art-tab="selection"]').click()
    track_button.click()
    panel.locator("[data-art-delete]").click()
    assert page.locator("#appDialogTitle").inner_text() == "删除视频文案艺术字？"
    page.locator("#appDialogConfirm").click()
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays
          .every(item => item.trackType !== 'transcript')"""
    )
    removed = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const frame = window.EditorProjectStore.selectEditorFrame(snapshot);
          return {
            overlayCount: snapshot.project.art.overlays.length,
            trackButtons: document.querySelectorAll('[data-art-track-select]').length,
            timeline: frame.timeline.tracks.filter(track =>
              track.id === 'art:transcript:browser-transcript-track'
            ).length,
            preview: frame.preview.art.overlays.filter(item =>
              item.trackType === 'transcript'
            ).length,
            composition: frame.composition.artOverlays.filter(item =>
              item.trackType === 'transcript'
            ).length,
          };
        }"""
    )
    assert removed == {
        "overlayCount": 2,
        "trackButtons": 0,
        "timeline": 0,
        "preview": 0,
        "composition": 0,
    }


def test_manual_and_transcript_art_each_use_one_distinct_timeline_row(
    browser_session,
    seeded_two_cue_transcript_track_editor_job,
):
    page = open_editor(browser_session, seeded_two_cue_transcript_track_editor_job)
    page.locator('[data-editor-tool="art"]').click()
    panel = page.locator("#editorArtPanelRoot")
    panel.wait_for(state="visible")

    for text in ("手动标题一", "手动标题二"):
        panel.locator('[data-art-tab="selection"]').click()
        panel.locator("[data-art-add-text]").fill(text)
        panel.locator("[data-art-add]").click()
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays.length === 4"""
    )

    layout = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const frame = window.EditorProjectStore.selectEditorFrame(snapshot);
          const manualIds = snapshot.project.art.overlays
            .filter(item => item.trackType !== 'transcript')
            .map(item => String(item.id));
          const manualIdSet = new Set(manualIds);
          const invariant = item => ({
            text: item.text,
            start: item.start,
            end: item.end,
            sourceStart: item.sourceStart ?? null,
            sourceEnd: item.sourceEnd ?? null,
          });
          const manualSegments = [...document.querySelectorAll(
            '#editorSuiteTimelineLayer [data-effect-kind="art"]'
          )].filter(item => manualIdSet.has(String(item.dataset.sourceId)));
          const transcriptSegments = [...document.querySelectorAll(
            '#editorSuiteTimelineLayer [data-effect-kind="art"]'
          )].filter(item => !manualIdSet.has(String(item.dataset.sourceId)));
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            manualIds,
            artTracks: frame.timeline.tracks
              .filter(track => track.kind === 'art')
              .map(track => ({
                id: track.id,
                name: track.name,
                sourceIds: track.clips.map(clip => clip.sourceId),
              })),
            manualSegments: manualSegments.map(item => {
              const rect = item.getBoundingClientRect();
              return {
                sourceId: item.dataset.sourceId,
                trackIndex: item.dataset.timelineTrackIndex,
                laneIndex: item.dataset.timelineLaneIndex,
                tabIndex: item.tabIndex,
                top: rect.top,
                bottom: rect.bottom,
              };
            }),
            transcriptSegments: transcriptSegments.map(item => ({
              sourceId: item.dataset.sourceId,
              trackIndex: item.dataset.timelineTrackIndex,
              laneIndex: item.dataset.timelineLaneIndex,
            })),
            overlays: snapshot.project.art.overlays.map(invariant),
            preview: frame.preview.art.overlays.map(invariant),
            composition: frame.composition.artOverlays.map(invariant),
          };
        }"""
    )

    assert [(track["id"], track["name"]) for track in layout["artTracks"]] == [
        ("art:transcript:browser-transcript-track", "视频文案艺术字"),
        ("art:manual", "手动艺术字"),
    ]
    assert layout["artTracks"][0]["sourceIds"] == [
        "browser-transcript-cue-1",
        "browser-transcript-cue-2",
    ]
    assert layout["artTracks"][1]["sourceIds"] == layout["manualIds"]
    assert layout["preview"] == layout["overlays"]
    assert layout["composition"] == layout["overlays"]
    assert len(layout["manualSegments"]) == 2
    assert len({item["trackIndex"] for item in layout["manualSegments"]}) == 1
    assert {item["laneIndex"] for item in layout["manualSegments"]} == {"0"}
    assert all(item["tabIndex"] >= 0 for item in layout["manualSegments"])
    first_segment, second_segment = layout["manualSegments"]
    assert first_segment["top"] == pytest.approx(second_segment["top"], abs=1)
    assert first_segment["bottom"] == pytest.approx(second_segment["bottom"], abs=1)
    assert {item["laneIndex"] for item in layout["transcriptSegments"]} == {"0"}
    assert len({item["trackIndex"] for item in layout["transcriptSegments"]}) == 1
    assert layout["transcriptSegments"][0]["trackIndex"] != (
        layout["manualSegments"][0]["trackIndex"]
    )
    for manual_id in layout["manualIds"]:
        panel.locator('[data-art-tab="selection"]').click()
        panel.locator(f'[data-art-select="{manual_id}"]').click()
        page.wait_for_function(
            """id => window.EditorSuite.projectSnapshot().project.timeline.selection
              ?.clipId === `art:${id}`""",
            arg=manual_id,
        )

    def click_clip_and_assert_playhead(segment, clip_id: str, ratio: float) -> None:
        geometry = segment.evaluate(
            """(item, ratio) => {
              const itemRect = item.getBoundingClientRect();
              const track = document.querySelector('#cutFrameTimelineTrack');
              const trackRect = track.getBoundingClientRect();
              const frame = window.EditorProjectStore.selectEditorFrame(
                window.EditorSuite.projectSnapshot()
              );
              const relativeX = itemRect.width * ratio;
              const clientX = itemRect.left + relativeX;
              return {
                relativeX,
                relativeY: itemRect.height / 2,
                clientX,
                expectedTime: Math.min(1, Math.max(
                  0,
                  (clientX - trackRect.left) / trackRect.width,
                )) * frame.timeline.duration,
                clipStart: Number(item.dataset.effectStart),
              };
            }""",
            ratio,
        )
        assert geometry["expectedTime"] - geometry["clipStart"] > 0.1
        segment.click(
            position={"x": geometry["relativeX"], "y": geometry["relativeY"]}
        )
        page.wait_for_function(
            """({ clipId, expectedTime, clientX }) => {
              const video = document.querySelector('#cutPreviewVideo');
              const playhead = document.querySelector('#cutFrameTimelinePlayhead');
              const playheadRect = playhead.getBoundingClientRect();
              const selection = window.EditorSuite.projectSnapshot()
                .project.timeline.selection?.clipId;
              return selection === clipId
                && Math.abs(video.currentTime - expectedTime) <= 0.06
                && Math.abs(playheadRect.left + playheadRect.width / 2 - clientX) <= 3;
            }""",
            arg={
                "clipId": clip_id,
                "expectedTime": geometry["expectedTime"],
                "clientX": geometry["clientX"],
            },
        )

    selected_id = layout["manualIds"][0]
    manual_segment = page.locator(
        f'#editorSuiteTimelineLayer [data-source-id="{selected_id}"]'
    )
    panel.locator('[data-art-tab="selection"]').click()
    panel.locator(f'[data-art-select="{selected_id}"]').click()
    click_clip_and_assert_playhead(manual_segment, f"art:{selected_id}", 0.68)
    transcript_segment = page.locator(
        '#editorSuiteTimelineLayer [data-source-id="browser-transcript-cue-2"]'
    )
    click_clip_and_assert_playhead(
        transcript_segment,
        "art:browser-transcript-cue-2",
        0.65,
    )
    panel.locator('[data-art-tab="selection"]').click()
    panel.locator(f'[data-art-select="{selected_id}"]').click()
    page.wait_for_function(
        """id => window.EditorSuite.projectSnapshot().project.timeline.selection?.clipId
          === `art:${id}`""",
        arg=selected_id,
    )
    before_change = page.evaluate(
        """ids => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            ranges: ids.map(id => {
              const item = snapshot.project.art.overlays.find(
                overlay => String(overlay.id) === id
              );
              return { id, start: item.start, end: item.end };
            }),
          };
        }""",
        layout["manualIds"],
    )
    panel.locator('[data-art-range="start"]').fill("0.12")
    panel.locator('[data-art-range="start"]').press("Tab")
    page.wait_for_function(
        """id => {
          const item = window.EditorSuite.projectSnapshot().project.art.overlays
            .find(overlay => String(overlay.id) === id);
          return Math.abs(Number(item?.start) - 0.12) < 0.001;
        }""",
        arg=selected_id,
    )
    after_change = page.evaluate(
        """ids => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            ranges: ids.map(id => {
              const item = snapshot.project.art.overlays.find(
                overlay => String(overlay.id) === id
              );
              return { id, start: item.start, end: item.end };
            }),
          };
        }""",
        layout["manualIds"],
    )
    assert after_change["revision"] == before_change["revision"] + 1
    assert after_change["timingRevision"] == before_change["timingRevision"] + 1
    assert after_change["ranges"][0]["start"] == pytest.approx(0.12)
    assert after_change["ranges"][0]["end"] == before_change["ranges"][0]["end"]
    assert after_change["ranges"][1] == before_change["ranges"][1]

    panel.locator("[data-art-delete]").click()
    page.locator("#appDialogConfirm").click()
    page.wait_for_function(
        """id => !window.EditorSuite.projectSnapshot().project.art.overlays
          .some(item => String(item.id) === id)""",
        arg=selected_id,
    )
    remaining = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          const frame = window.EditorProjectStore.selectEditorFrame(snapshot);
          const manual = snapshot.project.art.overlays.filter(
            item => item.trackType !== 'transcript'
          );
          const transcript = snapshot.project.art.overlays.filter(
            item => item.trackType === 'transcript'
          );
          return {
            manualIds: manual.map(item => item.id),
            transcriptIds: transcript.map(item => item.id),
            manualTracks: frame.timeline.tracks
              .filter(track => track.id === 'art:manual')
              .map(track => track.clips.map(clip => clip.sourceId)),
            transcriptTracks: frame.timeline.tracks
              .filter(track => track.id === 'art:transcript:browser-transcript-track')
              .map(track => track.clips.map(clip => clip.sourceId)),
            previewTexts: frame.preview.art.overlays.map(item => item.text),
            compositionTexts: frame.composition.artOverlays.map(item => item.text),
          };
        }"""
    )
    assert remaining["manualIds"] == [layout["manualIds"][1]]
    assert remaining["transcriptIds"] == [
        "browser-transcript-cue-2",
        "browser-transcript-cue-1",
    ]
    assert remaining["manualTracks"] == [[layout["manualIds"][1]]]
    assert remaining["transcriptTracks"] == [[
        "browser-transcript-cue-1",
        "browser-transcript-cue-2",
    ]]
    assert remaining["previewTexts"] == remaining["compositionTexts"]
    assert "手动标题一" not in remaining["previewTexts"]
    assert "手动标题二" in remaining["previewTexts"]


def test_deleting_only_transcript_track_resets_empty_selection_copy(
    browser_session,
    seeded_two_cue_transcript_track_editor_job,
):
    page = open_editor(browser_session, seeded_two_cue_transcript_track_editor_job)
    page.locator('[data-editor-tool="art"]').click()
    panel = page.locator("#editorArtPanelRoot")
    panel.wait_for(state="visible")

    panel.locator('[data-art-tab="selection"]').click()
    panel.locator('[data-art-track-select="browser-transcript-track"]').click()
    panel.locator("[data-art-delete]").click()
    page.locator("#appDialogConfirm").click()
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays.length === 0"""
    )

    assert panel.locator("[data-art-track-select]").count() == 0
    assert panel.locator('[data-art-tab="selection"]').get_attribute(
        "aria-selected"
    ) == "true"
    assert panel.locator('[data-art-panel="selection"]').is_visible()
    assert panel.locator('[data-art-panel="settings"]').is_hidden()
    panel.locator('[data-art-tab="settings"]').click()
    assert panel.locator("[data-art-selection-empty]").is_visible()
    assert panel.locator("[data-art-controls]").is_hidden()
    assert panel.locator("[data-art-detail-title]").inner_text() == "详细设置"
    assert panel.locator("[data-art-detail-help]").inner_text() == (
        "修改当前选中的艺术字"
    )
    assert panel.locator("[data-art-controls-legend]").inner_text() == (
        "当前艺术字设置"
    )


def test_template_preference_applies_to_new_manual_and_full_track_without_selection(
    browser_session,
    seeded_editor_job_without_art,
):
    job = seeded_editor_job_without_art
    page = browser_session.page
    install_template_catalog_revision_probe(page)
    page.goto(
        f"{browser_session.base_url}/?job={job.job_id}"
        "&tool=art&template=neon&templateColor=%2313579b"
        "&templateStroke=%232468ac&templateFont=kai&templateSize=64"
    )
    panel = page.locator("#editorArtPanelRoot")
    panel.wait_for(state="visible")
    page.wait_for_load_state("networkidle")
    assert panel.locator('[data-art-tab="selection"]').get_attribute(
        "aria-selected"
    ) == "true"
    assert panel.locator('[data-art-panel="selection"]').is_visible()

    preferred_only = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            baseline: window.__templateCatalogBaseline,
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            selection: snapshot.project.timeline.selection,
            overlayCount: snapshot.project.art.overlays.length,
          };
        }"""
    )
    assert preferred_only["overlayCount"] == 0
    assert preferred_only["selection"] is None
    assert preferred_only["revision"] == preferred_only["baseline"]["revision"]
    assert preferred_only["timingRevision"] == preferred_only["baseline"]["timingRevision"]

    panel.locator("[data-art-add-text]").fill("使用首选模板")
    panel.locator("[data-art-add]").click()
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays[0]
          ?.artStyle === 'neon'"""
    )
    assert panel.locator('[data-art-tab="settings"]').get_attribute(
        "aria-selected"
    ) == "true"
    manual = page.evaluate(
        "window.EditorSuite.projectSnapshot().project.art.overlays[0]"
    )
    assert manual["color"] == "#13579B"
    assert manual["strokeColor"] == "#2468AC"
    assert manual["font"] == "kai"
    assert manual["fontSize"] == 64

    panel.locator("[data-art-delete]").click()
    page.locator("#appDialogConfirm").click()
    page.wait_for_function(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return snapshot.project.art.overlays.length === 0 &&
            snapshot.project.timeline.selection === null;
        }"""
    )
    assert panel.locator('[data-art-tab="selection"]').get_attribute(
        "aria-selected"
    ) == "true"
    assert panel.locator("[data-art-controls]").is_hidden()
    panel.locator("[data-art-full-track]").click()
    page.wait_for_function(
        """() => {
          const overlays = window.EditorSuite.projectSnapshot().project.art.overlays;
          return overlays.length === 2 && overlays.every(item =>
            item.trackType === 'transcript' && item.artStyle === 'neon'
          );
        }"""
    )
    assert panel.locator('[data-art-tab="settings"]').get_attribute(
        "aria-selected"
    ) == "true"
    track = page.evaluate(
        "window.EditorSuite.projectSnapshot().project.art.overlays"
    )
    for overlay in track:
        assert overlay["color"] == "#13579B"
        assert overlay["strokeColor"] == "#2468AC"
        assert overlay["font"] == "kai"
        assert overlay["fontSize"] == 64


def test_invalid_template_handoff_values_fall_back_safely(
    browser_session,
    seeded_editor_job_without_art,
):
    job = seeded_editor_job_without_art
    page = browser_session.page
    install_template_catalog_revision_probe(page)
    page.goto(
        f"{browser_session.base_url}/?job={job.job_id}"
        "&tool=art&template=neon&templateColor=invalid"
        "&templateStroke=%23xyzxyz&templateFont=missing-font"
    )
    panel = page.locator("#editorArtPanelRoot")
    panel.wait_for(state="visible")
    page.wait_for_load_state("networkidle")
    assert page.evaluate(
        "window.EditorSuite.parseRequestedArtTemplate('?template=neon').fontSize"
    ) is None

    panel.locator("[data-art-add-text]").fill("安全回退")
    panel.locator("[data-art-add]").click()
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays.length === 1"""
    )
    result = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            baseline: window.__templateCatalogBaseline,
            overlay: snapshot.project.art.overlays[0],
          };
        }"""
    )
    catalog = page.request.get(
        f"{browser_session.base_url}/api/art-templates"
    ).json()
    neon = next(item for item in catalog["templates"] if item["id"] == "neon")
    assert result["overlay"]["artStyle"] == "neon"
    assert result["overlay"]["color"] == neon["color"].upper()
    assert result["overlay"]["strokeColor"] == neon["strokeColor"].upper()
    assert result["overlay"]["font"] == "bold"
    assert result["overlay"]["fontSize"] == 54


def test_unknown_template_handoff_is_ignored(
    browser_session,
    seeded_editor_job_without_art,
):
    job = seeded_editor_job_without_art
    page = browser_session.page
    install_template_catalog_revision_probe(page)
    page.goto(
        f"{browser_session.base_url}/?job={job.job_id}"
        "&tool=art&template=missing-template&templateSize=180"
    )
    panel = page.locator("#editorArtPanelRoot")
    panel.wait_for(state="visible")
    page.wait_for_load_state("networkidle")
    before_add = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            baseline: window.__templateCatalogBaseline,
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
          };
        }"""
    )
    assert before_add["revision"] == before_add["baseline"]["revision"]
    assert before_add["timingRevision"] == before_add["baseline"]["timingRevision"]

    panel.locator("[data-art-add-text]").fill("默认模板")
    panel.locator("[data-art-add]").click()
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays.length === 1"""
    )
    overlay = page.evaluate(
        "window.EditorSuite.projectSnapshot().project.art.overlays[0]"
    )
    assert overlay["artStyle"] == "impact"
    assert overlay["fontSize"] == 54


def test_legacy_art_url_redirects_to_narrow_single_page_runtime(
    browser_session,
    seeded_editor_job,
):
    page = browser_session.page
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto(
        f"{browser_session.base_url}/art-text"
        f"?job={seeded_editor_job.job_id}&source=original&embedded=1&tool=pip"
    )
    page.locator("#editorArtPanelRoot").wait_for(state="visible")
    page.wait_for_function("() => window.EditorSuite?.activeTool() === 'art'")

    result = page.evaluate(
        """() => ({
          path: location.pathname,
          job: new URLSearchParams(location.search).get('job'),
          source: new URLSearchParams(location.search).get('source'),
          tool: new URLSearchParams(location.search).get('tool'),
          hasEmbedded: new URLSearchParams(location.search).has('embedded'),
          iframeCount: document.querySelectorAll('iframe').length,
          videoCount: document.querySelectorAll('#cutPreviewVideo').length,
          legacyWorkspaceCount: document.querySelectorAll('#artWorkspace').length,
          artInert: document.querySelector('#editorArtPanelRoot').inert,
          pipInert: document.querySelector('#editorPipPanelRoot').inert,
          cutInert: document.querySelector('.text-editor-panel-stack').inert,
          overflow: document.documentElement.scrollWidth -
            document.documentElement.clientWidth,
          artTabs: [...document.querySelectorAll('#editorArtPanelRoot [data-art-tab]')]
            .map(tab => tab.textContent.trim()),
          transcriptInSettings: Boolean(document.querySelector(
            '#editorArtPanelRoot [data-art-panel="settings"] [data-art-transcript-section]'
          )),
          transcriptInSelection: Boolean(document.querySelector(
            '#editorArtPanelRoot [data-art-panel="selection"] [data-art-transcript-section]'
          )),
        })"""
    )
    assert result == {
        "path": "/",
        "job": seeded_editor_job.job_id,
        "source": "original",
        "tool": "art",
        "hasEmbedded": False,
        "iframeCount": 0,
        "videoCount": 1,
        "legacyWorkspaceCount": 0,
        "artInert": False,
        "pipInert": True,
        "cutInert": True,
        "overflow": 0,
        "artTabs": ["选择艺术字", "艺术字设置", "AI 推荐"],
        "transcriptInSettings": False,
        "transcriptInSelection": True,
    }


def test_job_url_remains_editable_after_service_restart(
    browser_session,
    browser_server,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
    editor_url = page.url
    original_text = page.locator("#segmentList").inner_text()

    page.goto("about:blank")
    browser_server.restart_without_memory_state()
    recovery_response = page.request.get(
        f"{browser_session.base_url}/api/transcriptions/{seeded_editor_job.job_id}"
    )
    assert recovery_response.ok
    page.goto(editor_url)

    page.locator("#resultCard").wait_for(state="visible", timeout=2000)
    assert page.locator("#segmentList").inner_text() == original_text
    assert page.locator('[data-editor-tool="art"]').get_attribute(
        "aria-disabled"
    ) == "false"


def test_running_job_restores_as_interrupted_without_endless_polling(
    browser_session,
    browser_server,
    seeded_editor_job,
):
    with app_module.JOBS_LOCK:
        job = app_module.JOBS[seeded_editor_job.job_id]
        job.update(
            status="transcribing",
            attemptId="browser-interrupted-attempt",
            stage="正在识别文字",
            progress=55,
            result=None,
            error=None,
            updatedAt=app_module.utc_now(),
        )
    app_module.persist_job_snapshot(seeded_editor_job.job_id, raise_on_error=True)

    browser_server.restart_without_memory_state()
    page = browser_session.page
    recovery_response = page.request.get(
        f"{browser_session.base_url}/api/transcriptions/{seeded_editor_job.job_id}"
    )
    assert recovery_response.ok
    page.goto(
        f"{browser_session.base_url}/?job={seeded_editor_job.job_id}"
    )
    page.locator("#jobError").wait_for(state="visible")

    assert page.locator("#liveStatus").inner_text() == "处理已中断，可重试"
    assert page.locator("#retryButton").inner_text() == "重试处理"
    assert page.locator("#reselectVideoButton").inner_text() == "重新选择视频"
    assert page.locator("#retryButton").is_enabled()
    page.wait_for_timeout(1400)
    assert page.locator("#jobError").is_visible()

    queued_payload = recovery_response.json()
    queued_payload.update(
        status="queued",
        stage="重试任务已创建",
        progress=10,
        error=None,
    )
    page.evaluate(
        """
        payload => {
          const originalFetch = window.fetch.bind(window);
          window.fetch = (input, init) => {
            const url = String(input || '');
            if (url.endsWith('/retry')) {
              return new Promise(resolve => {
                window.__resolveDelayedRetry = () => resolve(new Response(
                  JSON.stringify(payload),
                  {status: 202, headers: {'Content-Type': 'application/json'}},
                ));
              });
            }
            return originalFetch(input, init);
          };
        }
        """,
        queued_payload,
    )
    page.locator("#retryButton").click()
    page.wait_for_function("() => typeof window.__resolveDelayedRetry === 'function'")
    page.locator("#reselectVideoButton").click()
    page.evaluate("window.__resolveDelayedRetry()")
    page.wait_for_timeout(100)

    assert page.locator("#uploadCard").is_visible()
    assert page.locator("#progressCard").is_hidden()
    assert page.locator("#resultCard").is_hidden()
