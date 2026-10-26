"""Actual spawned deadline enforcement, with publication kept non-killable."""
import time
from threading import Event, Timer
from typing import ClassVar
from unittest.mock import patch

import pytest

from filewheel.converters import (
    Capability,
    ConversionCancelled,
    ConversionError,
    ConversionManager,
    EngineOutput,
    Registry,
)
from filewheel.converters.process_worker import run_in_process


class UncooperativeArchive:
    engine_id = 'deadline-fixture'
    capabilities = (Capability('.zip', 'Markdown/Text', '.md', 'Markdown', engine_id),)
    execution_timeouts: ClassVar[dict[str, float]] = {'.zip': 1.2}

    def available(self):
        return True

    def convert(self, source, extension, workdir, progress, cancel):
        output = workdir/'output.md'
        output.write_text('Must never publish')
        progress(.1, 'Uncooperative encoder entered')
        time.sleep(5)
        return (EngineOutput(output, source.with_suffix('.md').name),)

    def validate(self, output):
        assert output.path.read_text()


class FastArchive(UncooperativeArchive):
    execution_timeouts: ClassVar[dict[str, float]] = {'.zip': 1.}

    def convert(self, source, extension, workdir, progress, cancel):
        output = workdir/'output.md'
        output.write_text('Useful published result')
        return (EngineOutput(output, source.with_suffix('.md').name),)


class SlowPublisher(ConversionManager):
    @staticmethod
    def _publish(output, directory):
        time.sleep(1.3)  # Already has permit; exceeds encoder budget safely.
        return ConversionManager._publish(output, directory)


def test_uncooperative_encoder_is_stopped_before_publication_and_cleaned(tmp_path):
    source = tmp_path/'Résumé archive.zip'
    source.write_bytes(b'original source')
    cancellation = Event()
    messages = []
    started = time.monotonic()
    with pytest.raises(ConversionError, match='timed out') as failure:
        run_in_process(ConversionManager(Registry((UncooperativeArchive(),))), source, '.md',
                       progress=lambda _, message: messages.append(message), cancel=cancellation)
    assert time.monotonic() - started < 4
    assert failure.value.operation == 'timeout'
    assert failure.value.engine_id == 'deadline-fixture'
    assert not cancellation.is_set()
    assert messages  # Fixture reached the encoder rather than just startup.
    assert source.read_bytes() == b'original source'
    assert not source.with_suffix('.md').exists()
    assert not list(tmp_path.glob('.filewheel-*'))


def test_deadline_never_kills_a_worker_after_publication_permission(tmp_path):
    source = tmp_path/'publish.zip'
    source.write_bytes(b'original source')
    result = run_in_process(SlowPublisher(Registry((FastArchive(),))), source, '.md',
                            progress=lambda *args: None, cancel=Event())
    assert result.path.read_text() == 'Useful published result'
    assert source.read_bytes() == b'original source'
    assert not list(tmp_path.glob('.filewheel-*'))


def test_user_cancellation_keeps_cancelled_outcome_with_execution_budget(tmp_path):
    source = tmp_path/'cancel.zip'
    source.write_bytes(b'original source')
    cancellation = Event()
    timer = Timer(.2, cancellation.set)
    timer.start()
    try:
        with pytest.raises(ConversionCancelled) as failure:
            run_in_process(ConversionManager(Registry((UncooperativeArchive(),))), source, '.md',
                           progress=lambda *args: None, cancel=cancellation, _cancel_grace=.05)
        assert failure.value.kind == 'conversion_cancelled'
        assert not source.with_suffix('.md').exists()
        assert not list(tmp_path.glob('.filewheel-*'))
    finally:
        timer.cancel()
        timer.join()


def test_deadline_rechecked_after_packet_decode_before_publication(tmp_path):
    from filewheel.converters import process_worker
    source = tmp_path/'late-permit.zip'
    source.write_bytes(b'original source')
    original = process_worker.decode_packet
    def delayed_decode(payload):
        packet = original(payload)
        if packet['type'] == 'publish_ready':
            time.sleep(1.1)  # Budget expires after poll, while dispatching report.
        return packet
    with (patch.object(process_worker, 'decode_packet', side_effect=delayed_decode),
          pytest.raises(ConversionError, match='timed out')):
        run_in_process(ConversionManager(Registry((FastArchive(),))), source, '.md',
                       progress=lambda *args: None, cancel=Event())
    assert not source.with_suffix('.md').exists()
    assert not list(tmp_path.glob('.filewheel-*'))
