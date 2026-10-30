"""Native paths, provenance, platform ownership and real spawned conversion."""

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest.mock import patch

import pytest

from filewheel.core.controller import InvocationController
from filewheel.core.explicit_paths import FileCheck, validate_explicit_paths
from filewheel.core.models import TargetResolution
from filewheel.platforms.linux import startup
from filewheel.platforms.linux.paths import inspect_file, validate_paths


@pytest.mark.parametrize(
    "name",
    [
        "file.txt",
        "unicode-æøå.txt",
        "file with spaces.txt",
        "CON.txt",
        "a:b?*.txt",
        'quoted"$%.txt',
    ],
)
def test_native_filename_and_controller(tmp_path, name):
    source = tmp_path / name
    source.write_text("unchanged")
    controller = InvocationController(path_flavour="posix")
    result = controller.handle_explicit(
        [str(source)], point=(42, -10), timestamp=1, inspect_file=inspect_file
    )
    assert result.rejection is None
    assert result.target.path == PurePosixPath(source)
    assert result.target.source == "linux_explicit"
    assert source.read_text() == "unchanged"


@pytest.mark.parametrize(
    "arguments",
    [[], ["/a", "/b"], ["relative"], ["//remote/file"], ["/tmp/../bad"], ["/tmp/"], ["nul\0file"]],
)
def test_bad_arguments(arguments):
    assert validate_paths(arguments).path is None


def test_objects_and_links(tmp_path):
    file = tmp_path / "real"
    file.write_text("test")
    link = tmp_path / "link"
    link.symlink_to(file)
    parent = tmp_path / "alias"
    parent.symlink_to(tmp_path, target_is_directory=True)
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    for path in (tmp_path, tmp_path / "missing", link, parent / "real", fifo):
        assert validate_paths([str(path)]).path is None


def test_cancel_during_inspection(tmp_path):
    controller = InvocationController(path_flavour="posix")

    def inspect(path):
        controller.cancel()
        return FileCheck(True, True)

    assert (
        controller.handle_explicit(
            [str(tmp_path / "a")], point=(0, 0), timestamp=1, inspect_file=inspect
        ).rejection
        == "invocation_cancelled"
    )


def test_windows_rules_still_distinct():
    inspector = lambda _: FileCheck(True, True)
    assert validate_explicit_paths(["/tmp/file"], inspector).path is None
    assert validate_explicit_paths(["C:/test/file.txt"], inspector).path == PureWindowsPath(
        "C:/test/file.txt"
    )
    assert validate_explicit_paths(["C:/test/CON.txt"], inspector).path is None
    with pytest.raises(ValueError):
        TargetResolution(PurePosixPath("/a"), 0, (0, 0), 1, source="explorer_hover")
    with pytest.raises(ValueError):
        TargetResolution(PureWindowsPath("C:/a"), 0, (0, 0), 1, source="linux_explicit")


def test_startup_ownership_and_xdg(tmp_path):
    with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}):
        assert not startup.is_enabled()
        startup.configure("install")
        assert startup.is_enabled()
        entry = tmp_path / "autostart/org.filewheel.Filewheel.desktop"
        entry.write_text("unrelated entry")
        for action in ("install", "remove"):
            with pytest.raises(RuntimeError):
                startup.configure(action)
        assert entry.read_text() == "unrelated entry"
        entry.unlink()
        startup.configure("install")
        startup.configure("remove")
        assert not entry.exists()


def test_real_spawned_png_collision_and_source(tmp_path):
    from PIL import Image

    from filewheel.converters import ConversionManager, Registry
    from filewheel.converters.images import PillowEngine
    from filewheel.converters.process_worker import run_in_process

    file = tmp_path / "résumé source.png"
    Image.new("RGBA", (8, 9), (10, 30, 50, 0)).save(file)
    digest = hashlib.sha256(file.read_bytes()).digest()
    manager = ConversionManager(Registry((PillowEngine(),)))
    a = run_in_process(
        manager, str(file), ".jpg", progress=lambda *_: None, cancel=__import__("threading").Event()
    )
    b = run_in_process(
        manager, str(file), ".jpg", progress=lambda *_: None, cancel=__import__("threading").Event()
    )
    assert a.path != b.path
    with Image.open(a.path) as image:
        assert image.size == (8, 9)
    assert hashlib.sha256(file.read_bytes()).digest() == digest
    assert not list(tmp_path.glob(".filewheel-*"))


def _worker_with_tool(marker):
    os.setsid()
    process = subprocess.Popen(
        [sys.executable, "-c", "import time;time.sleep(60)"], process_group=0
    )
    Path(marker).write_text(str(process.pid))
    time.sleep(60)


def test_force_stop_owned_session_including_tool_group(tmp_path):
    import multiprocessing

    from filewheel.converters.process_worker import _stop_owned_worker

    marker = tmp_path / "tool.pid"
    worker = multiprocessing.get_context("spawn").Process(
        target=_worker_with_tool, args=(str(marker),)
    )
    worker.start()
    try:
        deadline = time.monotonic() + 8
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert marker.exists()
        pid = int(marker.read_text())
        _stop_owned_worker(worker)
        assert not worker.is_alive()
        stat = Path(f"/proc/{pid}/stat")
        assert not stat.exists() or stat.read_text().rsplit(")", 1)[1].split()[0] == "Z"
    finally:
        if worker.is_alive():
            worker.kill()
            worker.join(3)
