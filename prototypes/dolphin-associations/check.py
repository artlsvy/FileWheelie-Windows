"""Read KDE's real offer order before/setup/remove in isolated XDG directories."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from filewheel.platforms.linux import dolphin_associations as d
from filewheel.platforms.linux import integration


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise SystemExit("Refusing to replace a report")
    probe = args.probe.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="fw-kde-mime-check-") as temporary:
        root = Path(temporary)
        os.environ.update(
            XDG_CONFIG_HOME=str(root / "config"),
            XDG_DATA_HOME=str(root / "data"),
            XDG_CACHE_HOME=str(root / "cache"),
            XDG_CURRENT_DESKTOP="KDE",
        )
        apps = root / "data/applications"
        apps.mkdir(parents=True)
        for app in ["viewer", "editor"]:
            (apps / (app + ".desktop")).write_text(
                "[Desktop Entry]\nType=Application\nName="
                + app
                + "\nExec=/bin/true %f\nMimeType=image/png;application/pdf;\n"
            )
        command = ["/opt/filewheel/filewheel"]
        for path, value in integration.entries(command).items():
            integration.atomic_write(path, value)
        generic, _ = d._targets()
        generic.parent.mkdir(parents=True, exist_ok=True)
        generic.write_text(
            "[Default Applications]\nimage/png=viewer.desktop;editor.desktop;\n"
            "application/pdf=viewer.desktop;editor.desktop;\n"
        )

        def offers():
            return json.loads(
                subprocess.check_output(
                    [str(probe), "image/png", "application/pdf"], env=d._environment(), text=True
                )
            )

        d.refresh()
        before = offers()
        result = d.install(command, mimes=["image/png", "application/pdf"])
        installed = offers()
        assert result["configured"] == ["application/pdf", "image/png"]
        assert all(order[:2] == ["viewer.desktop", d.DESKTOP_ID] for order in installed.values())
        d.remove(command)
        removed = offers()
        assert all(order[:2] == ["viewer.desktop", "editor.desktop"] for order in removed.values())
        report = {
            "before": before,
            "installed": installed,
            "removed": removed,
            "default_unchanged": True,
            "isolated_xdg": True,
            "passed": True,
        }
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
