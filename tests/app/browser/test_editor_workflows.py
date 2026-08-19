from __future__ import annotations

import re

import pytest


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
    pip_frame = page.frame_locator('iframe[title="画中画设置"]')
    pip_frame.locator("#pipWorkspace").wait_for(state="visible")
    preview_button = pip_frame.get_by_role(
        "button",
        name="在视频中预览：保留内容",
    )
    preview_button.click()
    selected_card = pip_frame.locator(
        f'.pip-generated-card[data-picture-id="{seeded_editor_job.pip_asset_id}"]'
    )
    assert "is-selected" in (selected_card.get_attribute("class") or "")
    assert page.locator('[data-editor-suite-panel="pip"]').get_attribute(
        "aria-hidden"
    ) == "false"
    page.locator("#editorSuitePreviewOverlay .is-pip").wait_for(state="visible")
    assert art_panel.evaluate("panel => panel.inert") is True
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
    page.locator('[data-editor-tool="pip"]').click()
    wait_for_preview_time(page, selected_time)

    assert page.title() == original_title
    assert "is-selected" in (selected_art.get_attribute("class") or "")
    assert "is-selected" in (selected_card.get_attribute("class") or "")
    current_time = page.locator("#cutPreviewVideo").evaluate(
        "video => video.currentTime"
    )
    assert current_time == pytest.approx(selected_time, abs=0.06)
    assert page.locator("#editorSuitePreviewOverlay .is-art").count() == 1
    assert page.locator("#editorSuitePreviewOverlay .is-pip").count() == 1
    assert "tool=pip" in page.url
    assert base_media_mutations(page) == {"srcWrites": 0, "loadCalls": 0}


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
    assert after_range["draft"]["schemaVersion"] == 1
    assert after_range["draft"]["jobId"] == seeded_editor_job.job_id
    assert after_range["draft"]["art"]["overlays"][0]["id"] == before["id"]

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
    panel.locator('[data-art-tab="transcript"]').click()
    with page.expect_response(track_url) as track_response:
        panel.locator("[data-art-full-track]").click()
    assert track_response.value.status == 200
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays
          .filter(item => item.trackType === 'transcript').length === 2"""
    )
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
    panel.locator('[data-art-tab="transcript"]').click()
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
    panel.locator("[data-art-full-track]").click()
    page.wait_for_function("() => window.__b2LateTrackRequests.length === 1")
    page.locator('[data-editor-tool="pip"]').click()
    page.locator('[data-editor-tool="art"]').click()
    panel.wait_for(state="visible")
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


def test_top_level_art_deactivation_aborts_transcript_save(
    browser_session,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
    page.locator('[data-editor-tool="art"]').click()
    panel = page.locator("#editorArtPanelRoot")
    panel.wait_for(state="visible")
    panel.locator('[data-art-tab="transcript"]').click()
    before_revision = page.evaluate(
        "window.EditorSuite.projectSnapshot().revision"
    )
    page.evaluate(
        """() => {
          const originalFetch = window.fetch.bind(window);
          window.__b2TranscriptSave = { requested: false, aborted: false };
          window.__b2TranscriptActions = [];
          window.EditorSuite.subscribeProject((next, previous, action) => {
            window.__b2TranscriptActions.push(action.type);
          });
          window.fetch = (input, options = {}) => {
            const url = String(input?.url || input || '');
            if (url.endsWith('/transcript') && options.method === 'PUT') {
              window.__b2TranscriptSave.requested = true;
              return new Promise((resolve, reject) => {
                const abort = () => {
                  window.__b2TranscriptSave.aborted = true;
                  reject(new DOMException('Aborted', 'AbortError'));
                };
                if (options.signal?.aborted) abort();
                else options.signal?.addEventListener('abort', abort, { once: true });
              });
            }
            return originalFetch(input, options);
          };
        }"""
    )
    panel.locator("[data-art-transcript-text]").fill("取消中的文案保存")
    panel.locator("[data-art-transcript-save]").click()
    page.wait_for_function("window.__b2TranscriptSave.requested === true")

    page.locator('[data-editor-tool="pip"]').click()
    page.wait_for_function("window.__b2TranscriptSave.aborted === true")
    after = page.evaluate(
        """() => ({
          snapshot: window.EditorSuite.projectSnapshot(),
          actions: window.__b2TranscriptActions,
        })"""
    )
    assert after["snapshot"]["revision"] == before_revision + 1
    assert after["snapshot"]["project"]["art"]["overlays"][0]["text"] == (
        "保留内容"
    )
    assert after["actions"] == ["activeToolChanged"]
    assert panel.evaluate("panel => panel.inert") is True


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
            body='{"id":"b1-version","name":"B1 测试版本"}',
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
    pip_frame = page.frame_locator('iframe[title="画中画设置"]')
    pip_frame.locator("#pipWorkspace").wait_for(state="visible")
    pip_frame.get_by_role(
        "button",
        name="在视频中预览：保留内容",
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
    expected_pip_start = float(pip_frame.locator("#pipStartTime").input_value())
    expected_pip_end = float(pip_frame.locator("#pipEndTime").input_value())
    assert payload["target"] == "all"
    assert payload["ranges"] == [
        {
            "start": draft["textRanges"][0]["start"],
            "end": draft["textRanges"][0]["end"],
        }
    ]
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
        expected_pip_start,
        abs=0.001,
    )
    assert payload["pictureInPictureOverlays"][0]["end"] == pytest.approx(
        expected_pip_end,
        abs=0.001,
    )
    assert payload["historyName"] is None


@pytest.mark.parametrize("playing", [False, True], ids=["paused", "playing"])
def test_text_edit_preserves_media_iframes_and_effect_timing(
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
    pip_frame = page.frame_locator('iframe[title="画中画设置"]')
    pip_frame.locator("#pipWorkspace").wait_for(state="visible")
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
            video,
            artPanel: document.querySelector('#editorArtPanelRoot'),
                pipFrame: document.querySelector('iframe[title="画中画设置"]'),
              };
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
            sameVideo: identity?.video === video,
            sameArtPanel:
              identity?.artPanel === document.querySelector('#editorArtPanelRoot'),
            samePipFrame:
              identity?.pipFrame === document.querySelector('iframe[title="画中画设置"]'),
            src: video.currentSrc || video.src,
            currentTime: video.currentTime,
            paused: video.paused,
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            artTimes: times(snapshot.project.art.overlays),
            pipTimes: times(snapshot.project.pip.overlays),
            artTexts: snapshot.project.art.overlays.map(item => item.text || ''),
                composeArtTexts: request.artOverlays.map(item => item.text || ''),
              };
        }"""
    )

    assert after["identitySurvived"] is True
    assert after["sameVideo"] is True
    assert after["sameArtPanel"] is True
    assert after["samePipFrame"] is True
    assert after["src"] == before["src"]
    assert after["timingRevision"] == before["timingRevision"]
    assert after["revision"] > before["revision"]
    assert after["artTimes"] == before["artTimes"]
    assert after["pipTimes"] == before["pipTimes"]
    assert "全新文案" in after["artTexts"]
    assert "全新文案" in after["composeArtTexts"]
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
    page.frame_locator('iframe[title="画中画设置"]').locator(
        "#pipWorkspace"
    ).wait_for(state="visible")
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


def test_iframe_revision_floor_rejects_stale_state_and_acks_local_edits(
    browser_session,
    seeded_editor_job,
):
    browser_session.page.add_init_script(
        "window.__EDITOR_ART_PANEL_ENABLED__ = false;"
    )
    page = open_editor(browser_session, seeded_editor_job)
    page.locator("#cutPreviewVideo").evaluate(
        """video => {
          video.pause();
          video.currentTime = 0.5;
          video.dispatchEvent(new Event('seeking'));
          video.dispatchEvent(new Event('timeupdate'));
        }"""
    )
    page.locator('[data-editor-tool="art"]').click()
    art_frame = page.frame_locator('iframe[title="艺术字设置"]')
    art_frame.locator("#artWorkspace").wait_for(state="visible")
    page.locator("#editorSuitePreviewOverlay .is-art").wait_for(state="visible")

    child_revision = art_frame.locator("body").evaluate(
        "body => editorHostLastAppliedRevision"
    )
    before = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            art: snapshot.project.art,
          };
        }"""
    )
    page.evaluate(
        """() => {
          window.__staleToolStateHandled = false;
          const listener = event => {
            if (event.data?.probeId !== 'stale-art-state') return;
            window.removeEventListener('message', listener);
            window.__staleToolStateHandled = true;
          };
          window.addEventListener('message', listener);
        }"""
    )
    art_frame.locator("body").evaluate(
        """(body, payload) => {
          window.parent.postMessage(payload, window.location.origin);
        }""",
        {
            "type": "editor-suite:tool-state",
            "kind": "art",
            "probeId": "stale-art-state",
            "revision": child_revision - 2,
            "timingRevision": before["timingRevision"],
            "changeKind": "tool-state",
            "generationPayload": {
                "source": "original",
                "overlays": [{"text": "迟到旧状态", "start": 7, "end": 8}],
            },
        },
    )
    page.wait_for_function("window.__staleToolStateHandled === true")
    after_stale = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return {
            revision: snapshot.revision,
            timingRevision: snapshot.timingRevision,
            art: snapshot.project.art,
          };
        }"""
    )
    assert after_stale == before

    first_x = 0.37
    art_frame.locator("body").evaluate(
        """(body, x) => {
          overlays[0].x = x;
          notifyEditorHost({ force: true });
        }""",
        arg=first_x,
    )
    page.wait_for_function(
        """x => {
          const item = window.EditorSuite.projectSnapshot().project.art.overlays[0];
          return Math.abs(Number(item?.x) - x) < 0.0001;
        }""",
        arg=first_x,
    )
    first = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return { revision: snapshot.revision, timingRevision: snapshot.timingRevision };
        }"""
    )
    art_frame.locator("body").evaluate(
        """(body, revision) => new Promise(resolve => {
          const finish = () => resolve(editorHostLastAppliedRevision);
          if (editorHostLastAppliedRevision >= revision) finish();
          else window.addEventListener('message', finish, { once: true });
        })""",
        first["revision"],
    )

    second_x = 0.41
    art_frame.locator("body").evaluate(
        """(body, x) => {
          overlays[0].x = x;
          notifyEditorHost({ force: true });
        }""",
        arg=second_x,
    )
    page.wait_for_function(
        """x => {
          const item = window.EditorSuite.projectSnapshot().project.art.overlays[0];
          return Math.abs(Number(item?.x) - x) < 0.0001;
        }""",
        arg=second_x,
    )
    second = page.evaluate(
        """() => {
          const snapshot = window.EditorSuite.projectSnapshot();
          return { revision: snapshot.revision, timingRevision: snapshot.timingRevision };
        }"""
    )
    assert first["revision"] == before["revision"] + 1
    assert second["revision"] == first["revision"] + 1
    assert first["timingRevision"] == before["timingRevision"]
    assert second["timingRevision"] == before["timingRevision"]


def test_standalone_art_page_keeps_legacy_editor_with_shared_renderer(
    browser_session,
    seeded_editor_job,
):
    page = browser_session.page
    page.goto(
        f"{browser_session.base_url}/art-text"
        f"?job={seeded_editor_job.job_id}&source=original"
    )
    page.locator("#artWorkspace").wait_for(state="visible")
    page.locator("#artVideo").wait_for(state="attached")
    page.locator("#overlayText").wait_for(state="visible")
    shared_runtime = page.evaluate(
        """() => ({
          model: Boolean(window.EditorArtModel),
          renderer: Boolean(window.EditorArtRenderer),
          topLevelPanel: Boolean(document.querySelector('#editorArtPanelRoot')),
          overlayCount: overlays.length,
        })"""
    )
    assert shared_runtime == {
        "model": True,
        "renderer": True,
        "topLevelPanel": False,
        "overlayCount": 1,
    }

    page.locator("#overlayText").fill("独立页面仍可编辑")
    page.wait_for_function(
        "() => overlays[0]?.text === '独立页面仍可编辑'"
    )
    page.locator("#artVideo").evaluate(
        """video => {
          video.currentTime = 0.5;
          video.dispatchEvent(new Event('timeupdate'));
        }"""
    )
    assert page.locator("#overlayLayer .preview-overlay").count() == 1


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
    if recovery_response.status == 404:
        assert recovery_response.json()["detail"] == "转写任务不存在或服务已重启。"
        page.wait_for_timeout(50)
        assert browser_session.diagnostics() == []
        pytest.xfail("Phase A：服务重启后尚未从磁盘恢复同一 job 的完整可编辑状态。")

    assert recovery_response.ok
    page.goto(editor_url)

    page.locator("#resultCard").wait_for(state="visible", timeout=2000)
    assert page.locator("#segmentList").inner_text() == original_text
    assert page.locator('[data-editor-tool="art"]').get_attribute(
        "aria-disabled"
    ) == "false"
