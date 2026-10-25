"""Grouped-view replay/fakes: no claim of Windows COM or Explorer acceptance."""
import copy
import unittest
from pathlib import PureWindowsPath
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from test_large_folder_lookup import record_for
from test_shell_view_probe import probe_and_window

from filewheel.core.experimental import candidate_from_record
from filewheel.core.index_mapping import assess_index_mapping
from filewheel.platforms.windows import grouped_view
from filewheel.platforms.windows.shell_evidence import ShellEvidenceCollector


def grouped_record(name='yesterday.png', automation_id='0', count=1001):
    record = record_for(count, 0)
    entry = record['shell_candidates']['matching_windows'][0]
    parent = r'C:\fixture\project\tests'
    path = parent + '\\' + name
    item = record['uia_ancestry'][0]
    item.update(name=name, automation_id=automation_id)
    group = copy.deepcopy(item)
    group.update(name='Yesterday', class_name='UIGroup', control_type=50026, automation_id='1')
    record['uia_ancestry'].insert(1, group)
    entry.update(lookup_mode='grouped_name', candidates=[{
        'lookup_name': name, 'candidate_path': path, 'is_folder': False, 'is_filesystem': True,
    }], grouped_context={
        'method': 'active_folder_exact_name', 'grouping_key': 'uia_group',
        'folder_path': parent, 'native_anchor_path': parent + r'\today.png',
        'native_anchor_is_filesystem': True, 'native_parent_path': parent,
    })
    entry['native_view_candidate'].update(index=None, candidate_path=path)
    entry['name_ambiguity'].update(name=name, candidate_path=path)
    return record


class GroupedMappingTests(unittest.TestCase):
    def assess(self, record):
        return assess_index_mapping(record, now=record['timestamp_monotonic'] + .1)

    def test_all_sections_use_exact_child_names_not_local_or_compound_indices(self):
        for name in ('today.png', 'yesterday.png', 'earlier this week.png', 'Æ older.png'):
            for identifier in ('0', '1', '1.0', 'group-item-2', ''):
                with self.subTest(name=name, identifier=identifier):
                    record = grouped_record(name, identifier)
                    result = self.assess(record)
                    self.assertEqual(result['status'], 'provisional', result)
                    self.assertIsNone(result['candidate_index'])
                    self.assertFalse(result['checks']['index_in_range'])
                    self.assertIsNone(result['checks']['native_index_path_match'])
                    self.assertTrue(result['checks']['native_item_path_match'])
                    candidate = candidate_from_record(record, now=record['timestamp_monotonic'] + .1)
                    self.assertEqual(candidate.path.name, name)

    def test_missing_or_conflicting_group_context_and_native_evidence_reject(self):
        mutations = [
            lambda e: e.pop('grouped_context'),
            lambda e: (e.update(item_count=0), e['native_view_candidate'].update(view_item_count=0)),
            lambda e: e['grouped_context'].update(native_parent_path='C:/other'),
            lambda e: e['grouped_context'].update(native_anchor_path='C:/wrong/today.png'),
            lambda e: e['grouped_context'].update(grouping_key=''),
            lambda e: e['grouped_context'].update(native_anchor_is_filesystem=False),
            lambda e: e['native_view_candidate'].update(index=0),
            lambda e: e['native_view_candidate'].update(candidate_path='C:/wrong.png'),
            lambda e: e['native_view_candidate'].update(snapshot_stable=False),
            lambda e: e['native_view_candidate'].update(view_item_count=2),
            lambda e: e['candidates'][0].update(lookup_name='today.png'),
            lambda e: e['name_ambiguity'].update(status='ambiguous'),
            lambda e: e.update(shell_snapshot_stable=False),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                record = grouped_record()
                mutate(record['shell_candidates']['matching_windows'][0])
                self.assertEqual(self.assess(record)['status'], 'rejected')
                self.assertIsNone(candidate_from_record(record, now=record['timestamp_monotonic'] + .1))

    def test_group_headers_hidden_labels_and_outside_group_geometry_reject(self):
        record = grouped_record()
        record['uia_ancestry'][0]['name'] = 'yesterday'
        self.assertEqual(self.assess(record)['status'], 'rejected')
        record = grouped_record()
        record['uia_ancestry'][0]['class_name'] = 'UIGroup'
        self.assertEqual(self.assess(record)['rejection'], 'non_file_element')
        record = grouped_record()
        record['uia_ancestry'][1]['bounds'] = [0, 0, 1, 1]
        self.assertEqual(self.assess(record)['status'], 'rejected')

    def test_unique_active_tab_still_required_for_mixed_grouped_and_flat_tabs(self):
        record = grouped_record()
        peer = copy.deepcopy(record['shell_candidates']['matching_windows'][0])
        peer.update(lookup_mode='targeted_index', candidates=[], item_count=None)
        peer.pop('native_view_candidate')
        peer['active_view_association'].update(status='unproven', browser_hwnd=222, view_hwnd=333)
        record['shell_candidates']['matching_windows'].append(peer)
        self.assertEqual(self.assess(record)['status'], 'provisional')
        peer['active_view_association']['status'] = 'matched'
        self.assertEqual(self.assess(record)['status'], 'rejected')


def grouped_probe():
    probe, window, ancestry, _freed = probe_and_window()
    browser = window.QueryInterface(None).QueryService(None, None).QueryInterface(None)
    view = browser.QueryActiveShellView()
    folder = view.QueryInterface(None)
    browser.QueryActiveShellView = lambda: view
    group = {'class_name': 'UIGroup', 'control_type': 50026}
    ancestry[:0] = [{'class_name': 'UIItem', 'control_type': 50007,
                     'name': 'yesterday.png', 'automation_id': '1.0'}, group]
    parent = r'C:\fixture\downloads'
    native_parent = NS(path=parent)
    native_item = NS(path=parent + r'\yesterday.png', GetAttributes=lambda flags: 0x40000000,
                     GetParent=lambda: NS(QueryInterface=lambda kind: native_parent))
    anchor = NS(path=parent + r'\today.png', GetAttributes=lambda flags: 0x40000000)
    folder.GetItem = Mock(return_value=anchor)
    folder.ItemCount = Mock(return_value=1001)
    parsed = NS(Path=native_item.path, IsFolder=False, IsFileSystem=True)
    document = NS(Self=NS(Path=parent), ParseName=Mock(return_value=parsed),
                  Items=Mock(return_value=NS(Count=1001)))
    window.Document = NS(Folder=document)
    probe._path = lambda item: item.path
    return probe, window, ancestry, folder, native_item, document


class NativeGroupedProbeTests(unittest.TestCase):
    def capture(self, *, change=None):
        probe, window, ancestry, folder, item, document = grouped_probe()
        if change:
            change(probe, window, ancestry, folder, item, document)
        with patch.object(grouped_view, 'native_item_from_path', return_value=item), \
             patch.object(grouped_view, 'probe_name_ambiguity', return_value={'status': 'unique'}), \
             patch.object(grouped_view, 'file_stat', return_value=NS(st_mode=0o100644, st_file_attributes=0)):
            return probe.capture(window, ancestry, None), folder, document

    def test_second_group_does_not_use_local_index_and_work_is_bounded(self):
        result, folder, document = self.capture()
        self.assertIn('lookup_mode', result, result)
        self.assertEqual(result['lookup_mode'], 'grouped_name')
        self.assertTrue(result['native_view_candidate']['snapshot_stable'])
        self.assertEqual(PureWindowsPath(result['native_view_candidate']['candidate_path']).name,
                         'yesterday.png')
        self.assertEqual([call.args[0] for call in folder.GetItem.call_args_list], [0, 0])
        self.assertEqual(document.ParseName.call_count, 2)
        document.Items.assert_called_once()
        self.assertNotIn('enumeration_index', result['candidates'][0])

    def test_group_parent_path_and_snapshot_contradictions_reject(self):
        for change in (
            lambda p,w,a,f,i,d: setattr(d.Self, 'Path', r'C:\other'),
            lambda p,w,a,f,i,d: setattr(i, 'path', r'C:\other\yesterday.png'),
            lambda p,w,a,f,i,d: setattr(d.ParseName.return_value, 'Path', r'C:\fixture\downloads\yesterday.txt'),
        ):
            with self.subTest(change=change):
                result, _, _ = self.capture(change=change)
                self.assertNotIn('native_view_candidate', result)
        result, _, _ = self.capture(change=lambda p,w,a,f,i,d: setattr(f.ItemCount, 'side_effect', [1001, 1002]))
        self.assertFalse(result['native_view_candidate']['snapshot_stable'])

    def test_collector_never_treats_group_parse_as_flat_enumeration(self):
        evidence, _, document = self.capture()
        self.assertIn('lookup_mode', evidence, evidence)
        window = NS(HWND=10, Document=NS(Folder=document))
        collector = object.__new__(ShellEvidenceCollector)
        collector._shell = NS(Windows=lambda: NS(Count=1, Item=lambda i: window))
        collector._view_probe = NS(capture=lambda *a: evidence)
        before = document.Items.call_count
        result = collector.collect(10, [{'class_name': 'UIItem', 'control_type': 50007,
                                        'automation_id': '1.0', 'name': 'yesterday.png'}])
        self.assertEqual(result['matching_windows'][0]['lookup_mode'], 'grouped_name')
        self.assertEqual(document.Items.call_count, before)


class GroupingPropertyTests(unittest.TestCase):
    def test_native_property_detects_grouping_without_uia_group_container(self):
        import ctypes as c
        class Guid(c.Structure):
            _fields_ = [('value', c.c_uint32 * 4)]
            def __str__(self):
                return ('{11111111-2222-3333-4444-555555555555}' if self.value[0]
                        else '{00000000-0000-0000-0000-000000000000}')
        def get_group(pointer):
            pointer._obj.fmtid.value[0] = 1
            pointer._obj.pid = 14
            return False  # Descending groups are still groups.
        probe = NS(_types=(c, None, Guid))
        folder = NS(GetGroupBy=get_group)
        self.assertEqual(grouped_view.grouping_key(probe, folder, []),
                         '{11111111-2222-3333-4444-555555555555}:14')
        folder.GetGroupBy = lambda pointer: None
        self.assertIsNone(grouped_view.grouping_key(probe, folder, []))

    def test_native_group_property_evidence_does_not_need_uia_group_ancestor(self):
        record = grouped_record()
        record['uia_ancestry'].pop(1)
        record['shell_candidates']['matching_windows'][0]['grouped_context']['grouping_key'] = (
            '{11111111-2222-3333-4444-555555555555}:14')
        self.assertEqual(assess_index_mapping(record, now=record['timestamp_monotonic'] + .1)['status'],
                         'provisional')
