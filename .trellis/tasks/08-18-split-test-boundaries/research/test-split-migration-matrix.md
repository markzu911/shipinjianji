# Research: Test split migration matrix

- Query: Map every existing `tests/test_app.py` test exactly once into behavior-preserving `tests/app/` feature modules, including imports, fixtures, helpers, and ordering risks.
- Scope: internal
- Date: 2026-08-18

## Findings

### Inventory and invariant

- `tests/test_app.py` contains 164 top-level `test_*` functions. Two parameterized functions expand the application suite to 167 collected nodes: `test_shared_acoustic_boundary_requires_a_meaningful_valley` has two cases (`tests/test_app.py:5245`) and `test_full_transcript_art_track_repairs_ai_breaks_inside_phrases` has three cases (`tests/test_app.py:8213`). `tests/test_build_mac_package.py` contributes one node, so the repository baseline is 168 collected tests.
- The largest function is `test_frontend_assets_are_versioned_and_not_cached`, 1,037 lines at `tests/test_app.py:658`; its detailed assertion-preserving split is in `fixture-scope-and-frontend-contracts.md`.
- The module has only two pytest fixtures, `isolated_jobs` (`tests/test_app.py:20`) and `sample_video` (`tests/test_app.py:54`), and one non-test helper, `_build_track_words` (`tests/test_app.py:8310`).
- Preserve `from __future__ import annotations` in each destination module. The import lists below are the exact union of currently referenced imported names for the mapped tests, not stylistic guesses.
- The matrix below assigns all 164 original test functions exactly once. The frontend omnibus function remains one migration item but is replaced by nine more specific functions, increasing collected nodes without deleting a contract.

### Shared fixtures

Move these unchanged to `tests/app/conftest.py`:

- `isolated_jobs` (`tests/test_app.py:20-51`), imports: `Path`, `pytest`, `server.app as app_module`.
- `sample_video` (`tests/test_app.py:54-82`), imports: `subprocess`, `Path`, `pytest`, `server.app as app_module`.

### `tests/app/test_settings.py`

Imports: `Path`, `pytest`, `TestClient`, `server.app as app_module`.

- `test_health_reports_media_tools` (`tests/test_app.py:85`)
- `test_model_settings_mask_credentials_and_list_current_models` (`tests/test_app.py:108`)
- `test_model_settings_update_persists_and_applies_without_restart` (`tests/test_app.py:136`)
- `test_model_settings_update_volcengine_without_replacing_existing_key` (`tests/test_app.py:188`)
- `test_model_settings_clear_removes_current_and_legacy_keys` (`tests/test_app.py:223`)
- `test_model_settings_reject_invalid_provider_and_whitespace_key` (`tests/test_app.py:246`)
- `test_model_settings_allow_updates_from_remote_clients` (`tests/test_app.py:279`)
- `test_model_settings_page_is_available` (`tests/test_app.py:299`)

### `tests/app/test_maintenance_history.py`

Imports: `asyncio`, `Path`, `pytest`, `TestClient`, `server.app as app_module`.

- `test_job_cleanup_removes_only_stale_inactive_job_directories` (`tests/test_app.py:308`)
- `test_job_cleanup_removes_stale_completed_in_memory_job` (`tests/test_app.py:383`)
- `test_periodic_storage_cleanup_runs_after_interval` (`tests/test_app.py:406`)
- `test_job_cleanup_api_supports_preview_and_execution` (`tests/test_app.py:433`)
- `test_failed_transcription_removes_job_working_directory` (`tests/test_app.py:459`)
- `test_history_versions_are_persistent_manageable_and_reusable` (`tests/test_app.py:495`)
- `test_history_version_uses_custom_name_or_bounded_safe_default` (`tests/test_app.py:580`)
- `test_history_limit_keeps_latest_twenty_and_removes_old_directories` (`tests/test_app.py:620`)
- `test_missing_job_returns_404` (`tests/test_app.py:9568`)

### `tests/app/test_frontend_contracts.py`

Imports: `json`, `subprocess`, `Path`, `pytest`, `TestClient`, `server.app as app_module`.

- `test_frontend_assets_are_versioned_and_not_cached` (`tests/test_app.py:658`), replace with the nine assertion-preserving functions documented in `fixture-scope-and-frontend-contracts.md`.
- `test_frontend_text_ranges_use_character_units_with_per_segment_fallback` (`tests/test_app.py:1697`)
- `test_frontend_merges_adjacent_deleted_text_across_range_keys` (`tests/test_app.py:1917`)
- `test_frontend_merged_selection_preserves_shared_physical_boundaries` (`tests/test_app.py:2137`)
- `test_frontend_transcript_follow_scroll_anchors_clamps_and_deduplicates` (`tests/test_app.py:2230`)
- `test_timeline_model_shares_selection_drag_resize_and_persistence` (`tests/test_app.py:2337`)
- `test_douyin_preview_is_inline_only` (`tests/test_app.py:2431`)

### `tests/app/test_asset_libraries.py`

Imports: `io`, `json`, `Path`, `pytest`, `TestClient`, `server.app as app_module`.

- `test_art_template_library_upload_rename_render_and_delete` (`tests/test_app.py:2565`)
- `test_art_template_library_rejects_font_upload` (`tests/test_app.py:2673`)
- `test_art_template_library_rejects_unknown_character_animation` (`tests/test_app.py:2689`)
- `test_art_template_hide_and_restore` (`tests/test_app.py:2716`)
- `test_art_position_presets_crud` (`tests/test_app.py:2748`)
- `test_art_position_presets_validation` (`tests/test_app.py:2789`)
- `test_font_library_upload_rename_render_and_delete` (`tests/test_app.py:2819`)
- `test_font_library_rejects_non_font_upload` (`tests/test_app.py:2878`)

### `tests/app/test_transcription_suggestions.py`

Imports: `io`, `json`, `array` from `array`, `Path`, `pytest`, `TestClient`, `server.app as app_module`.

- `test_transcript_is_normalized_to_simplified_chinese` (`tests/test_app.py:2888`)
- `test_rejects_unsupported_file_type` (`tests/test_app.py:2892`)
- `test_requires_online_asr_api_key` (`tests/test_app.py:2906`)
- `test_paraformer_returns_simplified_timestamps` (`tests/test_app.py:2917`)
- `test_punctuation_polish_rebuilds_sentence_segments` (`tests/test_app.py:3000`)
- `test_editable_transcript_segments_follow_clause_boundaries` (`tests/test_app.py:3035`)
- `test_semantic_tokenization_replaces_mechanical_asr_chunks` (`tests/test_app.py:3071`)
- `test_ai_suggestions_are_validated_and_mapped_to_word_ranges` (`tests/test_app.py:3111`)
- `test_repeated_restart_is_detected_even_when_ai_returns_no_suggestion` (`tests/test_app.py:3231`)
- `test_abandoned_opinion_leadin_is_removed_without_touching_main_clause` (`tests/test_app.py:3343`)
- `test_repetition_rule_protects_the_copy_it_intends_to_keep` (`tests/test_app.py:3436`)
- `test_repetition_rules_override_partial_ai_ranges_and_merge_abandoned_restarts` (`tests/test_app.py:3516`)
- `test_repetition_rules_still_work_when_ai_analysis_fails` (`tests/test_app.py:3672`)
- `test_upload_extracts_audio_and_returns_transcript` (`tests/test_app.py:3738`)
- `test_no_speech_detection_keeps_boundaries_and_protects_video_edges` (`tests/test_app.py:3791`)
- `test_no_speech_detection_ignores_short_conversational_pauses` (`tests/test_app.py:3846`)

### `tests/app/test_cut_draft.py`

Imports: `array` from `array`, `Path`, `pytest`, `TestClient`, `server.app as app_module`.

- `test_transcript_word_can_be_corrected_without_changing_timestamps` (`tests/test_app.py:3858`)
- `test_transcript_word_correction_rejects_blank_text` (`tests/test_app.py:3909`)
- `test_full_transcript_edits_are_aligned_to_the_matching_words` (`tests/test_app.py:3940`)
- `test_cut_draft_is_persisted_versioned_restored_and_cleared` (`tests/test_app.py:4015`)
- `test_cut_draft_preserves_explicitly_empty_text_ranges` (`tests/test_app.py:4098`)
- `test_cut_draft_defaults_automatic_no_speech_marker_for_legacy_clients` (`tests/test_app.py:4134`)
- `test_cut_draft_aligns_text_media_ranges_before_preview_and_is_idempotent` (`tests/test_app.py:4162`)
- `test_cut_draft_put_uses_natural_character_boundaries_not_raw_asr_tokens` (`tests/test_app.py:4258`)
- `test_text_ranges_use_character_units_but_manual_timeline_ranges_stay_exact` (`tests/test_app.py:4362`)
- `test_character_units_fall_back_per_segment_in_mixed_transcript` (`tests/test_app.py:4404`)
- `test_semantic_range_ignores_overlapping_raw_asr_token` (`tests/test_app.py:4472`)
- `test_editable_transcript_segments_can_split_and_merge_by_selected_text` (`tests/test_app.py:4497`)
- `test_editable_transcript_segments_can_update_text_and_sync_source` (`tests/test_app.py:4580`)
- `test_editing_text_keeps_track_timeline_stable` (`tests/test_app.py:4627`)
- `test_delete_ranges_are_merged_and_cannot_remove_everything` (`tests/test_app.py:4724`)
- `test_overlapping_quiet_range_cannot_delete_the_retained_repeat_take` (`tests/test_app.py:4741`)
- `test_cut_draft_keeps_semantic_text_ranges_separate_from_media_boundaries` (`tests/test_app.py:4804`)
- `test_retained_transcript_does_not_drop_next_natural_word_character` (`tests/test_app.py:4856`)
- `test_quiet_range_is_trimmed_to_the_gap_between_recognized_words` (`tests/test_app.py:4922`)
- `test_quiet_ranges_partially_or_fully_covering_text_never_delete_it` (`tests/test_app.py:4945`)
- `test_automatic_ranges_do_not_merge_across_a_short_retained_word` (`tests/test_app.py:4969`)
- `test_partial_manual_word_delete_does_not_expand_adjacent_automatic_cuts` (`tests/test_app.py:5024`)
- `test_cut_draft_alignment_without_asr_words_falls_back_to_semantic_range` (`tests/test_app.py:5076`)

### `tests/app/test_cut_acoustic_boundaries.py`

Imports: `array` from `array`, `Path`, `pytest`, `server.app as app_module`.

- `test_shared_acoustic_boundary_removes_tail_inside_raw_ge_yi_token` (`tests/test_app.py:5127`)
- `test_shared_acoustic_boundary_removes_tail_inside_raw_de_ni_token` (`tests/test_app.py:5190`)
- `test_shared_acoustic_boundary_requires_a_meaningful_valley` (`tests/test_app.py:5246`)
- `test_shared_acoustic_boundary_rejects_mismatched_asr_text` (`tests/test_app.py:5295`)
- `test_shared_acoustic_boundary_only_moves_in_the_deletion_direction` (`tests/test_app.py:5347`)
- `test_shared_acoustic_boundary_rejects_character_center_on_monotonic_slope` (`tests/test_app.py:5400`)
- `test_shared_acoustic_boundary_accepts_only_a_quiet_directional_endpoint` (`tests/test_app.py:5455`)
- `test_shared_acoustic_boundary_reaches_true_pause_inside_adjacent_token` (`tests/test_app.py:5498`)
- `test_shared_acoustic_token_extension_requires_quiet_inside_token` (`tests/test_app.py:5540`)
- `test_shared_acoustic_delete_end_cannot_reach_pause_after_retained_character` (`tests/test_app.py:5576`)
- `test_resolved_draft_preserves_saved_shared_physical_boundary` (`tests/test_app.py:5611`)
- `test_media_cut_boundaries_snap_to_waveform_valleys_without_changing_text` (`tests/test_app.py:5656`)
- `test_media_cut_boundaries_can_reach_a_delayed_acoustic_tail_boundary` (`tests/test_app.py:5707`)
- `test_media_cut_boundaries_extend_to_remove_a_high_energy_word_tail` (`tests/test_app.py:5760`)
- `test_media_cut_boundaries_extend_a_quietly_recorded_word_tail` (`tests/test_app.py:5802`)
- `test_ai_suggestion_ranges_do_not_extend_into_next_retained_word` (`tests/test_app.py:5823`)
- `test_suggestion_snapping_does_not_follow_raw_de_ni_token_into_ni` (`tests/test_app.py:5883`)
- `test_suggestion_snapping_does_not_merge_across_short_retained_character` (`tests/test_app.py:5942`)
- `test_shared_acoustic_boundaries_preserve_short_retained_character_core` (`tests/test_app.py:5996`)
- `test_ai_suggestion_ranges_remove_gap_tail_without_crossing_next_word` (`tests/test_app.py:6043`)
- `test_media_cut_boundaries_extend_back_to_remove_an_early_word_head` (`tests/test_app.py:6096`)
- `test_media_cut_boundaries_leave_an_already_quiet_word_end_unchanged` (`tests/test_app.py:6138`)
- `test_audio_quiet_ranges_detect_pause_hidden_inside_asr_word_block` (`tests/test_app.py:9575`)
- `test_retained_transcript_maps_audio_quiet_ranges_to_edited_timeline` (`tests/test_app.py:9602`)

### `tests/app/test_cut_rendering.py`

Imports: `Path`, `pytest`, `TestClient`, `server.app as app_module`.

- `test_retained_transcript_uses_edited_video_timeline` (`tests/test_app.py:6159`)
- `test_retained_transcript_retimes_after_text_and_silence_deletions` (`tests/test_app.py:6190`)
- `test_retained_transcript_can_remove_one_character_without_losing_the_word` (`tests/test_app.py:6244`)
- `test_cut_endpoint_renders_preview_video` (`tests/test_app.py:6270`)
- `test_cut_endpoint_uses_saved_shared_media_range_and_semantic_transcript` (`tests/test_app.py:6445`)
- `test_cut_endpoint_keeps_ni_when_raw_asr_token_crosses_text_boundary` (`tests/test_app.py:6525`)
- `test_probe_video_dimensions` (`tests/test_app.py:9564`)
- `test_cut_render_normalizes_output_audio` (`tests/test_app.py:9718`)

### `tests/app/test_art_text_api.py`

Imports: `Path`, `pytest`, `TestClient`, `server.app as app_module`.

- `test_art_text_can_use_original_video_without_cut` (`tests/test_app.py:6609`)
- `test_art_text_rejects_invalid_overlay_time` (`tests/test_app.py:7653`)
- `test_art_text_preserves_original_timeline_anchor` (`tests/test_app.py:7672`)
- `test_transcript_art_text_overlap_ends_at_next_real_start_time` (`tests/test_app.py:7697`)
- `test_ai_art_suggestions_are_normalized_and_filled_to_requested_count` (`tests/test_app.py:7727`)
- `test_ai_art_suggestion_endpoint_uses_original_video_and_can_be_cleared` (`tests/test_app.py:7779`)

### `tests/app/test_composition.py`

Imports: `Path`, `pytest`, `TestClient`, `server.app as app_module`.

- `test_original_art_and_picture_in_picture_are_blocked_after_cut_starts` (`tests/test_app.py:6678`)
- `test_preview_composition_renders_cut_art_and_pip_in_one_request` (`tests/test_app.py:7344`)
- `test_preview_composition_allows_unchanged_timeline` (`tests/test_app.py:7523`)
- `test_failed_preview_composition_removes_job_working_directory` (`tests/test_app.py:7595`)

### `tests/app/test_picture_in_picture.py`

Imports: `base64`, `io`, `Image`, `Path`, `pytest`, `TestClient`, `server.app as app_module`.

- `test_picture_in_picture_writes_editable_prompt_from_selected_text` (`tests/test_app.py:6716`)
- `test_picture_in_picture_generates_image_with_requested_seedream_model` (`tests/test_app.py:6788`)
- `test_picture_in_picture_image_uses_source_anchor_without_edited_video` (`tests/test_app.py:6874`)
- `test_picture_in_picture_generation_requires_ark_key` (`tests/test_app.py:6941`)
- `test_picture_in_picture_rejects_unsupported_image_aspect_ratio` (`tests/test_app.py:6967`)
- `test_seedance_video_asset_can_be_generated_previewed_and_rendered` (`tests/test_app.py:6986`)
- `test_seedance_copyright_failure_retries_with_safe_prompt` (`tests/test_app.py:7086`)
- `test_seedance_copyright_error_is_user_facing` (`tests/test_app.py:7159`)
- `test_seedance_task_uses_official_content_generation_api` (`tests/test_app.py:7170`)
- `test_seedance_video_generation_requires_ark_key` (`tests/test_app.py:7214`)
- `test_picture_in_picture_video_is_rendered_for_selected_text_time` (`tests/test_app.py:7242`)
- `test_picture_in_picture_overlay_accepts_live_retimed_range` (`tests/test_app.py:7311`)

### `tests/app/test_art_text_track.py`

Imports: `unicodedata`, `SimpleNamespace`, `Path`, `pytest`, `TestClient`, `server.app as app_module`.

Move `_build_track_words` (`tests/test_app.py:8310-8318`) into this module, preferably before its three callers at lines 8323, 8351, and 8393.

- `test_art_text_formats_horizontal_and_vertical_layouts` (`tests/test_app.py:7883`)
- `test_full_transcript_art_track_uses_word_times_and_single_line_cues` (`tests/test_app.py:7908`)
- `test_full_transcript_art_track_keeps_complete_sentences_and_avoids_orphans` (`tests/test_app.py:7991`)
- `test_full_transcript_art_track_keeps_requested_large_font_size` (`tests/test_app.py:8035`)
- `test_full_transcript_art_track_uses_ai_semantic_breaks_and_limits_width` (`tests/test_app.py:8081`)
- `test_ai_transcript_art_text_segmentation_returns_valid_word_boundaries` (`tests/test_app.py:8164`)
- `test_full_transcript_art_track_repairs_ai_breaks_inside_phrases` (`tests/test_app.py:8265`)
- `test_transcript_art_text_track_keeps_two_short_sentences_separate` (`tests/test_app.py:8321`)
- `test_transcript_art_text_track_folds_single_character_sentence_into_next` (`tests/test_app.py:8349`)
- `test_transcript_art_text_track_splits_unpunctuated_long_phrase_naturally` (`tests/test_app.py:8378`)
- `test_transcript_art_text_character_limit_adapts_to_font_and_width` (`tests/test_app.py:8426`)
- `test_art_text_splitter_prefers_audio_pause_boundaries` (`tests/test_app.py:8450`)
- `test_full_transcript_art_track_rejects_missing_word_timestamps` (`tests/test_app.py:8517`)
- `test_full_transcript_art_track_repairs_zero_duration_boundary_words` (`tests/test_app.py:8542`)
- `test_full_transcript_art_track_keeps_spoken_clause_and_word_time_together` (`tests/test_app.py:8576`)
- `test_transcript_track_allows_many_cues_but_keeps_one_shared_style` (`tests/test_app.py:8662`)
- `test_spoken_character_bounce_requires_matching_transcript_timings` (`tests/test_app.py:8701`)
- `test_transcript_track_rejects_legacy_long_cue_before_rendering` (`tests/test_app.py:8745`)
- `test_transcript_track_endpoint_uses_selected_video_transcript` (`tests/test_app.py:8778`)
- `test_transcript_track_endpoint_uses_live_cut_draft_with_source_anchors` (`tests/test_app.py:8828`)
- `test_art_text_balances_lines_and_keeps_closing_punctuation_off_line_start` (`tests/test_app.py:8941`)
- `test_character_bounce_timings_skip_real_audio_pause` (`tests/test_app.py:9621`)
- `test_supplied_audio_aligned_timings_are_not_clamped_back_into_silence` (`tests/test_app.py:9634`)
- `test_character_bounce_overlay_starts_at_voice_after_leading_pause` (`tests/test_app.py:9658`)
- `test_static_transcript_overlays_share_segment_audio_alignment` (`tests/test_app.py:9679`)

### `tests/app/test_art_text_rendering.py`

Imports: `subprocess`, `Image`, `Path`, `pytest`, `server.app as app_module`.

- `test_balanced_multiline_art_text_renders_with_uniform_line_heights` (`tests/test_app.py:8964`)
- `test_all_art_text_templates_render_transparent_layers` (`tests/test_app.py:9005`)
- `test_every_art_text_effect_layer_reuses_fixed_multiline_positions` (`tests/test_app.py:9047`)
- `test_exported_templates_follow_preview_shadow_toggle_contract` (`tests/test_app.py:9092`)
- `test_impact_art_text_keeps_preview_like_thin_rim_and_soft_shadow` (`tests/test_app.py:9131`)
- `test_center_highlight_art_text_renders_white_edges_and_yellow_center` (`tests/test_app.py:9172`)
- `test_character_bounce_art_text_asset_contains_multiple_frames` (`tests/test_app.py:9213`)
- `test_character_bounce_without_speech_times_stays_static` (`tests/test_app.py:9259`)
- `test_impact_art_text_has_no_opaque_duplicate_glyph_below_text` (`tests/test_app.py:9283`)
- `test_art_text_video_uses_short_relative_ffmpeg_command_for_many_cues` (`tests/test_app.py:9331`)
- `test_character_bounce_video_plays_asset_once_from_overlay_start` (`tests/test_app.py:9384`)
- `test_multiline_impact_art_text_keeps_every_line_visually_uniform` (`tests/test_app.py:9446`)
- `test_art_text_render_padding_is_trimmed_without_moving_anchor` (`tests/test_app.py:9499`)
- `test_art_text_layer_is_scaled_into_video_safe_area` (`tests/test_app.py:9534`)

## Code Patterns

- Tests consistently exercise API serialization with `TestClient` (`tests/test_app.py:85`, `tests/test_app.py:495`, `tests/test_app.py:7344`) and media primitives directly when HTTP is not the contract (`tests/test_app.py:5127`, `tests/test_app.py:8964`). Preserve this split; do not convert direct media tests into source-string checks.
- Node-backed frontend behavior tests extract only the required JavaScript source into a temporary script and execute it with `subprocess` (`tests/test_app.py:1697`, `tests/test_app.py:1917`, `tests/test_app.py:2337`). Move them intact; their repeated extraction code is existing duplication, not a reason to introduce a new runner during this structural task.
- External ASR/generation/HTTP calls are isolated with `monkeypatch` in the owning test (`tests/test_app.py:2970`, `tests/test_app.py:3205`, `tests/test_app.py:6830`, `tests/test_app.py:7190`). Do not promote those mocks to broad shared fixtures because their response shapes are contract-specific.

## Related Specs

- `.trellis/spec/testing/index.md`: use `TestClient`, `tmp_path`, real short media, and explicit external-service monkeypatching; global state must be restored and tests must not depend on order.
- `.trellis/spec/guides/project-overview.md`: the current test suite is the authoritative behavior boundary for the monolithic backend and native frontend.
- `.trellis/spec/guides/code-reuse-thinking-guide.md`: avoid duplicating timeline normalization ownership while splitting files.

## Caveats / Not Found

- No pytest configuration file (`pytest.ini`, `pyproject.toml`, `setup.cfg`, or `tox.ini`) was found, so default pytest discovery rules apply.
- Do not add `tests/app/__init__.py` merely for discovery. It is unnecessary unless a new importable helper package is intentionally introduced; this proposal needs only `conftest.py` and test modules.
- Original source line references will become stale after migration; use names as the durable identity and validate the post-migration set against this matrix.
