"""Bounded targeted lookups, not Windows COM/runtime acceptance."""
import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from test_shell_view_probe import probe_and_window

from filewheel.core.experimental import candidate_from_record
from filewheel.core.index_mapping import assess_index_mapping
from filewheel.platforms.windows.shell_evidence import ShellEvidenceCollector


def record_for(count=500, index=499):
    fixture = Path(__file__).parents[1] / 'fixtures/windows_sta_1_sanitized.json'
    record = json.loads(fixture.read_text(encoding='utf-8'))['record']
    entry = record['shell_candidates']['matching_windows'][0]
    shell_view = copy.deepcopy(record['uia_ancestry'][1])
    shell_view.update(class_name='DUIListView', control_type=50033,
                      native_hwnd=entry['active_view_association']['view_hwnd'])
    record['uia_ancestry'].insert(2, shell_view)
    candidate = copy.deepcopy(entry['candidates'][3])
    candidate['enumeration_index'] = index
    path = candidate['candidate_path']
    entry.update(lookup_mode='targeted_index', item_count=count, truncated=False,
                 candidates=[candidate], shell_snapshot_stable=True,
                 name_ambiguity={'method': 'literal_name_collision_probe', 'status': 'unique',
                                 'name': Path(path.replace('\\', '/')).name,
                                 'candidate_path': path, 'query_count': 3})
    entry['native_view_candidate'].update(index=index, view_item_count=count)
    next(row for row in record['uia_ancestry'] if row['class_name'] == 'UIItem')['automation_id'] = str(index)
    return record


class LargeFolderMappingTests(unittest.TestCase):
    def assess(self, record):
        return assess_index_mapping(record, now=record['timestamp_monotonic'] + .1)

    def test_sizes_and_high_indices_accept_only_provisional_candidates(self):
        for count in (33, 50, 100, 500, 1001, 10000):
            for index in (0, count - 1):
                with self.subTest(count=count, index=index):
                    record = record_for(count, index)
                    result = self.assess(record)
                    self.assertEqual(result['status'], 'provisional', result)
                    self.assertTrue(result['checks']['candidate_lookup_complete'])
                    self.assertFalse(result['checks']['complete_candidates'])
                    self.assertFalse(result['checks']['identity_correspondence'])
                    self.assertIsNotNone(candidate_from_record(record, now=record['timestamp_monotonic'] + .1))

    def test_invalid_indices_or_conflicting_native_data_reject(self):
        mutations = [
            lambda e: e['native_view_candidate'].update(index=3),
            lambda e: e['native_view_candidate'].update(candidate_path='C:/wrong.txt'),
            lambda e: e['native_view_candidate'].update(view_item_count=499),
            lambda e: e['native_view_candidate'].update(view_item_count=500.0),
            lambda e: e['name_ambiguity'].pop('query_count'),
            lambda e: e['name_ambiguity'].update(query_count=10000),
            lambda e: e['native_view_candidate'].pop('snapshot_stable'),
            lambda e: e['native_view_candidate'].update(snapshot_stable=False),
            lambda e: e['native_view_candidate'].update(exists_regular_file=False),
            lambda e: e.update(shell_snapshot_stable=False),
            lambda e: e.update(candidates=[]),
            lambda e: e['candidates'][0].update(enumeration_index=True),
            lambda e: e.update(item_count=499),
            lambda e: e['active_view_association'].update(browser_hwnd=999),
        ]
        for change in mutations:
            with self.subTest(change=change):
                record = record_for()
                change(record['shell_candidates']['matching_windows'][0])
                self.assertEqual(self.assess(record)['status'], 'rejected')
                self.assertIsNone(candidate_from_record(record, now=record['timestamp_monotonic'] + .1))
        for index in ('-1', '500', '5000', '01', 'x', '999999999999', True):
            with self.subTest(index=index):
                record = record_for()
                next(r for r in record['uia_ancestry'] if r['class_name'] == 'UIItem')['automation_id'] = index
                self.assertEqual(self.assess(record)['status'], 'rejected')

    def test_hidden_or_duplicate_name_and_missing_uniqueness_evidence_reject(self):
        for value in ('ambiguous', 'unproven', None):
            record = record_for()
            entry = record['shell_candidates']['matching_windows'][0]
            if value is None:
                entry.pop('name_ambiguity')
            else:
                entry['name_ambiguity']['status'] = value
            self.assertEqual(self.assess(record)['status'], 'rejected')
        record = record_for()
        row = next(r for r in record['uia_ancestry'] if r['class_name'] == 'UIItem')
        row['name'] = 'b'  # A shortened name cannot borrow forged uniqueness.
        self.assertEqual(self.assess(record)['rejection'], 'ambiguous_display_name')

    def test_excluded_tabs_need_no_directory_listing_and_unknown_tabs_reject(self):
        for count in (3, 33, 1001):
            record = record_for(count, count - 1)
            entry = record['shell_candidates']['matching_windows'][0]
            peer = copy.deepcopy(entry)
            peer.update(item_count=None, candidates=[])
            peer.pop('native_view_candidate')
            peer['active_view_association'].update(status='unproven', browser_hwnd=111, view_hwnd=222)
            record['shell_candidates']['matching_windows'].append(peer)
            self.assertEqual(self.assess(record)['status'], 'provisional')
            peer['active_view_association']['browser_hwnd'] = entry['active_view_association']['browser_hwnd']
            self.assertEqual(self.assess(record)['status'], 'rejected')


class BoundedCollectorTests(unittest.TestCase):
    def test_large_active_view_reads_one_dispatch_item_no_inactive_listing(self):
        for count in (33, 50, 100, 500, 1001, 10000):
            with self.subTest(count=count):
                record = record_for(count, count - 1)
                evidence = record['shell_candidates']['matching_windows'][0]
                path = evidence['candidates'][0]['candidate_path']
                items = NS(Count=count, Item=Mock(return_value=NS(
                    Path=path, IsFolder=False, IsFileSystem=True)))
                active = NS(HWND=10, Document=NS(Folder=NS(Items=lambda items=items: items)))
                class Inactive:
                    HWND = 10
                    @property
                    def Document(self):
                        raise AssertionError('Inactive tab must not enumerate')
                inactive = Inactive()
                windows = NS(Count=2, Item=lambda i, inactive=inactive, active=active: [inactive, active][i])
                collector = object.__new__(ShellEvidenceCollector)
                collector._shell = NS(Windows=lambda windows=windows: windows)
                collector._view_probe = NS(capture=lambda window, ancestry, index, inactive=inactive, evidence=evidence: (
                    {'active_view_association': {'status': 'unproven'}} if window is inactive
                    else {k: copy.deepcopy(evidence[k]) for k in
                          ('active_view_association', 'native_view_candidate', 'name_ambiguity')}))
                result = collector.collect(10, record['uia_ancestry'])
                items.Item.assert_called_once_with(count - 1)
                self.assertEqual(len(result['matching_windows'][1]['candidates']), 1)

    def test_small_view_retains_bounded_complete_enumeration(self):
        items = NS(Count=3, Item=Mock(return_value=NS(Path='C:/a.txt', IsFolder=False, IsFileSystem=True)))
        window = NS(HWND=10, Document=NS(Folder=NS(Items=lambda items=items: items)))
        collector = object.__new__(ShellEvidenceCollector)
        collector._shell = NS(Windows=lambda: NS(Count=1, Item=lambda i: window))
        collector._view_probe = NS(capture=lambda *a: {
            'active_view_association': {'status': 'matched'}, 'native_view_candidate': {}})
        result = collector.collect(10, [{'class_name': 'UIItem', 'control_type': 50007, 'automation_id': '2'}])
        self.assertEqual(items.Item.call_count, 3)
        self.assertNotIn('lookup_mode', result['matching_windows'][0])

    def test_native_getitem_calls_are_constant_and_high_indices_reach_probe(self):
        for count in (33, 50, 100, 500, 1001, 10000):
            with self.subTest(count=count):
                probe, window, ancestry, _ = probe_and_window()
                folder = window.QueryInterface(None).QueryService(None, None).QueryInterface(None).QueryActiveShellView().QueryInterface(None)
                # Restore the consumed first view for the fixture's browser.
                view = NS(GetWindow=lambda: 30, QueryInterface=lambda kind, folder=folder: folder)
                browser = NS(QueryActiveShellView=lambda view=view: view, GetWindow=lambda: 20)
                window.QueryInterface = lambda kind, browser=browser: NS(QueryService=lambda *a: NS(QueryInterface=lambda kind: browser))
                folder.ItemCount = lambda flags, count=count: count
                original = folder.GetItem
                folder.GetItem = Mock(side_effect=original)
                ancestry.insert(0, {'class_name': 'UIItem', 'control_type': 50007, 'name': 'a.txt'})
                with patch('filewheel.platforms.windows.shell_view.os.stat', return_value=NS(st_mode=0o100644, st_file_attributes=0)), patch('filewheel.platforms.windows.name_ambiguity.probe_name_ambiguity', return_value={'status': 'unique'}) as names:
                    result = probe.capture(window, ancestry, count - 1)
                self.assertTrue(result['native_view_candidate']['snapshot_stable'])
                self.assertEqual(folder.GetItem.call_count, 2)
                self.assertEqual([call.args[0] for call in folder.GetItem.call_args_list], [count - 1] * 2)
                names.assert_called_once()

    def test_invalid_native_indices_never_read_an_item(self):
        for index in (-1, 3, 500, True, 2.5):
            with self.subTest(index=index):
                probe, window, ancestry, _ = probe_and_window()
                probe._path = lambda item: self.fail('Out-of-range native GetItem used')
                result = probe.capture(window, ancestry, index)
                self.assertEqual(result['native_error'], 'view_index_or_size')
                self.assertNotIn('native_view_candidate', result)

    def test_native_snapshot_recheck_detects_change_during_collision_query(self):
        probe, window, ancestry, _ = probe_and_window()
        browser = window.QueryInterface(None).QueryService(None, None).QueryInterface(None)
        view = browser.QueryActiveShellView()
        folder = view.QueryInterface(None)
        browser.QueryActiveShellView = lambda: view
        folder.ItemCount = Mock(side_effect=[500, 501])
        ancestry.insert(0, {'class_name': 'UIItem', 'control_type': 50007, 'name': 'a.txt'})
        stages = []
        def collision(*args):
            stages.append('collision')
            return {'status': 'unique'}
        def count(flags):
            stages.append('count')
            return 500 if len(stages) == 1 else 501
        folder.ItemCount = count
        with patch('filewheel.platforms.windows.shell_view.os.stat', return_value=NS(st_mode=0o100644, st_file_attributes=0)), patch('filewheel.platforms.windows.name_ambiguity.probe_name_ambiguity', side_effect=collision):
            result = probe.capture(window, ancestry, 499)
        self.assertEqual(stages, ['count', 'collision', 'count'])
        self.assertFalse(result['native_view_candidate']['snapshot_stable'])
