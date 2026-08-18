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
