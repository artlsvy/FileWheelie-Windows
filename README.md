# Filewheel

Private, local-first **Windows 11** file converter for personal/family use.
Middle-click an Explorer file, choose a format in the glass wheel, and convert
locally. No accounts, uploads or telemetry. Send to and the Widgets fallback remain.

The family build is a single executable containing Python, Qt, conversion engines,
Pandoc and LibreOffice. See [single EXE delivery](docs/SINGLE_EXE.md) for build and
verification instructions. The diagnostic onedir build is in
[PACKAGING.md](docs/PACKAGING.md); development setup uses
[scripts/setup-windows.ps1](scripts/setup-windows.ps1) with Python 3.14.

The Quick glass UI uses the tested OpenGL preference on Windows. Explicit graphics
settings and `--ui-backend widgets` are available. The user accepted F5 progress
reliability and cancellation; evidence is in
[F5_RENDERER_RELIABILITY.md](docs/F5_RENDERER_RELIABILITY.md).

See [conversion capabilities](docs/CONVERSION_MATRIX.md),
[status](docs/STATUS.md), [next task](docs/NEXT_TASK.md) and
[decisions](docs/DECISIONS.md). Linux is not a supported target; earlier Linux
measurements are retained only as historical project evidence.
