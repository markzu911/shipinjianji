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
    requirements = (build_dir / "requirements.txt").read_text(encoding="utf-8")
    assert (
        'torch==2.9.1; sys_platform == "darwin" and platform_machine == "arm64"'
        in requirements
    )
    assert (
        'torchaudio==2.9.1; sys_platform == "darwin" and platform_machine == "arm64"'
        in requirements
    )
    assert (
        'torch==2.2.2; sys_platform == "darwin" and platform_machine == "x86_64"'
        in requirements
    )
    assert (
        'torchaudio==2.2.2; sys_platform == "darwin" and platform_machine == "x86_64"'
        in requirements
    )
    assert 'charset-normalizer==3.4.4; sys_platform == "win32"' in requirements
    assert "首次在语音附近保存剪辑边界时" in build_mac_package.MAC_README
    assert "模型下载、校验、加载或推理失败时会安全降级" in build_mac_package.MAC_README
