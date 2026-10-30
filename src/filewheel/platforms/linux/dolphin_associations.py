"""Stock Dolphin middle-click via XDG MIME order, with per-entry rollback.

No input hook: Dolphin supplies the actual clicked file through our desktop entry.
Only installer/explicit management commands change preferences, never a popup.
"""

import fcntl
import json
import os
import re
import shutil
import stat
import subprocess
from functools import wraps
from pathlib import Path
from time import monotonic

from filewheel.platforms.linux.integration import atomic_write
from filewheel.platforms.linux.xdg import config_root

DESKTOP_ID = "org.filewheel.Filewheel.desktop"
GROUPS = ("Default Applications", "Added Associations", "Removed Associations")
LIMIT = 1024 * 1024


def _targets():
    root = config_root().parent
    return root / "mimeapps.list", root / "kde-mimeapps.list"


def _journal_path():
    return config_root() / "dolphin-associations.json"


def _text(path):
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise RuntimeError("Preserving a symlink in Dolphin preference paths")
    if not path.exists():
        return ""
    if not path.is_file() or path.stat().st_size > LIMIT:
        raise RuntimeError("Dolphin preference file is not a bounded regular file")
    with path.open(encoding="utf-8", newline="") as stream:
        return stream.read(LIMIT + 1)


def _exclusive(function):
    @wraps(function)
    def locked(*args, **kwargs):
        lock = config_root() / "dolphin-associations.lock"
        _text(lock)
        lock.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            metadata = os.fstat(descriptor)
            if metadata.st_uid != os.getuid() or not stat.S_ISREG(metadata.st_mode):
                raise RuntimeError("Preserving a foreign Dolphin setup lock")
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError(
                    "Another Dolphin setup is running; retry when it finishes"
                ) from error
            return function(*args, **kwargs)
        finally:
            os.close(descriptor)

    return locked


def _location(text, group, key):
    current, found = None, []
    for index, line in enumerate(text.splitlines(keepends=True)):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1]
        elif current == group and "=" in line and not stripped.startswith(("#", ";")):
            name, value = line.rstrip("\r\n").split("=", 1)
            if name.strip() == key:
                found.append((index, value))
    if len(found) > 1:
        raise RuntimeError("Duplicate MIME entries require manual reconciliation")
    return found[0] if found else (None, None)


def _value(text, group, key):
    return _location(text, group, key)[1]


def _replace(text, group, key, value):
    index, _ = _location(text, group, key)
    lines = text.splitlines(keepends=True)
    ending = "\r\n" if "\r\n" in text else "\n"
    if index is not None:
        if value is None:
            del lines[index]
        else:
            lines[index] = key + "=" + value + ending
        return "".join(lines)
    if value is None:
        return text
    current = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if current == group:
                lines.insert(index, key + "=" + value + ending)
                return "".join(lines)
            current = stripped[1:-1]
    if text and not text.endswith(("\n", "\r")):
        text += ending
    if current != group:
        text += ending + "[" + group + "]" + ending
    return text + key + "=" + value + ending


def _ids(value):
    return list(dict.fromkeys(part.strip() for part in (value or "").split(";") if part.strip()))


def _serialized(values):
    return ";".join(values) + ";" if values else None


def _without_us(value):
    return _serialized([item for item in _ids(value) if item != DESKTOP_ID])


def _environment():
    from filewheel.libreoffice_bundle import external_tool_environment

    with external_tool_environment() as env:
        # Query KDE's desktop-specific defaults even from an SSH shell.
        if (
            not env.get("XDG_MENU_PREFIX")
            and Path("/etc/xdg/menus/plasma-applications.menu").is_file()
        ):
            env["XDG_MENU_PREFIX"] = "plasma-"
        return dict(env, LC_ALL="C.UTF-8", XDG_CURRENT_DESKTOP="KDE")


def _run(arguments, timeout=3):
    result = subprocess.run(
        arguments,
        env=_environment(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode or len(result.stdout) > LIMIT:
        raise RuntimeError("Dolphin integration helper failed: " + Path(arguments[0]).name)
    return result.stdout


def available():
    if not all(shutil.which(name) for name in ("dolphin", "kbuildsycoca6", "gio")):
        return False
    desktop = os.getenv("XDG_CURRENT_DESKTOP", "")
    if desktop:
        return bool({"kde", "plasma"} & set(desktop.lower().split(":")))
    # KDE desktop variables may be missing in SSH. Ask the current session bus;
    # no Wayland input access or desktop modifications are involved.
    if not shutil.which("gdbus"):
        return False
    try:
        return (
            _run(
                [
                    "gdbus",
                    "call",
                    "--session",
                    "--dest",
                    "org.freedesktop.DBus",
                    "--object-path",
                    "/org/freedesktop/DBus",
                    "--method",
                    "org.freedesktop.DBus.NameHasOwner",
                    "org.kde.KWin",
                ],
                timeout=1,
            ).strip()
            == "(true,)"
        )
    except OSError, RuntimeError, subprocess.TimeoutExpired:
        return False


def supported_mimes(registry=None):
    from PySide6.QtCore import QMimeDatabase

    if registry is None:
        from filewheel.converters.registry import default_registry

        registry = default_registry()
    database = QMimeDatabase()
    result = set()
    for extension in {cap.input_extension.lower() for cap in registry.capabilities}:
        mime = database.mimeTypeForFile("input" + extension, QMimeDatabase.MatchExtension)
        if mime.isValid() and mime.name() not in {
            "application/octet-stream",
            "inode/directory",
            "application/x-executable",
            "application/x-sharedlib",
            "application/x-desktop",
        }:
            result.add(mime.name())
    return sorted(result)


def query_apps(mime):
    output = _run(["gio", "mime", mime])
    primary, apps, collecting = None, [], False
    for line in output.splitlines():
        if line.startswith("Default application for ") and ": " in line:
            primary = line.split(": ", 1)[1].strip()
        elif line == "Registered applications:":
            collecting = True
        elif line == "Recommended applications:":
            collecting = False
        elif collecting and line.startswith("\t"):
            apps.append(line.strip())
    return primary, list(dict.fromkeys(apps))


def refresh():
    _run(["kbuildsycoca6", "--noincremental"], timeout=12)


def _journal(command):
    text = _text(_journal_path())
    if not text:
        return {"schema": 1, "command": list(command), "changes": []}
    try:
        value = json.loads(text)
    except ValueError as error:
        raise RuntimeError("Invalid Dolphin ownership journal; preserving preferences") from error
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "command", "changes"}
        or value["schema"] != 1
        or value["command"] != list(command)
        or not isinstance(value["changes"], list)
        or len(value["changes"]) > 1024
    ):
        raise RuntimeError("Preserving Dolphin state owned by another installation")
    for change in value["changes"]:
        if (
            not isinstance(change, dict)
            or set(change) != {"path", "group", "mime", "before", "after"}
            or change["path"] not in {str(path) for path in _targets()}
            or change["group"] not in GROUPS
            or not isinstance(change["mime"], str)
            or not re.fullmatch(r"[a-zA-Z0-9!#$&^_.+-]+/[a-zA-Z0-9!#$&^_.+-]+", change["mime"])
            or any(
                item is not None and (not isinstance(item, str) or "\n" in item or "\r" in item)
                for item in (change["before"], change["after"])
            )
        ):
            raise RuntimeError("Invalid Dolphin ownership journal; preserving preferences")
    return value


@_exclusive
def install(command, *, mimes=None, query=None, update=None, force=False):
    from filewheel import preferences

    if not force and not preferences.dolphin_enabled():
        return {"configured": [], "skipped": {"all": "Disabled by user"}}
    if not available():
        return {
            "configured": [],
            "skipped": {"all": "Automatic setup requires Plasma, Dolphin, gio and kbuildsycoca6"},
        }
    from filewheel.platforms.linux.integration import preflight

    launcher = next(iter(preflight(command)))
    if not launcher.is_file():
        raise RuntimeError("Install Filewheel desktop integration before enabling Dolphin")
    mimes = supported_mimes() if mimes is None else sorted(set(mimes))
    query = query or query_apps
    update = update or refresh
    journal = _journal(command)
    generic, kde = _targets()
    texts = {path: _text(path) for path in (generic, kde)}
    originals = dict(texts)
    changes = {(c["path"], c["group"], c["mime"]): c for c in journal["changes"]}
    for key, change in list(changes.items()):
        if change["mime"] not in mimes:
            path = Path(change["path"])
            current = _value(texts[path], change["group"], change["mime"])
            if current == change["after"]:
                restored = change["before"]
                if change["group"] != "Removed Associations":
                    restored = _without_us(restored)
            elif current == change["before"] or change["group"] == "Removed Associations":
                restored = current
            else:
                restored = _without_us(current)
            texts[path] = _replace(texts[path], change["group"], change["mime"], restored)
            del changes[key]
    configured, skipped = [], {}
    deadline = monotonic() + 10
    for mime in mimes:
        if not re.fullmatch(r"[a-zA-Z0-9!#$&^_.+-]+/[a-zA-Z0-9!#$&^_.+-]+", mime):
            raise ValueError("Invalid MIME type")
        if monotonic() > deadline:
            skipped[mime] = "Application lookup budget exceeded"
            continue
        try:
            primary, _apps = query(mime)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            skipped[mime] = type(error).__name__ + ": handler lookup failed"
            continue
        if not primary or primary == DESKTOP_ID:
            skipped[mime] = (
                "No existing handler"
                if not primary
                else "Filewheel is already the default; preserving existing order"
            )
            continue
        if DESKTOP_ID in _ids(_value(texts[generic], "Removed Associations", mime)) and not force:
            skipped[mime] = "Excluded by user"
            continue
        default_path = (
            kde if _value(texts[kde], "Default Applications", mime) is not None else generic
        )
        # Both groups matter: KDE gives Default Applications precedence, including
        # fallback apps. Keep the current primary first and all other apps behind us.
        assignments = []
        for path, group in (
            (default_path, "Default Applications"),
            (generic, "Added Associations"),
        ):
            existing = _ids(_value(texts[path], group, mime))
            if any(
                not app.endswith(".desktop")
                or any(char in app for char in ("\n", "\r", "\0", "/", "\\"))
                for app in existing + [primary]
            ):
                skipped[mime] = "Unsafe desktop ID; preserving existing preferences"
                break
            # Do not pin the desktop's inferred app order from GIO: KDE may rank
            # those differently. Preserve only each group's explicit user order.
            order = [primary, DESKTOP_ID] + [
                app for app in existing if app not in (primary, DESKTOP_ID)
            ]
            assignments.append((path, group, _serialized(order)))
        if len(assignments) != 2:
            continue
        if force and DESKTOP_ID in _ids(_value(texts[generic], "Removed Associations", mime)):
            assignments.append(
                (
                    generic,
                    "Removed Associations",
                    _without_us(_value(texts[generic], "Removed Associations", mime)),
                )
            )
        for path, group, after in assignments:
            before = _value(texts[path], group, mime)
            key = str(path), group, mime
            previous = changes.get(key)
            if previous and before == previous["after"]:
                before = previous["before"]
            changes[key] = {
                "path": str(path),
                "group": group,
                "mime": mime,
                "before": before,
                "after": after,
            }
            texts[path] = _replace(texts[path], group, mime, after)
        configured.append(mime)
    original_changes = journal["changes"]
    journal["changes"] = list(changes.values())
    # Write-ahead ownership permits recovery if a process stops between files.
    if journal["changes"] or original_changes:
        _text(_journal_path())
        pending = dict(
            journal,
            changes=list(changes.values())
            + [c for c in original_changes if (c["path"], c["group"], c["mime"]) not in changes],
        )
        atomic_write(_journal_path(), json.dumps(pending, indent=2) + "\n", 0o600)
    for path, value in texts.items():
        if value != originals[path]:
            if _text(path) != originals[path]:
                raise RuntimeError("MIME preferences changed concurrently; retry setup")
            atomic_write(path, value, 0o600)
    if original_changes and original_changes != journal["changes"]:
        atomic_write(_journal_path(), json.dumps(journal, indent=2) + "\n", 0o600)
    if configured or texts != originals:
        update()
    return {"configured": configured, "skipped": skipped}


@_exclusive
def remove(command, *, update=None):
    journal = _journal(command)
    if not journal["changes"]:
        return
    texts = {path: _text(path) for path in _targets()}
    originals = dict(texts)
    for change in journal["changes"]:
        path, group, mime = Path(change["path"]), change["group"], change["mime"]
        current = _value(texts[path], group, mime)
        if current == change["after"]:
            restored = change["before"]
            if group != "Removed Associations":
                restored = _without_us(restored)
        elif current == change["before"]:
            continue  # The journal was written but this entry was never changed.
        elif group != "Removed Associations":
            restored = _without_us(current)  # Preserve the user's later edits.
        else:
            continue
        texts[path] = _replace(texts[path], group, mime, restored)
    for path, value in texts.items():
        if value != originals[path]:
            if _text(path) != originals[path]:
                raise RuntimeError("MIME preferences changed concurrently; retry removal")
            atomic_write(path, value, 0o600)
    _journal_path().unlink(missing_ok=True)
    if journal["changes"] and shutil.which("kbuildsycoca6"):
        (update or refresh)()


def status():
    from filewheel import preferences

    text = _text(_journal_path())
    if not text:
        return {"configured": [], "enabled": preferences.dolphin_enabled()}
    try:
        value = json.loads(text)
        command = value["command"]
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeError("Invalid Dolphin ownership journal; preserving preferences") from error
    journal = _journal(command)
    managed = sorted({c["mime"] for c in journal["changes"]})
    configured = []
    for change in journal["changes"]:
        if change["group"] == "Default Applications":
            current = _ids(_value(_text(Path(change["path"])), change["group"], change["mime"]))
            if len(current) >= 2 and current[1] == DESKTOP_ID and current[0] != DESKTOP_ID:
                configured.append(change["mime"])
    return {
        "configured": sorted(configured),
        "managed": managed,
        "enabled": preferences.dolphin_enabled(),
    }
