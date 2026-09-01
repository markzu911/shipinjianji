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
    mac_readme = (build_dir / "README_MAC.md").read_text(encoding="utf-8")
    assert "安装包只包含程序代码、内置字体和空白数据目录" in mac_readme
    assert "首次在语音附近保存剪辑边界时" in mac_readme
    assert "模型下载、校验、加载或推理失败时会安全降级" in mac_readme


def test_mac_package_can_include_env_and_user_assets(
    tmp_path: Path,
    monkeypatch,
):
    root = tmp_path / "root"
    build_dir = tmp_path / "build" / build_mac_package.PACKAGE_NAME
    font_dir = tmp_path / "fonts"

    root.mkdir()
    font_dir.mkdir()
    for filename in build_mac_package.BUILTIN_FONT_FILENAMES:
        (font_dir / filename).write_bytes(b"font")

    (root / ".env").write_text("DASHSCOPE_API_KEY=test-key\n", encoding="utf-8")
    for filename in build_mac_package.USER_ASSET_FILES:
        (root / filename).write_text('{"name":"asset"}\n', encoding="utf-8")

    (root / "data" / "fonts").mkdir(parents=True)
    (root / "data" / "fonts" / "manifest.json").write_text(
        '[{"id":"font-1"}]\n',
        encoding="utf-8",
    )
    (root / "data" / "art-templates").mkdir(parents=True)
    (root / "data" / "art-templates" / "manifest.json").write_text(
        '[{"id":"custom-art-1"}]\n',
        encoding="utf-8",
    )
    (root / "data" / "art-templates" / "hidden.json").write_text(
        '["hidden-template"]\n',
        encoding="utf-8",
    )
    (root / "data" / "art-position-presets").mkdir(parents=True)
    (root / "data" / "art-position-presets" / "manifest.json").write_text(
        '[{"id":"pos-1"}]\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(build_mac_package, "ROOT", root)
    monkeypatch.setattr(build_mac_package, "BUILD_DIR", build_dir)
    monkeypatch.setattr(build_mac_package, "WINDOWS_FONT_DIR", font_dir)
    monkeypatch.setattr(build_mac_package, "PROJECT_FILES", [])

    build_mac_package.copy_project_files(include_env=True, include_user_assets=True)

    assert (build_dir / ".env").read_text(encoding="utf-8") == (
        "DASHSCOPE_API_KEY=test-key\n"
    )
    for filename in build_mac_package.USER_ASSET_FILES:
        assert (build_dir / filename).is_file()
    assert "custom-art-1" in (
        build_dir / "data" / "art-templates" / "manifest.json"
    ).read_text(encoding="utf-8")
    assert "pos-1" in (
        build_dir / "data" / "art-position-presets" / "manifest.json"
    ).read_text(encoding="utf-8")
    assert "font-1" in (build_dir / "data" / "fonts" / "manifest.json").read_text(
        encoding="utf-8"
    )
    mac_readme = (build_dir / "README_MAC.md").read_text(encoding="utf-8")
    assert "包含已配置的 API Key" in mac_readme
    assert "艺术字模板" in mac_readme
