"""Opt-in exact-URI test for the private patched Dolphin. No conversion code.

Run with system Python/PyGObject. Only messages from the exact child executable,
with this run's secret, fresh monotonic timestamp and an owned fixture URI pass.
"""

import argparse
import hmac
import json
import os
import secrets
import signal
import subprocess
import tempfile
from pathlib import Path
from time import monotonic_ns
from urllib.parse import unquote_to_bytes, urlsplit


def validate(payload, *, token, previous, now, fixtures):
    if not isinstance(payload, tuple) or len(payload) != 4:
        raise ValueError("invalid_payload")
    supplied, uri, sequence, captured = payload
    if not isinstance(supplied, str) or not hmac.compare_digest(
        supplied.encode("utf-8"), token.encode("utf-8")
    ):
        raise ValueError("wrong_run")
    if (
        type(sequence) is not int
        or sequence <= previous
        or type(captured) is not int
        or not 0 <= now - captured <= 2_000_000_000
    ):
        raise ValueError("stale_or_replayed")
    if not isinstance(uri, str) or len(uri) > 8192:
        raise ValueError("invalid_uri")
    parsed = urlsplit(uri)
    if parsed.scheme != "file" or parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("nonlocal_uri")
    path = Path(unquote_to_bytes(parsed.path).decode("utf-8", errors="strict"))
    if path not in fixtures or path.is_symlink() or not path.is_file():
        raise ValueError("not_an_owned_fixture")
    return path, sequence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dolphin", type=Path, required=True)
    parser.add_argument("--library-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=180)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 300 or args.report.exists():
        parser.error("Use a new report and a duration from 1 to 300 seconds")
    executable = args.dolphin.resolve(strict=True)
    runtime = Path("/run/user") / str(os.getuid())
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=" + str(runtime / "bus")
    import gi

    gi.require_version("Gio", "2.0")
    from gi.repository import Gio, GLib

    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    token = secrets.token_hex(32)
    result = {
        "accepted": [],
        "rejections": [],
        "hardware_source": "requires user confirmation",
        "conversion_started": False,
    }
    loop = GLib.MainLoop()
    signal.signal(signal.SIGINT, lambda *_: loop.quit())
    sequence = 0
    child = None
    with tempfile.TemporaryDirectory(prefix="filewheel-clicked-uri-") as folder:
        root = Path(folder)
        fixtures = set()
        for directory in ("Tab A", "Tab B"):
            (root / directory).mkdir()
            for name in ("previous selection.txt", "report.txt", "report.csv", "unicode-æøå.txt"):
                path = root / directory / name
                path.write_text("Harmless Filewheel test fixture\n")
                fixtures.add(path)

        def receive(connection, sender, path, interface, signal, parameters):
            nonlocal sequence
            try:
                reply = bus.call_sync(
                    "org.freedesktop.DBus",
                    "/org/freedesktop/DBus",
                    "org.freedesktop.DBus",
                    "GetConnectionUnixProcessID",
                    GLib.Variant("(s)", (sender,)),
                    None,
                    Gio.DBusCallFlags.NONE,
                    500,
                    None,
                ).unpack()[0]
                if (
                    child is None
                    or reply != child.pid
                    or Path(f"/proc/{reply}/exe").resolve() != executable
                ):
                    raise ValueError("wrong_sender")
                target, sequence = validate(
                    parameters.unpack(),
                    token=token,
                    previous=sequence,
                    now=monotonic_ns(),
                    fixtures=fixtures,
                )
                result["accepted"].append(
                    {
                        "relative_path": str(target.relative_to(root)),
                        "sequence": sequence,
                        "source": "patched_dolphin_click",
                    }
                )
                print("ACCEPTED exact clicked URI:", target.relative_to(root), flush=True)
            except (ValueError, OSError, GLib.Error) as error:
                result["rejections"].append(type(error).__name__)
                print("REJECTED:", type(error).__name__, flush=True)

        subscription = bus.signal_subscribe(
            None,
            "org.filewheel.DolphinProbe",
            "MiddleClicked",
            "/org/filewheel/DolphinProbe",
            None,
            Gio.DBusSignalFlags.NONE,
            receive,
        )
        env = dict(
            os.environ,
            XDG_RUNTIME_DIR=str(runtime),
            WAYLAND_DISPLAY="wayland-0",
            QT_QPA_PLATFORM="wayland",
            FILEWHEEL_DOLPHIN_PROBE_DEST=bus.get_unique_name(),
            FILEWHEEL_DOLPHIN_PROBE_TOKEN=token,
            LD_LIBRARY_PATH=str(args.library_dir.absolute()),
        )
        for key, directory in (
            ("XDG_CONFIG_HOME", "config"),
            ("XDG_STATE_HOME", "state"),
            ("XDG_CACHE_HOME", "cache"),
            ("XDG_DATA_HOME", "data"),
        ):
            (root / directory).mkdir()
            env[key] = str(root / directory)
        try:
            with (root / "dolphin.log").open("w") as output:
                child = subprocess.Popen(
                    [str(executable), "--new-window", str(root / "Tab A"), str(root / "Tab B")],
                    env=env,
                    stdout=output,
                    stderr=output,
                )
                print(
                    "READY: private Dolphin test window. Middle-click report.txt, unicode-æøå.txt,",
                    "and report.csv in BOTH tabs. No conversion will run.",
                    flush=True,
                )

                def check_child():
                    if child.poll() is not None:
                        result["startup_or_exit_note"] = "Private Dolphin exited before deadline"
                        print("Private Dolphin exited; stopping probe.", flush=True)
                        loop.quit()
                        return False
                    return True

                GLib.timeout_add_seconds(1, check_child)
                GLib.timeout_add_seconds(args.seconds, lambda: (loop.quit(), False)[1])
                loop.run()
        finally:
            bus.signal_unsubscribe(subscription)
            if child is not None:
                if child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=3)
                result["child_exit"] = child.returncode
    with args.report.open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
    print("Report:", args.report, flush=True)


if __name__ == "__main__":
    main()
