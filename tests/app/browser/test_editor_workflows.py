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
    art_frame = page.frame_locator('iframe[title="艺术字设置"]')
    art_frame.locator("#artWorkspace").wait_for(state="visible")
    art_frame.get_by_role("button", name=re.compile("保留内容")).first.wait_for()
    selected_art = art_frame.locator("#overlayList button.is-selected")
    assert selected_art.count() == 1
    assert "保留内容" in selected_art.inner_text()
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
    selected_time = page.locator("#cutPreviewVideo").evaluate(
        "video => video.currentTime"
    )

    page.locator('[data-editor-tool="cut"]').click()
    assert page.locator(".text-editor-panel-stack").is_visible()
    wait_for_preview_time(page, selected_time)
    page.locator('[data-editor-tool="art"]').click()
    wait_for_preview_time(page, selected_time)
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


@pytest.mark.parametrize("playing", [False, True], ids=["paused", "playing"])
def test_version_save_preserves_base_media_identity_and_playback(
    browser_session,
    seeded_editor_job,
    playing,
):
    page = open_editor(browser_session, seeded_editor_job)
    page.locator('[data-editor-tool="art"]').click()
    page.frame_locator('iframe[title="艺术字设置"]').locator(
        "#artWorkspace"
    ).wait_for(state="visible")
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
    art_frame = page.frame_locator('iframe[title="艺术字设置"]')
    art_frame.locator("#artWorkspace").wait_for(state="visible")
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
    expected_art_start = float(art_frame.locator("#startTime").input_value())
    expected_art_end = float(art_frame.locator("#endTime").input_value())
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
    art_frame = page.frame_locator('iframe[title="艺术字设置"]')
    art_frame.locator("#artWorkspace").wait_for(state="visible")
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
            artFrame: document.querySelector('iframe[title="艺术字设置"]'),
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
            sameArtFrame:
              identity?.artFrame === document.querySelector('iframe[title="艺术字设置"]'),
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
    assert after["sameArtFrame"] is True
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
    art_frame = page.frame_locator('iframe[title="艺术字设置"]')
    art_frame.locator("#artWorkspace").wait_for(state="visible")
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
    art_frame.locator("body").evaluate(
        """body => new Promise(resolve => {
          const check = () => {
            const parentRevision = window.parent.EditorSuite.projectSnapshot().revision;
            if (editorHostLastAppliedRevision >= parentRevision) resolve(true);
            else window.requestAnimationFrame(check);
          };
          check();
        })"""
    )
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
    page.wait_for_function(
        """expected => {
          const frame = document.querySelector('iframe[title="艺术字设置"]');
          const input = frame?.contentDocument?.querySelector('#startTime');
          return input && Math.abs(Number(input.value) - expected) < 0.001;
        }""",
        arg=committed["start"],
    )

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
    assert base_media_mutations(page) == {"srcWrites": 0, "loadCalls": 0}


def test_iframe_revision_floor_rejects_stale_state_and_acks_local_edits(
    browser_session,
    seeded_editor_job,
):
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
