"""Production bridge payload policy and stale/ambiguous target rejection."""

from time import monotonic_ns

import pytest

from filewheel.platforms.linux.dolphin_bridge import validated_click


def test_exact_click_unicode_and_replay(tmp_path):
    source = tmp_path / "unicode æøå %.txt"
    source.write_text("test")
    now = monotonic_ns()
    token = "a" * 64
    values = [token, source.as_uri(), 1, now]
    assert validated_click(values, token=token, previous=0, now=now)[0] == str(source)
    for previous, clock in ((1, now), (0, now + 3_000_000_000), (0, now - 1)):
        with pytest.raises(ValueError):
            validated_click(values, token=token, previous=previous, now=clock)


@pytest.mark.parametrize(
    "uri",
    [
        "https://example.com/file",
        "file://remote/path",
        "file:///dev/null",
        "file:///tmp/%00",
        "file:///tmp/?q=1",
    ],
)
def test_rejects_nonlocal_or_invalid(uri):
    with pytest.raises((ValueError, OSError)):
        validated_click(["a" * 64, uri, 1, 100], token="a" * 64, previous=0, now=101)


def test_missing_and_symlink(tmp_path):
    source = tmp_path / "source"
    source.write_text("test")
    link = tmp_path / "link"
    link.symlink_to(source)
    for path in (link, tmp_path / "missing", tmp_path):
        with pytest.raises(ValueError):
            validated_click(["a" * 64, path.as_uri(), 1, 100], token="a" * 64, previous=0, now=101)


def test_real_quick_background_conversion_after_collapse(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("QT_QUICK_BACKEND", "software")
    from PIL import Image
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication

    from filewheel.converters import ConversionManager, Registry
    from filewheel.converters.images import PillowEngine
    from filewheel.ui.desktop import DesktopApplication

    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    source = tmp_path / "source æøå.png"
    Image.new("RGBA", (16, 20), (20, 40, 60, 0)).save(source)
    original = source.read_bytes()
    manager = ConversionManager(Registry((PillowEngine(),)))
    host = DesktopApplication(manager=manager, ui_backend="quick", auto_start=False)
    loop = QEventLoop()
    outcomes = []
    host.conversions.completed.connect(
        lambda result, error: (outcomes.append((result, error)), loop.quit())
    )
    assert host.present_explicit([str(source)], (200, 200), source="dolphin_click")
    host.popup.session.choose(0)
    host.popup.session.choose(0)
    host.popup.collapse_progress()
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(host.conversions.cancel)
    timeout.start(10000)
    loop.exec()
    timeout.stop()
    assert outcomes and outcomes[0][1] is None
    assert outcomes[0][0].path.is_file()
    assert source.read_bytes() == original
    assert host.conversions.job is None
    host.popup.dismiss()
