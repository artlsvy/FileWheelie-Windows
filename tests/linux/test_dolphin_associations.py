"""MIME preference safety; all writes and helper calls stay in isolated XDG roots."""

import json
from types import SimpleNamespace

import pytest

from filewheel import preferences
from filewheel.platforms.linux import dolphin_associations as d

COMMAND = ["/opt/filewheel/filewheel"]
MIME = "image/png"
FW = d.DESKTOP_ID


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setattr(d, "available", lambda: True)
    monkeypatch.setattr(d, "refresh", lambda: None)
    monkeypatch.setattr(
        d, "query_apps", lambda mime: ("viewer.desktop", ["viewer.desktop", "editor.desktop"])
    )
    from filewheel.platforms.linux.integration import atomic_write, entries

    for path, value in entries(COMMAND).items():
        atomic_write(path, value)
    generic, kde = d._targets()
    generic.parent.mkdir(exist_ok=True)
    return generic, kde


def apply():
    return d.install(COMMAND, mimes=[MIME])


def test_second_position_keeps_primary_and_unrelated_bytes(setup):
    generic, _ = setup
    original = "# keep me\n[Default Applications]\nimage/png=viewer.desktop;editor.desktop;\ntext/plain=kate.desktop;\n\n[Added Associations]\nimage/png=viewer.desktop;third.desktop;\n"
    generic.write_text(original)
    assert apply()["configured"] == [MIME]
    value = generic.read_text()
    assert d._ids(d._value(value, "Default Applications", MIME)) == [
        "viewer.desktop",
        FW,
        "editor.desktop",
    ]
    assert d._ids(d._value(value, "Added Associations", MIME)) == [
        "viewer.desktop",
        FW,
        "third.desktop",
    ]
    assert "# keep me\n" in value and "text/plain=kate.desktop;\n" in value
    d.remove(COMMAND)
    assert generic.read_text() == original


def test_upgrade_is_idempotent_and_remembers_original_preferences(setup):
    generic, _ = setup
    generic.write_text("[Default Applications]\nimage/png=viewer.desktop;editor.desktop;\n")
    apply()
    snapshot = d._journal_path().read_text()
    apply()
    assert d._journal_path().read_text() == snapshot
    d.remove(COMMAND)
    assert d._ids(d._value(generic.read_text(), "Default Applications", MIME)) == [
        "viewer.desktop",
        "editor.desktop",
    ]
    assert not d._journal_path().exists()


def test_manual_existing_filewheel_second_is_not_left_dangling_on_remove(setup):
    generic, _ = setup
    generic.write_text(f"[Added Associations]\nimage/png=viewer.desktop;{FW};editor.desktop;\n")
    apply()
    d.remove(COMMAND)
    assert FW not in generic.read_text()
    assert "viewer.desktop;editor.desktop;" in generic.read_text()


def test_kde_specific_defaults_keep_precedence_and_generic_default(setup):
    generic, kde = setup
    generic.write_text("[Default Applications]\nimage/png=generic.desktop;\n")
    kde.write_text("# kde\n[Default Applications]\nimage/png=viewer.desktop;editor.desktop;\n")
    apply()
    assert d._ids(d._value(kde.read_text(), "Default Applications", MIME))[:2] == [
        "viewer.desktop",
        FW,
    ]
    assert d._value(generic.read_text(), "Default Applications", MIME) == "generic.desktop;"
    d.remove(COMMAND)
    assert (
        kde.read_text()
        == "# kde\n[Default Applications]\nimage/png=viewer.desktop;editor.desktop;\n"
    )


def test_later_user_edits_are_preserved_except_our_id(setup):
    generic, _ = setup
    apply()
    current = generic.read_text()
    current = d._replace(current, "Default Applications", MIME, f"new.desktop;{FW};custom.desktop;")
    current += "\n# user's later addition\n[Other]\nsetting=preserve\n"
    generic.write_text(current)
    d.remove(COMMAND)
    restored = generic.read_text()
    assert d._value(restored, "Default Applications", MIME) == "new.desktop;custom.desktop;"
    assert "# user's later addition\n[Other]\nsetting=preserve\n" in restored


@pytest.mark.parametrize("primary", [None, FW])
def test_never_promotes_filewheel_to_normal_default_or_replaces_user_default(
    setup, monkeypatch, primary
):
    generic, _ = setup
    monkeypatch.setattr(d, "query_apps", lambda mime: (primary, []))
    assert not apply()["configured"]
    assert not generic.exists() and not d._journal_path().exists()


def test_explicit_user_exclusion_and_opt_out_respected(setup):
    generic, _ = setup
    original = f"[Removed Associations]\nimage/png={FW};excluded.desktop;\n"
    generic.write_text(original)
    assert not apply()["configured"]
    assert generic.read_text() == original
    assert d.install(COMMAND, mimes=[MIME], force=True)["configured"] == [MIME]
    assert FW not in d._value(generic.read_text(), "Removed Associations", MIME)
    d.remove(COMMAND)
    assert d._value(generic.read_text(), "Removed Associations", MIME) == f"{FW};excluded.desktop;"
    preferences.save_dolphin_enabled(False)
    assert not apply()["configured"]
    assert d.install(COMMAND, mimes=[MIME], force=True)["configured"] == [MIME]


def test_foreign_state_and_symlinks_preserved(setup, tmp_path):
    generic, _ = setup
    apply()
    with pytest.raises(RuntimeError, match="another installation"):
        d.install(["/other/filewheel"], mimes=[MIME])
    d.remove(COMMAND)
    generic.unlink()
    external = tmp_path / "foreign"
    external.write_text("preserve")
    generic.symlink_to(external)
    with pytest.raises(RuntimeError, match="symlink"):
        apply()
    assert external.read_text() == "preserve"


def test_cache_failure_is_recoverable_with_original_rollback(setup):
    generic, _ = setup
    original = "[Default Applications]\nimage/png=viewer.desktop;editor.desktop;\n"
    generic.write_text(original)

    def fail():
        raise RuntimeError("cache refresh failed")

    with pytest.raises(RuntimeError, match="cache"):
        d.install(COMMAND, mimes=[MIME], update=fail)
    assert d._journal_path().exists()
    apply()
    d.remove(COMMAND)
    assert (
        d._value(generic.read_text(), "Default Applications", MIME)
        == "viewer.desktop;editor.desktop;"
    )


def test_concurrent_preference_edit_not_overwritten(setup, monkeypatch):
    generic, _ = setup
    real_write = d.atomic_write

    def editing(path, content, mode=0o644):
        real_write(path, content, mode)
        if path == d._journal_path():
            generic.write_text("# concurrent editor\n")

    monkeypatch.setattr(d, "atomic_write", editing)
    with pytest.raises(RuntimeError, match="concurrently"):
        apply()
    assert generic.read_text() == "# concurrent editor\n"


def test_registry_mime_selection_only_uses_available_inputs():
    registry = SimpleNamespace(
        capabilities=[
            SimpleNamespace(input_extension=ext)
            for ext in (".png", ".pdf", ".jpg", ".jpeg", ".unknown-filewheel")
        ]
    )
    assert d.supported_mimes(registry) == ["application/pdf", "image/jpeg", "image/png"]


def test_malformed_journal_cannot_write_arbitrary_files(setup, tmp_path):
    apply()
    state = json.loads(d._journal_path().read_text())
    state["changes"][0]["path"] = str(tmp_path / "outside")
    d._journal_path().write_text(json.dumps(state))
    with pytest.raises(RuntimeError, match="Invalid"):
        d.remove(COMMAND)
    assert not (tmp_path / "outside").exists()


def test_duplicate_mime_entries_fail_without_preference_changes(setup):
    generic, _ = setup
    original = "[Default Applications]\nimage/png=first.desktop;\nimage/png=second.desktop;\n"
    generic.write_text(original)
    with pytest.raises(RuntimeError, match="Duplicate"):
        apply()
    assert generic.read_text() == original


def test_capability_removal_restores_obsolete_mime_entries(setup):
    generic, _ = setup
    original = "[Default Applications]\nimage/png=viewer.desktop;editor.desktop;\n"
    generic.write_text(original)
    apply()
    d.install(COMMAND, mimes=[])
    assert (
        d._value(generic.read_text(), "Default Applications", MIME)
        == "viewer.desktop;editor.desktop;"
    )
    assert FW not in generic.read_text()
    assert not d.status()["configured"]


def test_parallel_management_refused_without_preference_changes(setup):
    import fcntl

    lock = preferences._path().parent / "dolphin-associations.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("w") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="Another Dolphin setup"):
            apply()
    assert not d._targets()[0].exists()


def test_legacy_owned_desktop_launcher_migrates_without_global_octet_stream(setup):
    from filewheel.platforms.linux import integration

    for path, content in integration.entries(COMMAND, legacy=True).items():
        path.write_text(content)
    integration.configure("install", COMMAND)
    desktop = next(iter(integration.entries(COMMAND)))
    assert "MimeType=application/octet-stream" not in desktop.read_text()
