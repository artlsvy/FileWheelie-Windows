"""Filewheel: private local conversion with optional portable engines."""

import os

# Set before optional Magika/ONNX imports, including worker initialization.
# Filewheel has no telemetry opt-in or cloud conversion path.
os.environ["ORT_DISABLE_TELEMETRY"] = "1"
