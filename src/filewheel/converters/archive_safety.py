"""Bounded, in-memory ZIP reads; no archive member is extracted to disk."""
import io
import math
import stat
import struct
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from time import monotonic
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile

from filewheel.converters.base import ConversionError, check_cancel


@dataclass(frozen=True)
class ArchiveLimits:
    archive_bytes: int = 16 * 1024 * 1024
    expanded_bytes: int = 32 * 1024 * 1024
    member_bytes: int = 8 * 1024 * 1024
    members: int = 128
    ratio: int = 100
    seconds: float = 10.
    directory_bytes: int = 256 * 1024

    def __post_init__(self):
        values = (self.archive_bytes, self.expanded_bytes, self.member_bytes, self.members, self.ratio, self.directory_bytes)
        if any(type(value) is not int or value < 1 for value in values) or not isinstance(self.seconds, (int, float)) or not math.isfinite(self.seconds) or not 0 < self.seconds <= 60:
            raise ValueError('Archive limits must be positive and bounded')


def safe_member_name(name):
    if (not name or '\\' in name or ':' in name or any(ord(c) < 32 for c in name)
            or name.startswith('/') or any(p in ('', '.', '..') for p in name.rstrip('/').split('/'))
            or any(p.endswith((' ', '.')) for p in name.rstrip('/').split('/'))):
        raise ConversionError('Unsafe archive member path')
    path = PurePosixPath(name)
    if path.is_absolute():
        raise ConversionError('Unsafe archive member path')
    return name.rstrip('/')


DEFAULT_LIMITS = ArchiveLimits()


def _preflight_directory(source, limits, check):
    # ZipFile eagerly allocates ZipInfo for every central-directory entry.
    # Bound that directory and its actual records before constructing ZipFile.
    size = len(source)
    tail = source[-65557:]
    at = tail.rfind(b'PK\x05\x06')
    if at < 0 or len(tail) - at < 22:
        raise ConversionError('Archive has no valid end directory')
    _, disk, directory_disk, on_disk, entries, directory_size, directory_offset, comment = struct.unpack_from('<4s4H2IH', tail, at)
    absolute_end = size - len(tail) + at
    if (at + 22 + comment != len(tail) or disk or directory_disk or on_disk != entries
            or entries == 65535 or directory_size == 0xffffffff or directory_offset == 0xffffffff):
        raise ConversionError('ZIP64, split or ambiguous archive directories are unsupported')
    if entries > limits.members or directory_size > limits.directory_bytes:
        raise ConversionError('Archive central directory count or size limit exceeded')
    if directory_offset + directory_size != absolute_end:
        raise ConversionError('Archive central directory is inconsistent')
    central = source[directory_offset:directory_offset + directory_size]
    offset = count = 0
    while offset < len(central):
        check()
        if central[offset:offset+4] != b'PK\x01\x02' or offset + 46 > len(central):
            raise ConversionError('Archive central directory is malformed')
        name, extra, annotation = struct.unpack_from('<HHH', central, offset + 28)
        offset += 46 + name + extra + annotation
        count += 1
        if count > limits.members or offset > len(central):
            raise ConversionError('Archive central directory count or size limit exceeded')
    if count != entries:
        raise ConversionError('Archive central directory count is inconsistent')


def read_archive(source: Path, *, limits=DEFAULT_LIMITS, cancel=None, clock=monotonic):
    """Preflight claims and actual streamed bytes/CRC before returning bounded data."""
    if source.stat().st_size > limits.archive_bytes:
        raise ConversionError('Archive exceeds the compressed size limit')
    deadline = clock() + limits.seconds
    def check():
        check_cancel(cancel)
        if clock() > deadline:
            raise ConversionError('Archive processing time limit exceeded')
    check()
    with source.open('rb') as stream:
        snapshot = stream.read(limits.archive_bytes + 1)
    if len(snapshot) > limits.archive_bytes:
        raise ConversionError('Archive exceeds the compressed size limit')
    _preflight_directory(snapshot, limits, check)
    try:
        with ZipFile(io.BytesIO(snapshot)) as archive:
            infos = archive.infolist()
            if len(infos) > limits.members:
                raise ConversionError('Archive member count limit exceeded')
            names, claimed = set(), 0
            for info in infos:
                check()
                name = safe_member_name(info.orig_filename)
                key = name.casefold()
                if key in names:
                    raise ConversionError('Duplicate archive member paths are unsupported')
                names.add(key)
                mode = stat.S_IFMT(info.external_attr >> 16)
                if mode not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise ConversionError('Archive links and special files are unsupported')
                if info.flag_bits & 1:
                    raise ConversionError('Encrypted archive members are unsupported')
                if info.compress_type not in (ZIP_STORED, ZIP_DEFLATED):
                    raise ConversionError('Unsupported archive compression method')
                if info.file_size > limits.member_bytes:
                    raise ConversionError('Archive member size limit exceeded')
                claimed += info.file_size
                if claimed > limits.expanded_bytes:
                    raise ConversionError('Archive expanded size limit exceeded')
                if info.file_size > max(1, info.compress_size) * limits.ratio:
                    raise ConversionError('Archive compression ratio limit exceeded')
            result, actual = {}, 0
            for info in infos:
                check()
                if info.is_dir():
                    continue
                chunks, member_size = [], 0
                with archive.open(info) as stream:
                    while chunk := stream.read(65536):
                        check()
                        member_size += len(chunk)
                        actual += len(chunk)
                        if member_size > limits.member_bytes or actual > limits.expanded_bytes:
                            raise ConversionError('Archive actual expanded size limit exceeded')
                        chunks.append(chunk)
                result[info.filename] = b''.join(chunks)
            return result
    except (BadZipFile, OSError, RuntimeError, NotImplementedError) as error:
        if isinstance(error, ConversionError):
            raise
        raise ConversionError('The archive is corrupt or unsupported') from error
