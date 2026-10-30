# Read-only KDE offer-order acceptance probe

This is a development check, not a runtime dependency or a mouse hook. It prints
`KApplicationTrader::queryByMimeType`, the exact list used by stock Dolphin25.12.3.
Build against the target's Qt/KF6; the existing isolated build image matches this
Kubuntu26.04 host. No host development packages or system Dolphin changes needed.

```sh
mkdir -p build/dolphin-association-check
docker run --rm --network none \
  -v "$PWD/prototypes/dolphin-associations:/source:ro" \
  -v "$PWD/build/dolphin-association-check:/output" \
  filewheel-dolphin-probe:25.12.3 sh -c \
  'c++ -fPIC /source/query.cpp -o /output/query -I/usr/include/KF6/KService $(pkg-config --cflags --libs Qt6Core) -lKF6Service'
PYTHONPATH=src .venv-ui/bin/python prototypes/dolphin-associations/check.py \
  --probe build/dolphin-association-check/query --report /tmp/fw-mime-acceptance.json
```

The Python check creates temporary XDG preferences/launchers/cache, sets up second
position for PNG/PDF, checks the real KDE ordering, removes setup and verifies the
original first/second apps return. It never executes fixture desktop launchers.
It does not prove a hardware click, other desktop support or native popup placement.
