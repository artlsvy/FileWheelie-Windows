"""Optional current-user startup registration; never installed automatically."""
import subprocess

from filewheel.paths import launch_command
from filewheel.platforms.windows.native import require_windows

KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
NAME = 'Filewheel'


def _commands():
    parts = launch_command('--tray')
    return {subprocess.list2cmdline(parts),
            '"' + parts[0] + '" ' + subprocess.list2cmdline(parts[1:])}


def is_enabled():
    require_windows()
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_READ) as key:
            command, kind = winreg.QueryValueEx(key, NAME)
        return kind == winreg.REG_SZ and command in _commands()
    except FileNotFoundError:
        return False


def configure(action):
    require_windows()
    if action not in ('install', 'remove'):
        raise ValueError('Unknown startup action')
    import winreg
    command = subprocess.list2cmdline(launch_command('--tray'))
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_READ) as key:
            try:
                existing, kind = winreg.QueryValueEx(key, NAME)
            except FileNotFoundError:
                existing = None
    except FileNotFoundError:
        existing = None
    if existing is not None and (kind != winreg.REG_SZ or existing not in _commands()):
        raise RuntimeError('Startup entry differs; refusing to overwrite or remove it')
    if action == 'remove' and existing is None:
        return
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as key:
        if action == 'install':
            winreg.SetValueEx(key, NAME, 0, winreg.REG_SZ, command)
        else:
            winreg.DeleteValue(key, NAME)
