"""Per-user install/update/remove ownership; never executes fixture binaries."""

import os

import pytest

from filewheel.platforms.linux import install, integration


@pytest.fixture(autouse=True)
def isolated_association_environment(tmp_path, monkeypatch):
    from filewheel.platforms.linux import dolphin_associations

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr(dolphin_associations, "available", lambda: False)


def image(path, version=b"one"):
    path.write_bytes(b"\x7fELF" + b"\0" * 4 + b"AI\x02" + b"\0" * 5 + version)
    return path


def test_install_upgrade_remove_preserves_documents(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    source = image(tmp_path / "download.AppImage")
    original = source.read_bytes()
    target = install.install(source)
    assert target.read_bytes() == original and os.access(target, os.X_OK)
    assert all(path.exists() for path in integration.entries([str(target)]))
    document = tmp_path / "user.txt"
    document.write_text("preserve")
    image(source, b"two")
    install.install(source)
    assert target.read_bytes() == source.read_bytes()
    install.uninstall()
    assert not target.exists() and document.read_text() == "preserve"
    assert not any(path.exists() for path in integration.entries([str(target)]))
    assert source.exists()


def test_modified_install_and_foreign_integration_are_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    source = image(tmp_path / "source.AppImage")
    target = install.install(source)
    target.write_text("user modified")
    for action in (lambda: install.install(source), install.uninstall):
        with pytest.raises(RuntimeError):
            action()
    assert target.read_text() == "user modified"
    target.write_bytes(source.read_bytes())
    entry = next(iter(integration.entries([str(target)])))
    entry.write_text("foreign entry")
    with pytest.raises(RuntimeError):
        install.uninstall()
    assert target.exists() and entry.read_text() == "foreign entry"


def test_unowned_and_symlink_targets_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    source = image(tmp_path / "source.AppImage")
    root, target, _ = install._paths()
    root.mkdir(parents=True)
    target.symlink_to(tmp_path / "missing")
    with pytest.raises(RuntimeError):
        install.install(source)
    assert target.is_symlink()


def test_source_mode_launcher_quotes_and_refuses_conflict(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    command = ["/tmp/a $quoted file/python", "-m", "filewheel"]
    integration.configure("install", command)
    desktop = next(iter(integration.entries(command)))
    assert "\\$" in desktop.read_text() and "%%" in integration.quote("percent%")
    assert "-- %f" in desktop.read_text()
    with pytest.raises(RuntimeError):
        integration.configure("remove", ["different"])
    integration.configure("remove", command)


def test_requires_real_appimage_container(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    fake = tmp_path / "source"
    fake.write_text("not executable")
    with pytest.raises(RuntimeError):
        install.install(fake)


def test_desktop_argv_round_trip_with_gio(tmp_path, monkeypatch):
    """Exercise the desktop parser, including both layers of backslash escaping."""
    import json
    import subprocess
    import time
    from pathlib import Path

    probe = subprocess.run(
        ["/usr/bin/python3", "-c", "from gi.repository import Gio"],
        capture_output=True,
        check=False,
    )
    if probe.returncode:
        pytest.skip("System GIO desktop parser unavailable")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    executable = tmp_path / 'space æ $ ` " \\ launcher'
    result = tmp_path / "argv.json"
    executable.write_text(
        "#!/usr/bin/python3\nimport json,sys\nfrom pathlib import Path\n"
        + f"Path({str(result)!r}).write_text(json.dumps(sys.argv[1:]))\n"
    )
    executable.chmod(0o755)
    integration.configure("install", [str(executable)])
    entry = next(iter(integration.entries([str(executable)])))
    source = tmp_path / 'unicode æ file % $ " .txt'
    source.write_text("fixture")
    subprocess.run(
        [
            "/usr/bin/python3",
            "-c",
            (
                "from gi.repository import Gio; import sys; "
                "app=Gio.DesktopAppInfo.new_from_filename(sys.argv[1]); "
                "assert app is not None; app.launch([Gio.File.new_for_path(sys.argv[2])],None)"
            ),
            str(entry),
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    deadline = time.monotonic() + 3
    while not result.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert json.loads(Path(result).read_text()) == ["--ui-backend", "quick", "--", str(source)]


def test_uninstall_removes_only_installed_startup_from_another_invocation(tmp_path, monkeypatch):
    from filewheel.platforms.linux import startup

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    source = image(tmp_path / "download.AppImage")
    target = install.install(source)
    startup.configure("install", [str(target)])
    # Uninstall invoked from the downloaded copy must remove the installed entry.
    monkeypatch.setattr(startup, "launch_command", lambda: [str(source)])
    install.uninstall()
    assert not startup._entry().exists()
    target = install.install(source)
    startup.configure("install", ["/other/independent/filewheel"])
    install.uninstall()
    assert "independent" in startup._entry().read_text()
    assert not target.exists()
