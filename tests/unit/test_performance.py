"""Portable tests for bounded opt-in timing data; Qt is deliberately absent."""

import json
from unittest.mock import patch

from filewheel.performance import TimingRecorder, summarize


def test_disabled_does_not_touch_disk(tmp_path):
    recorder = TimingRecorder()
    with patch('pathlib.Path.write_text', side_effect=AssertionError('disk access')):
        recorder.record('paint_cpu', 1)
        assert recorder.snapshot() == []
        assert recorder.flush() is False
    assert list(tmp_path.iterdir()) == []


def test_bounded_allowlisted_records_are_copies(tmp_path):
    recorder = TimingRecorder(tmp_path / 'timing.json', capacity=2)
    recorder.record('private filename.png', 5)
    recorder.record('paint_cpu', float('nan'))
    recorder.record('paint_cpu', -1)
    recorder.record('paint_cpu', 'private window title')
    for value in (1, 2, 3):
        recorder.record('paint_cpu', value)
    rows = recorder.snapshot()
    assert rows == [{'stage': 'paint_cpu', 'duration_ms': 2},
                    {'stage': 'paint_cpu', 'duration_ms': 3}]
    rows[0]['duration_ms'] = 50
    assert recorder.snapshot()[0]['duration_ms'] == 2
    assert list(tmp_path.iterdir()) == []
    assert recorder.flush()
    payload = json.loads((tmp_path / 'timing.json').read_text())
    assert set(payload['records'][0]) == {'stage', 'duration_ms'}
    assert 'private' not in json.dumps(payload)


def test_percentiles_use_nearest_rank():
    records = [{'stage': 'paint_cpu', 'duration_ms': value} for value in range(1, 101)]
    assert summarize(records) == {'paint_cpu': {'count': 100, 'p50_ms': 50,
                                               'p95_ms': 95, 'max_ms': 100}}
    assert summarize([]) == {}


def test_malformed_or_unwritable_output_is_nonfatal(tmp_path):
    for value in ('relative.json', tmp_path / 'timing.txt', object()):
        recorder = TimingRecorder(value)
        assert not recorder.enabled
        assert not recorder.flush()
    recorder = TimingRecorder(tmp_path / 'absent' / 'timing.json')
    recorder.record('resolver', 2)
    assert not recorder.flush()
    recorder = TimingRecorder(str(tmp_path / 'bad\0.json'))
    assert not recorder.flush()


def test_flush_never_replaces_existing_file_or_link_and_is_once(tmp_path):
    path = tmp_path / 'existing.json'
    path.write_text('user content')
    recorder = TimingRecorder(path)
    recorder.record('resolver', 2)
    assert not recorder.flush()
    assert path.read_text() == 'user content'
    destination = tmp_path / 'new.json'
    recorder = TimingRecorder(destination)
    recorder.record('resolver', 3)
    assert recorder.flush()
    before = destination.read_bytes()
    recorder.record('resolver', 4)
    assert not recorder.flush()
    assert destination.read_bytes() == before
