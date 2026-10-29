"""Generated FFmpeg fixtures cover the advertised media routes and safety rules."""

import shutil
import subprocess
from pathlib import Path
from threading import Event

import pytest

from filewheel.converters import ConversionCancelled, ConversionError, ConversionManager, Registry
from filewheel.converters.video import VideoEngine

FFMPEG = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(not FFMPEG, reason="FFmpeg unavailable")


def manager():
    engine = VideoEngine(FFMPEG)
    assert engine.available()
    return ConversionManager(Registry((engine,)))


def run(args):
    result = subprocess.run(args, check=False, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr.decode(errors="replace")


def make_video(
    path,
    *,
    codec="libx264",
    audio=True,
    second_audio=False,
    second_audio_codec=None,
    duration=0.5,
):
    if path.suffix.lower() == ".webm" and codec == "libx264":
        codec = "libvpx-vp9"
    args = [FFMPEG, "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=160x120:rate=12"]
    if audio:
        args += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000"]
    if second_audio:
        args += ["-f", "lavfi", "-i", "sine=frequency=880:sample_rate=48000"]
    args += ["-t", str(duration)]
    if not audio:
        args += ["-an"]
    else:
        args += ["-map", "0:v:0"]
    if audio:
        args += ["-map", "1:a:0"]
        if second_audio:
            args += ["-map", "2:a:0"]
    args += ["-c:v", codec]
    if codec == "libx264":
        args += ["-pix_fmt", "yuv420p"]
    if audio:
        first_audio_codec = "libopus" if path.suffix.lower() == ".webm" else "aac"
        if second_audio_codec:
            args += ["-c:a:0", first_audio_codec, "-c:a:1", second_audio_codec]
        else:
            args += ["-c:a", first_audio_codec]
    args += ["-y", str(path)]
    run(args)


def make_audio(path, codec, muxer=None):
    args = [
        FFMPEG,
        "-v",
        "error",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=44100",
        "-t",
        "0.5",
        "-c:a",
        codec,
    ]
    if codec == "libmp3lame":
        args += ["-q:a", "3"]
    if muxer:
        args += ["-f", muxer]
    args += ["-y", str(path)]
    run(args)


@pytest.mark.parametrize(
    ("source_ext", "target_ext"),
    [
        (".mp4", ".mov"),
        (".mp4", ".mkv"),
        (".mov", ".mp4"),
        (".mov", ".mkv"),
        (".mkv", ".mp4"),
        (".mkv", ".mov"),
        (".mp4", ".webm"),
        (".webm", ".mp4"),
        (".avi", ".mp4"),
        (".m4v", ".mkv"),
    ],
)
def test_video_routes_preserve_source_and_emit_valid_output(tmp_path, source_ext, target_ext):
    source = tmp_path / ("sample" + source_ext)
    make_video(source)
    original = source.read_bytes()
    result = manager().convert(source, target_ext)
    assert result.path.suffix == target_ext
    assert result.path.stat().st_size > 1024
    assert source.read_bytes() == original


@pytest.mark.parametrize(
    ("target_ext", "expected_video", "expected_audio"),
    [(".mp4", "h264", "aac"), (".mkv", "h264", "aac"), (".webm", "vp9", "opus")],
)
def test_video_targets_preserve_usable_track_and_omit_undecodable_apac(
    tmp_path, monkeypatch, target_ext, expected_video, expected_audio
):
    source = tmp_path / "iphone.mov"
    make_video(source, second_audio=True)
    original = source.read_bytes()
    engine = VideoEngine(FFMPEG)
    inspect = engine._inspect

    def report_apac(path, workdir, cancel, *, require_video):
        duration, diagnostic, streams = inspect(path, workdir, cancel, require_video=require_video)
        if Path(path).resolve() == source.resolve():
            streams = [
                stream._replace(codec="apple_apac") if stream.index == 2 else stream
                for stream in streams
            ]
        return duration, diagnostic, streams

    monkeypatch.setattr(engine, "_inspect", report_apac)
    result = ConversionManager(Registry((engine,))).convert(source, target_ext)
    output_streams = inspect(result.path, tmp_path, None, require_video=True)[2]
    assert [stream.codec for stream in output_streams if stream.kind == "Video"] == [expected_video]
    assert [stream.codec for stream in output_streams if stream.kind == "Audio"] == [expected_audio]
    assert any("track 2 (apple_apac) was omitted" in warning for warning in result.warnings)
    assert source.read_bytes() == original


@pytest.mark.parametrize(
    ("target_ext", "expected_video", "expected_audio"),
    [(".mp4", "h264", "aac"), (".mkv", "h264", "aac"), (".webm", "vp9", "opus")],
)
def test_video_formats_reencode_incompatible_decodable_audio_only(
    tmp_path, target_ext, expected_video, expected_audio
):
    source = tmp_path / "iphone-with-adpcm.mov"
    make_video(source, second_audio=True, second_audio_codec="adpcm_ima_qt")
    original = source.read_bytes()
    engine = VideoEngine(FFMPEG)
    result = ConversionManager(Registry((engine,))).convert(source, target_ext)
    output_streams = engine._inspect(result.path, tmp_path, None, require_video=True)[2]
    output_video = next(stream.codec for stream in output_streams if stream.kind == "Video")
    assert output_video == expected_video
    assert [stream.codec for stream in output_streams if stream.kind == "Audio"] == [
        expected_audio,
        expected_audio,
    ]
    assert any(
        f"adpcm_ima_qt) was re-encoded as {expected_audio.upper()}" in warning
        for warning in result.warnings
    )
    assert source.read_bytes() == original


@pytest.mark.parametrize("target_ext", [".mp4", ".mkv", ".webm"])
def test_video_targets_keep_multiple_compatible_audio_tracks(tmp_path, target_ext):
    source = tmp_path / "multi-audio.mov"
    make_video(source, second_audio=True)
    engine = VideoEngine(FFMPEG)
    result = ConversionManager(Registry((engine,))).convert(source, target_ext)
    output_streams = engine._inspect(result.path, tmp_path, None, require_video=True)[2]
    expected_audio = "opus" if target_ext == ".webm" else "aac"
    assert [stream.codec for stream in output_streams if stream.kind == "Audio"] == [
        expected_audio,
        expected_audio,
    ]
    assert not any("omitted" in warning.lower() for warning in result.warnings)
    if target_ext == ".webm":
        assert sum("re-encoded as OPUS" in warning for warning in result.warnings) == 2


@pytest.mark.parametrize("target_ext", [".mp4", ".mkv", ".webm", ".mp3", ".m4a", ".wav"])
def test_apac_only_fails_clearly_without_publishing(tmp_path, monkeypatch, target_ext):
    source = tmp_path / "apac-only.mov"
    make_video(source)
    original = source.read_bytes()
    engine = VideoEngine(FFMPEG)
    inspect = engine._inspect

    def report_apac(path, workdir, cancel, *, require_video):
        duration, diagnostic, streams = inspect(path, workdir, cancel, require_video=require_video)
        if Path(path).resolve() == source.resolve():
            streams = [
                stream._replace(codec="apple_apac") if stream.kind == "Audio" else stream
                for stream in streams
            ]
        return duration, diagnostic, streams

    monkeypatch.setattr(engine, "_inspect", report_apac)
    with pytest.raises(ConversionError, match="apple_apac.*cannot decode"):
        ConversionManager(Registry((engine,))).convert(source, target_ext)
    assert not source.with_suffix(target_ext).exists()
    assert source.read_bytes() == original


@pytest.mark.parametrize(
    ("target_ext", "expected_codec"),
    [(".mp3", "mp3"), (".m4a", "aac"), (".wav", "pcm_s16le"), (".flac", "flac")],
)
def test_audio_extraction_skips_apac_and_uses_decodable_alternate(
    tmp_path, monkeypatch, target_ext, expected_codec
):
    source = tmp_path / "alternate-audio.mov"
    make_video(source, second_audio=True)
    original = source.read_bytes()
    engine = VideoEngine(FFMPEG)
    inspect = engine._inspect

    def report_apac_first(path, workdir, cancel, *, require_video):
        duration, diagnostic, streams = inspect(path, workdir, cancel, require_video=require_video)
        if Path(path).resolve() == source.resolve():
            streams = [
                stream._replace(codec="apple_apac") if stream.index == 1 else stream
                for stream in streams
            ]
        return duration, diagnostic, streams

    monkeypatch.setattr(engine, "_inspect", report_apac_first)
    result = ConversionManager(Registry((engine,))).convert(source, target_ext)
    output_streams = inspect(result.path, tmp_path, None, require_video=False)[2]
    assert [stream.codec for stream in output_streams if stream.kind == "Audio"] == [expected_codec]
    assert any("track 1 (apple_apac) was omitted" in warning for warning in result.warnings)
    assert source.read_bytes() == original


@pytest.mark.parametrize(
    "diagnostic",
    [
        b"No wav codec tag found for codec apple_apac",
        b"Could not find tag for codec apple_apac",
        b"Codec not currently supported in container",
    ],
)
def test_mkv_codec_header_failures_are_classified_as_incompatible(diagnostic):
    assert VideoEngine._incompatible(diagnostic)


def test_mkv_cancellation_does_not_publish_or_change_source(tmp_path):
    source = tmp_path / "cancel-me.mov"
    make_video(source, second_audio=True, duration=30)
    original = source.read_bytes()
    cancel = Event()
    engine = VideoEngine(FFMPEG)
    run = engine._run

    def realtime_output(args, **kwargs):
        if "output.mkv" in " ".join(str(argument) for argument in args):
            args = ["-re", *args]
        return run(args, **kwargs)

    engine._run = realtime_output

    def progress(_fraction, message):
        if "Converting media" in message:
            cancel.set()

    with pytest.raises(ConversionCancelled):
        ConversionManager(Registry((engine,))).convert(
            source, ".mkv", cancel=cancel, progress=progress
        )
    assert not source.with_suffix(".mkv").exists()
    assert source.read_bytes() == original


@pytest.mark.parametrize(
    ("source_ext", "codec", "muxer"),
    [
        (".mp3", "libmp3lame", None),
        (".m4a", "aac", "ipod"),
        (".wav", "pcm_s16le", "wav"),
        (".flac", "flac", None),
        (".ogg", "libvorbis", "ogg"),
        (".opus", "libopus", "opus"),
    ],
)
@pytest.mark.parametrize("target_ext", [".mp3", ".m4a", ".wav", ".flac"])
def test_audio_routes_convert_between_popular_formats(
    tmp_path, source_ext, codec, muxer, target_ext
):
    if source_ext == target_ext:
        pytest.skip("same-format conversions are not advertised")
    source = tmp_path / ("sample" + source_ext)
    make_audio(source, codec, muxer)
    original = source.read_bytes()
    result = manager().convert(source, target_ext)
    assert result.path.suffix == target_ext
    assert result.path.stat().st_size > 1024
    assert source.read_bytes() == original
    if target_ext == ".flac" and source_ext in (".mp3", ".m4a", ".ogg", ".opus"):
        assert any("cannot restore quality lost earlier" in warning for warning in result.warnings)


@pytest.mark.parametrize("target_ext", [".mp3", ".m4a", ".wav"])
def test_video_audio_extraction_warns_when_additional_tracks_are_dropped(tmp_path, target_ext):
    source = tmp_path / "multi-audio.mp4"
    make_video(source, second_audio=True)
    result = manager().convert(source, target_ext)
    assert result.path.stat().st_size > 1024
    assert any("audio track 2" in warning.lower() for warning in result.warnings)


def test_prores_mov_uses_explicit_h264_aac_profile(tmp_path):
    source = tmp_path / "edit.mov"
    make_video(source, codec="prores_ks", audio=False)
    result = manager().convert(source, ".mp4")
    assert any("re-encoded as H.264" in warning for warning in result.warnings)


def test_invalid_video_rejected_without_publishing(tmp_path):
    source = tmp_path / "broken.mp4"
    source.write_bytes(b"not media")
    with pytest.raises(ConversionError):
        manager().convert(source, ".mov")
    assert not source.with_suffix(".mov").exists()


def test_cancellation_before_probe_publishes_nothing(tmp_path):
    source = tmp_path / "sample.mp4"
    make_video(source)
    cancel = Event()
    with pytest.raises(ConversionCancelled):
        manager().convert(source, ".mov", cancel=cancel, progress=lambda *_: cancel.set())
    assert not source.with_suffix(".mov").exists()
