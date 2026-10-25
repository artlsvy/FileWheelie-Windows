"""Bounded exact-name evidence for grouped Explorer views, never trusted hover.

Group-local UIA identifiers are deliberately not treated as flat Shell indices.
The native view's first item anchors a real filesystem parent, automation parses
one literal child name, and a native IShellItem corroborates child and parent.
"""
import stat
from os import stat as file_stat
from pathlib import PureWindowsPath

from filewheel.core.index_mapping import _local_file_path
from filewheel.platforms.windows.name_ambiguity import probe_name_ambiguity


def grouping_key(probe, folder, ancestry):
    """Use native grouping metadata or a UIA group between item and items view."""
    try:
        c, _, guid, *_ = probe._types
        class PropertyKey(c.Structure):
            _fields_ = [('fmtid', guid), ('pid', c.c_uint32)]  # noqa: RUF012 - native struct declaration
        key = PropertyKey()
        folder.GetGroupBy(c.byref(key))
        if str(key.fmtid).strip('{}').lower() != '00000000-0000-0000-0000-000000000000':
            return f'{key.fmtid}:{key.pid}'
    except Exception:  # noqa: BLE001, S110 - optional metadata; UIA fallback below
        pass
    item = [i for i, row in enumerate(ancestry) if row.get('class_name') == 'UIItem'
            and row.get('control_type') == 50007]
    view = [i for i, row in enumerate(ancestry) if row.get('class_name') == 'UIItemsView']
    if len(item) == len(view) == 1 and any(
            row.get('control_type') == 50026 for row in ancestry[item[0] + 1:view[0]]):
        return 'uia_group'
    return None


def native_item_from_path(probe, path):
    """Create an independent native IShellItem; COM ownership stays in this STA."""
    c, w, _, *_, item_type = probe._types
    shell = c.WinDLL('shell32', use_last_error=True)
    create = shell.SHCreateItemFromParsingName
    create.argtypes = [w.LPCWSTR, c.c_void_p, c.c_void_p,
                       c.POINTER(c.POINTER(item_type))]
    create.restype = c.c_long
    result = c.POINTER(item_type)()
    status = create(path, None, c.byref(item_type._iid_), c.byref(result))
    if status < 0:
        raise OSError('Native Shell item creation failed')
    return result


def capture_grouped(probe, shell_window, ancestry, folder, browser, view_hwnd,
                    association, count, key, step):
    """Constant number of Shell lookups, independent of group/folder size."""
    rows = [row for row in ancestry if row.get('class_name') == 'UIItem'
            and row.get('control_type') == 50007]
    if len(rows) != 1 or type(count) is not int or count < 1:
        raise ValueError('No grouped file item')
    name = rows[0].get('name')
    # Validate a literal component before passing anything to the Shell parser.
    if (not isinstance(name, str) or not name or len(name) > 255
            or _local_file_path('C:\\literal\\' + name) is None
            or PureWindowsPath(name).name != name):
        raise ValueError('Invalid grouped filename')
    c, _, *_, item_type = probe._types
    document = step('group_document_folder', lambda: shell_window.Document.Folder)
    parent = step('group_folder_path', lambda: str(document.Self.Path))
    parent_path = _local_file_path(parent)
    if parent_path is None or probe._native.kernel.GetDriveTypeW(parent_path.anchor) != 3:
        raise ValueError('Grouped view is not a local filesystem folder')
    anchor = step('group_anchor_item', lambda: folder.GetItem(0, c.byref(item_type._iid_)))
    anchor_path = step('group_anchor_path', lambda: probe._path(anchor))
    anchor_attrs = step('group_anchor_attributes', lambda: anchor.GetAttributes(0x40000000))
    if (not anchor_attrs & 0x40000000 or _local_file_path(anchor_path) is None
            or PureWindowsPath(anchor_path).parent != parent_path):
        raise ValueError('Native view parent contradicts automation folder')
    item = step('group_parse_name', lambda: document.ParseName(name))
    path = step('group_parsed_path', lambda: str(item.Path))
    candidate_path = _local_file_path(path)
    if candidate_path is None or candidate_path.parent != parent_path or candidate_path.name != name:
        raise ValueError('Grouped filename is not an exact child name')
    automation = {'lookup_name': name, 'candidate_path': path,
                  'is_folder': bool(item.IsFolder), 'is_filesystem': bool(item.IsFileSystem)}
    native_item = step('group_native_item', lambda: native_item_from_path(probe, path))
    native_path = step('group_native_path', lambda: probe._path(native_item))
    native_parent = step('group_native_parent', lambda: probe._path(
        native_item.GetParent().QueryInterface(item_type)))
    attributes = step('group_native_attributes', lambda: native_item.GetAttributes(0x60000000))
    if _local_file_path(native_path) != candidate_path or _local_file_path(native_parent) != parent_path:
        raise ValueError('Grouped native child/parent mismatch')
    if (not automation['is_filesystem'] or automation['is_folder']
            or not attributes & 0x40000000 or attributes & 0x20000000):
        raise ValueError('Grouped candidate is not a filesystem file')
    info = step('group_file_state', lambda: file_stat(path, follow_symlinks=False))
    regular = stat.S_ISREG(info.st_mode)
    reparse = bool(getattr(info, 'st_file_attributes', 0) & 0x400)
    if not regular or reparse:
        raise ValueError('Grouped file is missing or unsupported')
    ambiguity = step('group_name_collision', lambda: probe_name_ambiguity(path, name))
    # Re-read the exact child and native view after collision checking. No offset
    # arithmetic or selected/focused file is consulted, even for the first group.
    again = step('group_parse_recheck', lambda: document.ParseName(name))
    current = step('group_view_recheck', lambda: browser.QueryActiveShellView())
    anchor_again = step('group_anchor_recheck', lambda: folder.GetItem(0, c.byref(item_type._iid_)))
    stable = (
        step('group_count_recheck', lambda: folder.ItemCount(2)) == count
        and step('group_shell_count', lambda: document.Items().Count) == count
        and step('group_hwnd_recheck', lambda: current.GetWindow()) == view_hwnd
        and step('group_parent_recheck', lambda: str(document.Self.Path)) == parent
        and step('group_child_recheck', lambda: str(again.Path)) == path
        and bool(again.IsFileSystem) and not bool(again.IsFolder)
        and step('group_anchor_path_recheck', lambda: probe._path(anchor_again)) == anchor_path
        and grouping_key(probe, folder, ancestry) == key
    )
    return {
        'lookup_mode': 'grouped_name', 'item_count': count, 'truncated': False,
        'candidates': [automation], 'shell_snapshot_stable': bool(stable),
        'active_view_association': association, 'name_ambiguity': ambiguity,
        'grouped_context': {'method': 'active_folder_exact_name', 'grouping_key': key,
                            'folder_path': parent, 'native_anchor_path': anchor_path,
                            'native_anchor_is_filesystem': True, 'native_parent_path': native_parent},
        'native_view_candidate': {
            'index': None, 'candidate_path': native_path, 'is_filesystem': True,
            'is_folder': False, 'view_item_count': count, 'snapshot_stable': bool(stable),
            'exists_regular_file': regular, 'is_reparse_point': reparse, 'local_fixed_drive': True,
        },
    }
