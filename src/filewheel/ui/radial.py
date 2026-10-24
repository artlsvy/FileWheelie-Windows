"""Preview capabilities and menu transitions, independent of Qt and filesystems."""

from dataclasses import dataclass
from pathlib import PureWindowsPath

from filewheel.core.models import TargetResolution

CATEGORIES = ("Image", "Document", "Markdown/Text", "Audio", "Video")


@dataclass(frozen=True)
class PreviewCapability:
    input_extension: str
    category: str
    output_extension: str
    label: str

    def __post_init__(self):
        for extension in (self.input_extension, self.output_extension):
            if not extension.startswith(".") or not extension[1:].isascii() or not extension[1:].isalnum():
                raise ValueError("ordinary dotted extensions required")
        if self.category not in CATEGORIES or not self.label.strip():
            raise ValueError("known category and nonempty label required")
        if self.input_extension.lower() == self.output_extension.lower():
            raise ValueError("preview cannot overwrite its own input format")


@dataclass(frozen=True)
class CapabilityRegistry:
    """Declared UI preview edges only: this registry attests no conversion engine."""

    capabilities: tuple[PreviewCapability, ...]

    def __post_init__(self):
        object.__setattr__(self, "capabilities", tuple(self.capabilities))
        keys = [(c.input_extension.lower(), c.category, c.output_extension.lower())
                for c in self.capabilities]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate preview capability")

    def categories(self, path: PureWindowsPath) -> tuple[str, ...]:
        return tuple(category for category in CATEGORIES if self.formats(path, category))

    def formats(self, path: PureWindowsPath, category: str) -> tuple[PreviewCapability, ...]:
        return tuple(c for c in self.capabilities
                     if c.input_extension.lower() == path.suffix.lower() and c.category == category)


def _defaults():
    edges = []
    for source in (".png", ".jpg", ".jpeg", ".webp", ".tiff", ".heic"):
        for output, label in ((".jpg", "JPEG"), (".png", "PNG"), (".webp", "WebP"), (".tiff", "TIFF")):
            if source != output and not (source == ".jpeg" and output == ".jpg"):
                edges.append(PreviewCapability(source, "Image", output, label))
        edges.append(PreviewCapability(source, "Document", ".pdf", "PDF"))
    for source in (".docx", ".pdf", ".pptx", ".xlsx", ".html"):
        edges.append(PreviewCapability(source, "Markdown/Text", ".md", "Markdown"))
    edges.extend((PreviewCapability(".pdf", "Document", ".docx", "DOCX"),
                  PreviewCapability(".docx", "Document", ".pdf", "PDF"),
                  PreviewCapability(".pdf", "Image", ".png", "PNG"),
                  PreviewCapability(".md", "Document", ".docx", "DOCX")))
    # Audio/video are declared optional FFmpeg previews, never installed engines.
    for source in (".mp3", ".wav", ".flac"):
        for output in (".mp3", ".wav", ".flac"):
            if source != output:
                edges.append(PreviewCapability(source, "Audio", output, output[1:].upper()))
    for source in (".mp4", ".mkv", ".webm"):
        for output in (".mp4", ".mkv", ".webm"):
            if source != output:
                edges.append(PreviewCapability(source, "Video", output, output[1:].upper()))
    return CapabilityRegistry(tuple(edges))


DEFAULT_PREVIEW_REGISTRY = _defaults()


@dataclass(frozen=True)
class DryRunSelection:
    input_path: PureWindowsPath
    category: str
    output_extension: str
    intended_path: PureWindowsPath
    action: str = "dry_run_only"

    @property
    def original_format(self):
        return self.input_path.suffix[1:].upper() or "Unknown"


class RadialState:
    """One invocation; a confirmation is terminal until dismissed or reopened."""

    def __init__(self, registry=DEFAULT_PREVIEW_REGISTRY):
        self.registry = registry
        self.target = None
        self.category = None
        self.selection = None
        self.stage = "closed"

    def open(self, target):
        self.dismiss()
        if not isinstance(target, TargetResolution):
            return False
        self.target = target
        self.stage = "categories"
        return True

    @property
    def options(self):
        if self.stage == "categories":
            return self.registry.categories(self.target.path)
        if self.stage == "formats":
            return self.registry.formats(self.target.path, self.category)
        return ()

    def choose(self, index):
        if type(index) is not int or not 0 <= index < len(self.options):
            return None
        option = self.options[index]
        if self.stage == "categories":
            self.category = option
            self.stage = "formats"
        elif self.stage == "formats":
            self.selection = DryRunSelection(self.target.path, self.category,
                                            option.output_extension,
                                            self.target.path.with_suffix(option.output_extension))
            self.stage = "confirmation"
        return self.selection

    def back(self):
        if self.stage == "formats":
            self.category = None
            self.stage = "categories"
            return True
        return False

    def dismiss(self):
        self.target = None
        self.category = None
        self.selection = None
        self.stage = "closed"
