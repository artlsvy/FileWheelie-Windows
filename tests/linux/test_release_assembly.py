import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "release", Path(__file__).parents[2] / "scripts/assemble_release.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize("nested", [False, True])
def test_layouts(tmp_path, nested):
    root = tmp_path / "artifacts"
    for platform, names in [
        ("linux", ["Filewheel-Linux-x86_64.AppImage", "BUILD-INFO.json"]),
        ("windows", ["FilewheelSetup.exe", "INSTALLER-BUILD-INFO.json"]),
    ]:
        folder = root / platform / ("home/runner/work/build" if nested else "")
        folder.mkdir(parents=True)
        for name in names:
            (folder / name).write_text(name)
    output = tmp_path / "release"
    module.assemble(root, output)
    assert len(list(output.iterdir())) == 5
    assert len((output / "SHA256SUMS.txt").read_text().splitlines()) == 2


def test_missing_artifacts_fail_without_partial_release(tmp_path):
    with pytest.raises(ValueError):
        module.assemble(tmp_path / "missing", tmp_path / "release")
    assert not (tmp_path / "release").exists()
