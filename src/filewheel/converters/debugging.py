"""Private rotating local diagnostics, never telemetry or a conversion dependency."""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock

_lock = Lock()


def debug_log_path():
    override = os.environ.get('FILEWHEEL_LOG_DIR')
    if override:
        root = Path(override)
    else:
        root = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'Filewheel/logs'
    return root / 'conversion-debug.log'


def record_failure(engine, operation, error):
    try:
        path = debug_log_path()
        with _lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(path, maxBytes=2_000_000, backupCount=3, encoding='utf-8')
            try:
                handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
                record = logging.LogRecord('filewheel.conversion', logging.ERROR, __file__, 0,
                                           'engine=%s operation=%s', (engine, operation),
                                           (type(error), error, error.__traceback__))
                handler.emit(record)
                handler.flush()
            finally:
                handler.close()
        return path
    except (OSError, RuntimeError):
        # Failure to create a debug log must not lose the original conversion error.
        return None


def describe_conversion_error(error):
    engine = getattr(error, 'engine_id', None)
    kind = getattr(error, 'kind', 'conversion_failed')
    prefix = f'{engine}: ' if engine else ''
    if kind == 'dependency_unavailable':
        return prefix + 'Required local dependency is unavailable. See debug log.'
    return (prefix + (str(error) or type(error).__name__))[:250]


def error_details(error):
    return (f"Engine: {getattr(error, 'engine_id', 'unselected')}\n"
            f"Operation: {getattr(error, 'operation', 'unknown')}\n"
            f"{error}\nDebug log: {getattr(error, 'debug_log', None) or 'unavailable'}")
