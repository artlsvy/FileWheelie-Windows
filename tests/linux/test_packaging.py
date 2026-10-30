"""Build contracts that can be checked without creating binaries or network access."""

import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_linux_lock_has_explicit_hashes_and_platform_dependencies():
    lock = (ROOT / "packaging/linux/python-py314-x86_64.lock").read_text()
    lines = [line for line in lock.splitlines() if line and not line.startswith("#")]
    packages = []
    for line in lines:
        assert re.fullmatch(r"[A-Za-z0-9_.-]+==[^ ]+ --hash=sha256:[a-f0-9]{64}", line)
        packages.append(line.split("==")[0].lower().replace("_", "-"))
    assert len(packages) == len(set(packages))
    assert {
        "pyside6-essentials",
        "pillow",
        "pymupdf",
        "pdf2docx",
        "markitdown",
        "pyinstaller",
    } <= set(packages)
    assert "comtypes" not in packages
    assert len(lines) == len(packages)


def test_pinned_tool_and_notice_metadata():
    pins = json.loads((ROOT / "packaging/linux/artifacts.json").read_text())
    for item in (pins["python"], pins["appimagetool"], pins["runtime"]):
        assert item["url"].startswith("https://")
        assert re.fullmatch("[a-f0-9]{64}", item["sha256"])
    for name, value in pins["pandoc_notices"].items():
        data = (ROOT / "packaging/linux/notices/pandoc-3.12.1" / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == value["sha256"]


def test_build_import_has_no_mutating_side_effects():
    spec = importlib.util.spec_from_file_location("linux_build", ROOT / "packaging/linux/build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert "%f" in module.desktop("filewheel")
    assert "--gui" not in module.desktop("filewheel")  # launcher also works without a file
    assert "<svg" in module.icon()


def test_frozen_release_does_not_accept_missing_converter_family():
    import pytest

    spec = importlib.util.spec_from_file_location(
        "linux_verify", ROOT / "packaging/linux/verify_smoke.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    results = [{"engine": name, "ok": True} for name in module.REQUIRED]
    results.extend(
        [
            {"quick_qml_render": True, "ok": True},
            {"quick_progress_render": True, "ok": True},
            {"frozen_spawn_cancel_retry": True, "ok": True},
            {"libreoffice_source": "bundled", "ok": True},
            {"pandoc_source": "bundled", "ok": True},
            {"bundled_ffmpeg": "/bundle/ffmpeg", "ok": True},
        ]
    )
    module.verify({"ok": True, "results": results})
    for missing in module.REQUIRED:
        with pytest.raises(RuntimeError, match="families missing"):
            module.verify(
                {"ok": True, "results": [item for item in results if item.get("engine") != missing]}
            )
    with pytest.raises(RuntimeError, match="self-test failed"):
        module.verify({"ok": False, "results": results})
