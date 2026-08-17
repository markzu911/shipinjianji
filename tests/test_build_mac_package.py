from pathlib import Path

from tools import build_mac_package


def test_mac_package_uses_clean_data_directory(
    tmp_path: Path,
    monkeypatch,
):
    build_dir = tmp_path / "build" / build_mac_package.PACKAGE_NAME
    monkeypatch.setattr(build_mac_package, "BUILD_DIR", build_dir)
    monkeypatch.setattr(build_mac_package, "WINDOWS_FONT_DIR", tmp_path / "fonts")

    font_dir = tmp_path / "fonts"
    font_dir.mkdir()
    for filename in build_mac_package.BUILTIN_FONT_FILENAMES:
        (font_dir / filename).write_bytes(b"font")

    build_mac_package.copy_project_files()

    assert "data" not in build_mac_package.PROJECT_FILES
    assert not any((build_dir / "data" / "jobs").glob("*.mp4"))
    assert not any((build_dir / "data" / "history").glob("history-*"))
    assert {path.name for path in (build_dir / "data" / "models").iterdir()} == {
        ".gitkeep"
    }
    assert (build_dir / "data" / "fonts" / "manifest.json").read_text(
        encoding="utf-8"
    ) == "[]\n"
    assert (build_dir / "data" / "art-templates" / "manifest.json").read_text(
        encoding="utf-8"
    ) == "[]\n"
