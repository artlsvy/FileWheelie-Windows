# -*- mode: python ; coding: utf-8 -*-
"""Windows CPython 3.14 amd64 onedir bundle. Build on Windows, never cross-freeze."""

import os
import re
import sys
from pathlib import Path

if sys.platform != "win32" or sys.version_info[:2] != (3, 14):
    raise SystemExit("Filewheel packaging requires Windows CPython 3.14")

# Collection imports Magika/ONNX package metadata on the build machine too.
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

root = Path(SPECPATH).resolve().parent
onefile = os.environ.get('FILEWHEEL_BUILD_ONEFILE') == '1'
binaries = []
datas = [(str(root / "src/filewheel/platforms/windows/sendto_shortcut.ps1"),
          "filewheel/platforms/windows")]
# Python package data is not sufficient for Analysis(entry.py). Preserve the
# local relative QML path used by GlassPopup, including its Lens component.
datas += [(str(path), "filewheel/ui/qml") for path in (root / "src/filewheel/ui/qml").glob("*.qml")]
hiddenimports = collect_submodules("filewheel")
if onefile:
    # Include the COMPLETE native tools in the archive, not external siblings.
    for tool in ('libreoffice', 'pandoc'):
        source = Path(os.environ['FILEWHEEL_BUNDLE_' + tool.upper()])
        if not source.is_dir():
            raise SystemExit('Complete bundled tool directory required: ' + tool)
        datas.append((str(source), 'tools/' + tool))
# QtQml's pinned PyInstaller hook collects the installed Essentials QML plugin
# tree; QML-only imports such as QtQuick.Shapes are not Python module names.
hiddenimports += ["PySide6.QtQuick", "PySide6.QtQml"]

# Dynamic imports and model/templates/native codecs are explicit. Standard
# PyInstaller hooks handle numpy/pandas/lxml and PySide6 Essentials/qwindows.
for package in ("pillow_heif", "pymupdf", "pdf2docx", "markitdown", "magika",
                "cv2", "docx", "pptx", "pdfminer", "pdfplumber", "pypdfium2"):
    package_datas, package_binaries, package_imports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_imports

# Avoid collecting ONNX training/quantization integrations or optional torch.
# The inference binding/providers and model files are sufficient for Magika.
binaries += collect_dynamic_libs("onnxruntime")
datas += collect_data_files("onnxruntime", includes=["**/*.json", "**/*.onnx", "**/*.txt"])
hiddenimports += ["onnxruntime", "onnxruntime.capi._pybind_state",
                  "onnxruntime.capi.onnxruntime_pybind11_state", "fitz", "pandas",
                  "openpyxl", "mammoth", "lxml.etree", "PySide6.QtNetwork"]
hiddenimports += collect_submodules("comtypes", filter=lambda name: not name.startswith("comtypes.test"))

# Preserve exact distribution versions and bundled license metadata for runtime
# capability/self-test reports, including packages loaded only by dynamic APIs.
for line in (root / "packaging/windows-py314.lock").read_text(encoding="utf-8").splitlines():
    match = re.match(r"^([A-Za-z0-9_.-]+)(?:\[[^]]+\])?==", line)
    if match:
        datas += copy_metadata(match.group(1))

analysis = Analysis(
    [str(root / "packaging/entry.py")],
    pathex=[str(root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    runtime_hooks=[str(root / "packaging/runtime_hook.py")],
    excludes=["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
              "PySide6.QtWebEngineQuick", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
              "PyQt5", "PyQt6", "tkinter", "torch", "tensorflow"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz, analysis.scripts,
    *([analysis.binaries, analysis.datas] if onefile else [[]]),
    exclude_binaries=not onefile,
    name="Filewheel",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    contents_directory="_internal",
)
if not onefile:
    collection = COLLECT(exe, analysis.binaries, analysis.datas,
                         strip=False, upx=False, name="Filewheel")
