# -*- mode: python ; coding: utf-8 -*-
"""Linux CPython 3.14 x86_64 onedir; no Windows resources or COM dependencies."""

import os
import re
import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

if sys.platform != "linux" or sys.version_info[:2] != (3, 14):
    raise SystemExit("Build the Linux spec with Linux CPython 3.14")
os.environ["ORT_DISABLE_TELEMETRY"] = "1"
root = Path(SPECPATH).resolve().parents[1]
datas = [(str(path), "filewheel/ui/qml") for path in (root / "src/filewheel/ui/qml").glob("*.qml")]
datas.append((str(root / "LICENSE"), "."))
binaries = []
hiddenimports = collect_submodules(
    "filewheel", filter=lambda name: not name.startswith("filewheel.platforms.windows")
)
hiddenimports += ["PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtNetwork", "PySide6.QtDBus"]
for package in (
    "pillow_heif",
    "pymupdf",
    "pdf2docx",
    "markitdown",
    "magika",
    "cv2",
    "docx",
    "pptx",
    "pdfminer",
    "pdfplumber",
    "pypdfium2",
):
    data, binary, imports = collect_all(package)
    datas += data
    binaries += binary
    hiddenimports += imports
binaries += collect_dynamic_libs("onnxruntime")
datas += collect_data_files("onnxruntime", includes=["**/*.json", "**/*.onnx", "**/*.txt"])
hiddenimports += [
    "onnxruntime",
    "onnxruntime.capi._pybind_state",
    "onnxruntime.capi.onnxruntime_pybind11_state",
    "fitz",
    "pandas",
    "openpyxl",
    "mammoth",
    "lxml.etree",
]
for line in (root / "packaging/linux/python-py314-x86_64.lock").read_text().splitlines():
    match = re.match(r"^([A-Za-z0-9_.-]+)==", line)
    if match:
        datas += copy_metadata(match.group(1))
analysis = Analysis(
    [str(root / "packaging/entry.py")],
    pathex=[str(root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    runtime_hooks=[str(root / "packaging/runtime_hook.py")],
    excludes=[
        "filewheel.platforms.windows",
        "comtypes",
        "tkinter",
        "torch",
        "tensorflow",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
    ],
    noarchive=False,
)
# libmvec belongs to the host glibc family; do not mix its private ABI with
# a newer host libc/libm. Linux targets already provide this alongside glibc.
analysis.binaries = [
    entry for entry in analysis.binaries if not Path(entry[0]).name.startswith("libmvec.so")
]
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="filewheel",
    console=True,
    debug=False,
    strip=False,
    upx=False,
    contents_directory="_internal",
)
collection = COLLECT(
    exe, analysis.binaries, analysis.datas, name="Filewheel", strip=False, upx=False
)
