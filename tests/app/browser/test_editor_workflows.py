from __future__ import annotations

import json
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
            while (!window.EditorSuite?.projectSnapshot?.()) {
              await new Promise(resolve => window.setTimeout(resolve, 0));
            }
            const snapshot = window.EditorSuite.projectSnapshot();
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
        "艺术字设置",
        "AI 推荐",
    ]
    assert art_panel.locator('[data-art-tab="transcript"]').count() == 0
    assert art_panel.locator(
        '[data-art-panel="settings"] [data-art-transcript-section]'
    ).is_visible()
    transcript_action = art_panel.locator("[data-art-transcript-section]")
    assert transcript_action.get_by_role(
        "button", name="一键添加视频文案", exact=True
    ).count() == 1
    assert transcript_action.locator("textarea").count() == 0
    assert transcript_action.locator("[data-art-transcript-save]").count() == 0
    assert transcript_action.locator("[data-art-transcript-list]").count() == 0
    assert transcript_action.locator("[data-art-add-selected]").count() == 0
    for tab_name in ("settings", "ai"):
        tab = art_panel.locator(f'[data-art-tab="{tab_name}"]')
        panel = art_panel.locator(f'[data-art-panel="{tab_name}"]')
        assert tab.get_attribute("aria-controls") == panel.get_attribute("id")
        assert panel.get_attribute("aria-labelledby") == tab.get_attribute("id")
    settings_tab = art_panel.locator('[data-art-tab="settings"]')
    ai_tab = art_panel.locator('[data-art-tab="ai"]')
    settings_tab.focus()
    settings_tab.press("ArrowRight")
    assert ai_tab.get_attribute("aria-selected") == "true"
    assert art_panel.locator('[data-art-panel="settings"]').is_hidden()
    assert art_panel.locator('[data-art-panel="ai"]').is_visible()
    ai_tab.press("End")
    assert ai_tab.get_attribute("aria-selected") == "true"
    ai_tab.press("Home")
    assert settings_tab.get_attribute("aria-selected") == "true"
    settings_tab.press("ArrowLeft")
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
    art_panel.locator('[data-art-tab="settings"]').click()
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


def test_top_level_pip_prompt_image_controls_and_schema_v2_recovery(
    browser_session,
    seeded_editor_job,
):
    page = open_editor(browser_session, seeded_editor_job)
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
        panel.locator("[data-art-add-text]").fill(text)
        panel.locator("[data-art-add]").click()
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays.length === 4"""
    )

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


def test_manual_art_overlays_share_one_timeline_track_and_independent_lanes(
    browser_session,
    seeded_two_cue_transcript_track_editor_job,
):
    page = open_editor(browser_session, seeded_two_cue_transcript_track_editor_job)
    page.locator('[data-editor-tool="art"]').click()
    panel = page.locator("#editorArtPanelRoot")
    panel.wait_for(state="visible")

    for text in ("手动标题一", "手动标题二"):
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
    assert {item["laneIndex"] for item in layout["manualSegments"]} == {"0", "1"}
    assert all(item["tabIndex"] >= 0 for item in layout["manualSegments"])
    first_segment, second_segment = layout["manualSegments"]
    assert first_segment["bottom"] <= second_segment["top"] or (
        second_segment["bottom"] <= first_segment["top"]
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
    click_clip_and_assert_playhead(manual_segment, f"art:{selected_id}", 0.68)
    transcript_segment = page.locator(
        '#editorSuiteTimelineLayer [data-source-id="browser-transcript-cue-2"]'
    )
    click_clip_and_assert_playhead(
        transcript_segment,
        "art:browser-transcript-cue-2",
        0.65,
    )
    manual_segment.click()
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

    panel.locator('[data-art-track-select="browser-transcript-track"]').click()
    panel.locator("[data-art-delete]").click()
    page.locator("#appDialogConfirm").click()
    page.wait_for_function(
        """() => window.EditorSuite.projectSnapshot().project.art.overlays.length === 0"""
    )

    assert panel.locator("[data-art-track-select]").count() == 0
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
    assert panel.locator("[data-art-selection-empty]").is_visible()
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
        "artTabs": ["艺术字设置", "AI 推荐"],
        "transcriptInSettings": True,
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
