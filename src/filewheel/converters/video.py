"""Bounded local FFmpeg video remuxing and transcoding."""

import os
import re
import shutil
import subprocess
from pathlib import Path
from time import monotonic
from typing import NamedTuple

from filewheel.converters.base import Capability, ConversionError, EngineOutput, check_cancel
from filewheel.converters.office import _stop_office_tree
from filewheel.paths import bundled_tool_root

_DURATION = re.compile(rb"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)")
_STREAM = re.compile(
    rb"Stream #\d+:(\d+).*?\b(Video|Audio|Subtitle|Data|Attachment|Unknown):\s*([^,\s]+)"
)
_DECODER = re.compile(rb"^\s*[A-Z.]{6}\s+(\S+)", re.MULTILINE)
VIDEO_INPUTS = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v")
AUDIO_INPUTS = (".mp3", ".m4a", ".wav", ".flac", ".ogg", ".opus")
VIDEO_EDGES = (
    (".mp4", ".mov"),
    (".mp4", ".mkv"),
    (".mp4", ".webm"),
    (".mov", ".mp4"),
    (".mov", ".mkv"),
    (".mov", ".webm"),
    (".mkv", ".mp4"),
    (".mkv", ".mov"),
    (".mkv", ".webm"),
    (".webm", ".mp4"),
    (".webm", ".mkv"),
    (".avi", ".mp4"),
    (".avi", ".mkv"),
    (".m4v", ".mp4"),
    (".m4v", ".mkv"),
)
VIDEO_OUTPUTS = (".mp4", ".mov", ".mkv", ".webm")
AUDIO_OUTPUTS = (".mp3", ".m4a", ".wav", ".flac")
MAX_INPUT = 20 * 1024 * 1024 * 1024
MAX_DURATION = 4 * 60 * 60

# Container-specific codecs accepted by the corresponding muxer. Other audio
# codecs are re-encoded when a decoder and target encoder are available.
_MKV_COPY_AUDIO = frozenset(
    {
        "aac",
        "ac3",
        "alac",
        "dts",
        "eac3",
        "flac",
        "mp2",
        "mp3",
        "opus",
        "pcm_s16be",
        "pcm_s16le",
        "pcm_s24be",
        "pcm_s24le",
        "pcm_s32be",
        "pcm_s32le",
        "truehd",
        "vorbis",
    }
)
_MP4_COPY_AUDIO = frozenset({"aac", "ac3", "alac", "eac3", "mp2", "mp3"})
_MOV_COPY_AUDIO = frozenset(
    {
        "aac",
        "ac3",
        "alac",
        "eac3",
        "mp2",
        "mp3",
        "pcm_s16be",
        "pcm_s16le",
        "pcm_s24be",
        "pcm_s24le",
        "pcm_s32be",
        "pcm_s32le",
    }
)
_WEBM_COPY_AUDIO = frozenset({"opus", "vorbis"})
_VIDEO_COPY_BY_CONTAINER = {
    ".mp4": frozenset({"av1", "h264", "hevc", "mjpeg", "mpeg4"}),
    ".mov": frozenset({"av1", "dnxhd", "dvvideo", "h264", "hevc", "mjpeg", "mpeg4", "prores"}),
    ".webm": frozenset({"av1", "vp8", "vp9"}),
}
_AUDIO_COPY_BY_CONTAINER = {
    ".mkv": _MKV_COPY_AUDIO,
    ".mp4": _MP4_COPY_AUDIO,
    ".mov": _MOV_COPY_AUDIO,
    ".webm": _WEBM_COPY_AUDIO,
}


class MediaStream(NamedTuple):
    index: int
    kind: str
    codec: str


class FfmpegEngine:
    engine_id = "ffmpeg"

    def __init__(self, executable=None, timeout=7200):
        self.executable = self._find(executable)
        self.timeout = timeout
        self.execution_timeouts = {extension: timeout for extension in VIDEO_INPUTS + AUDIO_INPUTS}
        self.encoder_listing = self._encoders()
        self._decoder_listing = None
        capabilities = list(self.video_capabilities)
        for capability in self.audio_capabilities:
            required = {
                ".mp3": b"libmp3lame",
                ".m4a": b"aac",
                ".wav": b"pcm_s16le",
                ".flac": b"flac",
            }[capability.output_extension]
            if required in self.encoder_listing:
                capabilities.append(capability)
        if b"libvpx-vp9" not in self.encoder_listing or b"libopus" not in self.encoder_listing:
            capabilities = [
                capability for capability in capabilities if capability.output_extension != ".webm"
            ]
        self.capabilities = tuple(capabilities)

    @staticmethod
    def _find(executable=None):
        candidates = [executable, os.getenv("FILEWHEEL_FFMPEG")]
        if os.getenv("FILEWHEEL_BUNDLED_TOOLS_ONLY") != "1":
            try:
                from filewheel.installation import selected_tool

                candidates.append(selected_tool("FFmpeg"))
            except OSError, ValueError:
                pass
            candidates.append(shutil.which("ffmpeg"))
        candidates.append(str(bundled_tool_root() / "tools/ffmpeg/ffmpeg.exe"))
        for candidate in candidates:
            if candidate and Path(candidate).is_file():
                return Path(candidate).resolve()
        return None

    def _encoders(self):
        if self.executable is None:
            return b""
        try:
            result = subprocess.run(
                [str(self.executable), "-hide_banner", "-encoders"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=8,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return (
                result.stdout
                if result.returncode == 0 and len(result.stdout) <= 8 * 1024 * 1024
                else b""
            )
        except OSError, subprocess.TimeoutExpired:
            return b""

    def _decoders(self):
        if self.executable is None:
            return frozenset()
        try:
            result = subprocess.run(
                [str(self.executable), "-hide_banner", "-decoders"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=8,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode != 0 or len(result.stdout) > 8 * 1024 * 1024:
                return frozenset()
            return frozenset(
                match.decode("ascii", errors="replace") for match in _DECODER.findall(result.stdout)
            )
        except OSError, subprocess.TimeoutExpired:
            return frozenset()

    @property
    def decoder_listing(self):
        if self._decoder_listing is None:
            self._decoder_listing = self._decoders()
        return self._decoder_listing

    def _run(
        self,
        args,
        *,
        workdir,
        timeout,
        cancel=None,
        progress=None,
        duration=None,
        loglevel="warning",
    ):
        check_cancel(cancel)
        stderr_path = workdir / "ffmpeg-stderr.log"
        progress_path = workdir / "ffmpeg-progress.txt"
        stderr_path.unlink(missing_ok=True)
        progress_path.unlink(missing_ok=True)
        environment = dict(os.environ)
        environment["AV_LOG_FORCE_NOCOLOR"] = "1"
        with stderr_path.open("wb") as stderr, progress_path.open("wb") as stdout:
            process = subprocess.Popen(
                [
                    str(self.executable),
                    "-nostdin",
                    "-hide_banner",
                    "-loglevel",
                    loglevel,
                    "-protocol_whitelist",
                    "file,pipe",
                    *args,
                    "-progress",
                    "pipe:1",
                    "-nostats",
                ],
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                cwd=workdir,
                env=environment,
                shell=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            deadline = monotonic() + timeout
            last_progress = 0
            try:
                while process.poll() is None:
                    check_cancel(cancel)
                    if monotonic() >= deadline:
                        raise ConversionError("FFmpeg conversion exceeded its time limit")
                    if stderr_path.stat().st_size > 256 * 1024:
                        raise ConversionError("FFmpeg diagnostic output exceeded its limit")
                    if progress is not None and progress_path.stat().st_size <= 64 * 1024:
                        raw = progress_path.read_bytes()
                        values = re.findall(rb"out_time_(?:us|ms)=(\d+)", raw)
                        if values and duration and duration > 0:
                            current = min(1.0, int(values[-1]) / (duration * 1_000_000))
                            last_progress = max(last_progress, current)
                            progress(0.15 + 0.7 * last_progress, "Converting media")
                    try:
                        process.wait(timeout=0.1)
                    except subprocess.TimeoutExpired:
                        pass
                check_cancel(cancel)
            except BaseException:
                _stop_office_tree(process, environment)
                raise
        return process.returncode, stderr_path.read_bytes()[: 256 * 1024]

    def _inspect(self, source, workdir, cancel, *, require_video):
        _code, diagnostic = self._run(
            ["-i", str(source)], workdir=workdir, timeout=20, cancel=cancel, loglevel="info"
        )
        match = _DURATION.search(diagnostic)
        if not match:
            raise ConversionError("FFmpeg could not read this media or determine its duration")
        hours, minutes, seconds = match.groups()
        duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        if not 0 < duration <= MAX_DURATION:
            raise ConversionError("Media duration exceeds the four-hour conversion limit")
        streams = [
            MediaStream(
                int(index),
                kind.decode("ascii"),
                codec.decode("ascii", errors="replace").lower(),
            )
            for index, kind, codec in _STREAM.findall(diagnostic)
        ]
        if require_video and not any(stream.kind == "Video" for stream in streams):
            raise ConversionError("The input does not contain a readable video stream")
        if not require_video and not any(stream.kind == "Audio" for stream in streams):
            raise ConversionError("The input does not contain a readable audio stream")
        return duration, diagnostic, streams

    @staticmethod
    def _incompatible(diagnostic):
        text = diagnostic.decode("utf-8", errors="replace").lower()
        return (
            "could not find tag for codec" in text
            or "no wav codec tag found for codec" in text
            or "codec not currently supported in container" in text
            or "only vp8 or vp9 or av1 video" in text
        )

    def available(self):
        return (
            self.executable is not None
            and 0 < self.timeout <= 7200
            and b"libx264" in self.encoder_listing
            and b"aac" in self.encoder_listing
        )

    def validate(self, output):
        if output.path.stat().st_size <= 1024:
            raise ConversionError("Generated media is too small to be valid")


class VideoEngine(FfmpegEngine):
    video_capabilities = tuple(
        Capability(source, "Video", target, target[1:].upper(), "ffmpeg")
        for source, target in VIDEO_EDGES
    )
    audio_capabilities = tuple(
        Capability(source, "Audio", target, target[1:].upper(), "ffmpeg")
        for source in (*VIDEO_INPUTS, *AUDIO_INPUTS)
        for target in AUDIO_OUTPUTS
        if source != target
    )
    capabilities = video_capabilities + audio_capabilities

    def convert(self, source, extension, workdir, progress, cancel):
        source = Path(source)
        extension = extension.lower()
        if extension in AUDIO_OUTPUTS:
            return self._convert_audio(source, extension, workdir, progress, cancel)
        if (source.suffix.lower(), extension) not in VIDEO_EDGES:
            raise ConversionError("This video conversion pair is unsupported")
        if source.stat().st_size > MAX_INPUT:
            raise ConversionError("Video exceeds the 20 GiB input limit")
        progress(0.05, "Inspecting video")
        duration, _diagnostic, streams = self._inspect(source, workdir, cancel, require_video=True)
        target = workdir / ("output" + extension)
        video_tracks = [stream for stream in streams if stream.kind == "Video"]
        audio_tracks = [stream for stream in streams if stream.kind == "Audio"]
        container = {".mkv": "matroska"}.get(extension, extension[1:])

        video_codec = video_tracks[0].codec
        video_copyable = extension == ".mkv" or video_codec in _VIDEO_COPY_BY_CONTAINER.get(
            extension, frozenset()
        )
        video_encoder = (
            None if video_copyable else ("libvpx-vp9" if extension == ".webm" else "libx264")
        )
        if video_encoder and video_encoder.encode() not in self.encoder_listing:
            raise ConversionError(f"This FFmpeg build lacks the {video_encoder} video encoder")

        audio_encoder = "libopus" if extension == ".webm" else "aac"
        audio_codec = "opus" if extension == ".webm" else "aac"
        audio_copyable = _AUDIO_COPY_BY_CONTAINER[extension]
        can_encode_audio = audio_encoder.encode() in self.encoder_listing
        audio_plan = []
        omitted_audio = []
        for stream in audio_tracks:
            if stream.codec in audio_copyable:
                audio_plan.append((stream, "copy"))
            elif can_encode_audio and stream.codec in self.decoder_listing:
                audio_plan.append((stream, audio_codec))
            else:
                omitted_audio.append(stream)

        if audio_tracks and not audio_plan:
            if any(stream.codec == "apple_apac" for stream in omitted_audio):
                raise ConversionError(
                    "The source contains Apple Positional Audio (apple_apac), which the bundled "
                    "FFmpeg cannot decode, and it has no other usable audio track. "
                    f"The {extension[1:].upper()} was not created."
                )
            codecs = ", ".join(sorted({stream.codec for stream in omitted_audio}))
            raise ConversionError(
                f"The bundled FFmpeg cannot decode or convert the source audio ({codecs}); "
                f"the {extension[1:].upper()} was not created."
            )

        args = ["-i", str(source), "-map", "0:v:0"]
        for stream, _mode in audio_plan:
            args.extend(["-map", f"0:{stream.index}"])
        args.extend(["-map_metadata", "0", "-map_chapters", "0"])
        if video_copyable:
            args.extend(["-c:v", "copy"])
        elif video_encoder == "libx264":
            args.extend(["-c:v", video_encoder, "-preset", "veryfast", "-crf", "23"])
        else:
            args.extend(
                [
                    "-c:v",
                    video_encoder,
                    "-deadline",
                    "realtime",
                    "-cpu-used",
                    "6",
                    "-b:v",
                    "2M",
                ]
            )
        expected_audio = []
        for ordinal, (stream, mode) in enumerate(audio_plan):
            output_codec = stream.codec if mode == "copy" else audio_codec
            expected_audio.append(output_codec)
            args.extend([f"-c:a:{ordinal}", "copy" if mode == "copy" else audio_encoder])
            if mode != "copy":
                args.extend([f"-b:a:{ordinal}", "128k" if audio_codec == "opus" else "192k"])
        if extension in (".mp4", ".mov"):
            args.extend(["-movflags", "+faststart"])

        progress(
            0.15,
            "Copying compatible streams"
            if video_copyable and all(mode == "copy" for _stream, mode in audio_plan)
            else "Preparing compatible streams and required re-encoding",
        )
        code, diagnostic = self._run(
            [*args, "-f", container, str(target)],
            workdir=workdir,
            timeout=self.timeout,
            cancel=cancel,
            progress=progress,
            duration=duration,
        )
        if code:
            raise ConversionError(
                f"FFmpeg could not produce the requested {extension[1:].upper()}. "
                + diagnostic.decode("utf-8", errors="replace")[-600:]
            )
        check_cancel(cancel)
        if not target.is_file() or target.stat().st_size <= 1024:
            raise ConversionError("FFmpeg produced an empty or incomplete video")
        output_duration, _output_info, output_streams = self._inspect(
            target, workdir, cancel, require_video=True
        )
        if abs(output_duration - duration) > max(2.0, duration * 0.02):
            raise ConversionError("Converted video duration differs from the source")
        output_video = [stream for stream in output_streams if stream.kind == "Video"]
        output_audio = [stream for stream in output_streams if stream.kind == "Audio"]
        expected_video = (
            video_codec if video_copyable else ("vp9" if video_encoder == "libvpx-vp9" else "h264")
        )
        if not output_video or output_video[0].codec != expected_video:
            raise ConversionError("The output did not preserve or encode the primary video stream")
        if [stream.codec for stream in output_audio] != expected_audio:
            raise ConversionError("The output did not preserve every selected audio track")

        warnings = []
        if video_encoder:
            name = "VP9" if video_encoder == "libvpx-vp9" else "H.264"
            warnings.append(f"Video was re-encoded as {name}; review quality.")
        for stream, mode in audio_plan:
            if mode != "copy":
                warnings.append(
                    f"Audio track {stream.index} ({stream.codec}) was re-encoded as "
                    f"{audio_codec.upper()}."
                )
        for stream in omitted_audio:
            if stream.codec == "apple_apac":
                reason = "the bundled FFmpeg cannot decode it"
            elif stream.codec not in self.decoder_listing:
                reason = "the bundled FFmpeg has no decoder for it"
            else:
                reason = f"no {audio_codec.upper()} encoder is available"
            warnings.append(
                f"Audio track {stream.index} ({stream.codec}) was omitted because {reason}."
            )
        if any(stream.kind == "Subtitle" for stream in streams):
            warnings.append("Subtitle tracks were not copied.")
        if any(stream.kind == "Data" for stream in streams):
            warnings.append("Data tracks were not copied.")
        if any(stream.kind == "Attachment" for stream in streams):
            warnings.append("Attachment tracks were not copied.")
        if len(video_tracks) > 1:
            warnings.append("Only the primary video track was included.")
        progress(0.85, "Validating converted video")
        return (EngineOutput(target, source.with_suffix(extension).name, tuple(warnings)),)

    def _convert_audio(self, source, extension, workdir, progress, cancel):
        source = Path(source)
        input_extension = source.suffix.lower()
        if input_extension not in (*VIDEO_INPUTS, *AUDIO_INPUTS) or input_extension == extension:
            raise ConversionError("This audio conversion pair is unsupported")
        if source.stat().st_size > MAX_INPUT:
            raise ConversionError("Media exceeds the 20 GiB input limit")
        progress(0.05, "Inspecting audio")
        duration, _diagnostic, streams = self._inspect(
            source, workdir, cancel, require_video=input_extension in VIDEO_INPUTS
        )
        audio_streams = [stream for stream in streams if stream.kind == "Audio"]
        if not audio_streams:
            raise ConversionError("The input does not contain an audio stream")
        target = workdir / ("output" + extension)
        output_codec, profile, container = {
            ".mp3": ("mp3", ["-c:a", "libmp3lame", "-q:a", "2"], "mp3"),
            ".m4a": ("aac", ["-c:a", "aac", "-b:a", "192k"], "ipod"),
            ".wav": ("pcm_s16le", ["-c:a", "pcm_s16le"], "wav"),
            ".flac": ("flac", ["-c:a", "flac"], "flac"),
        }[extension]
        copyable = {
            ".mp3": ("mp3", "mp3"),
            ".m4a": ("aac", "ipod"),
            ".wav": ("pcm_s16le", "wav"),
            ".flac": ("flac", "flac"),
        }
        encoder_for_output = {
            ".mp3": b"libmp3lame",
            ".m4a": b"aac",
            ".wav": b"pcm_s16le",
            ".flac": b"flac",
        }[extension]
        can_encode = encoder_for_output in self.encoder_listing
        usable = [
            stream
            for stream in audio_streams
            if stream.codec == copyable[extension][0]
            or (can_encode and stream.codec in self.decoder_listing)
        ]
        if not usable:
            codecs = ", ".join(sorted({stream.codec for stream in audio_streams}))
            if any(stream.codec == "apple_apac" for stream in audio_streams):
                raise ConversionError(
                    "The source contains Apple Positional Audio (apple_apac), which the bundled "
                    "FFmpeg cannot decode, and it has no other usable audio track. "
                    "No audio output was created."
                )
            raise ConversionError(
                f"The bundled FFmpeg cannot decode or convert the source audio ({codecs}); "
                "no audio output was created."
            )
        selected = usable[0]
        codec = selected.codec
        copied = codec == copyable[extension][0]
        common = ["-i", str(source), "-map", f"0:{selected.index}", "-vn", "-map_metadata", "0"]
        progress(0.15, "Trying lossless audio stream copy")
        if copied:
            code, diagnostic = self._run(
                [*common, "-c:a", "copy", "-f", container, str(target)],
                workdir=workdir,
                timeout=self.timeout,
                cancel=cancel,
                progress=progress,
                duration=duration,
            )
        else:
            code = 1
        if code and copied and not self._incompatible(diagnostic):
            raise ConversionError(
                "FFmpeg audio stream copy failed. "
                + diagnostic.decode("utf-8", errors="replace")[-600:]
            )
        if code:
            target.unlink(missing_ok=True)
            check_cancel(cancel)
            if not can_encode:
                raise ConversionError(f"This FFmpeg build lacks the {output_codec} audio encoder")
            progress(0.15, "Re-encoding audio")
            code, diagnostic = self._run(
                [*common, *profile, "-f", container, str(target)],
                workdir=workdir,
                timeout=self.timeout,
                cancel=cancel,
                progress=progress,
                duration=duration,
            )
        if code:
            raise ConversionError(
                "FFmpeg could not produce the requested audio. "
                + diagnostic.decode("utf-8", errors="replace")[-600:]
            )
        if not target.is_file() or target.stat().st_size <= 1024:
            raise ConversionError("FFmpeg produced an empty or incomplete audio file")
        output_duration, _output_info, _output_streams = self._inspect(
            target, workdir, cancel, require_video=False
        )
        if input_extension in VIDEO_INPUTS:
            if output_duration > duration + max(2.0, duration * 0.02):
                raise ConversionError("Extracted audio exceeds the source video duration")
        elif abs(output_duration - duration) > max(2.0, duration * 0.02):
            raise ConversionError("Converted audio duration differs from the source")
        warnings = []
        if not copied:
            warnings.append(f"Audio was re-encoded as {output_codec.upper()}.")
        if (
            extension == ".flac"
            and codec not in ("flac", "alac", "truehd", "wavpack")
            and not codec.startswith("pcm_")
        ):
            warnings.append(
                "FLAC preserves the decoded source audio; it cannot restore quality lost earlier."
            )
        for stream in audio_streams:
            if stream == selected:
                continue
            reason = (
                "the bundled FFmpeg cannot decode it"
                if stream.codec == "apple_apac" or stream.codec not in self.decoder_listing
                else "only one audio track can be extracted at a time"
            )
            warnings.append(
                f"Audio track {stream.index} ({stream.codec}) was omitted because {reason}."
            )
        progress(0.85, "Validating converted audio")
        return (EngineOutput(target, source.with_suffix(extension).name, tuple(warnings)),)
