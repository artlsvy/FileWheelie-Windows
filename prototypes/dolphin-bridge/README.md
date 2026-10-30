# Private native-Wayland Dolphin URI prototype

User explicitly authorized this isolated experiment. It is **not** a supported
Dolphin plugin, a replacement for system Dolphin, or a distributable Linux port.
No conversion, global mouse hook, KWin binary plugin or production app is added.

## Contract

The small `clicked-uri.patch` modifies Dolphin 25.12.3's actual
`DolphinView::slotItemMiddleClicked(index)` handler. Dolphin's controller only
emits this after matching press/release over the same item. The handler takes
the URI from `m_model->fileItem(index)`, not the selected item or displayed name.

Only the privately launched process has the opt-in destination/secret variables.
It forwards local regular-file clicks as a directed session-bus signal with the
URI, per-process sequence and CLOCK_MONOTONIC nanoseconds. That private click
does not also open the normal default application. Folders and unconfigured
instances keep their normal behavior. No installed Dolphin files/configuration
are changed. A successfully queued signal is not proof of receiver acceptance;
the receiver report is authoritative for this experiment.

The receiver verifies session-bus sender PID and executable against its own
launched child, a run-specific token, increasing sequence, <=2 second age, and
membership in its scratch fixture set. It validates current regular-file state
and rejects links/remote URLs. Only relative fixture paths enter the report.
No TargetResolution or conversion is produced. Credentials do not defend against
an attacker already able to modify/read all processes under the same Unix UID.

## Build and run

Docker's Ubuntu 26.04 build installs dependencies **inside the container only**.
The exact 25.12.3 source directory must exist; the patch is dry-run before apply.
This prototype build is not a locked release build or a universal Linux binary.

```bash
docker build --progress plain -t filewheel-dolphin-probe:25.12.3 prototypes/dolphin-bridge
/usr/bin/python3 prototypes/dolphin-bridge/extract.py
```

Extract `/opt/filewheel-dolphin-probe` from that image into an ignored `build/`
directory using a newly created stopped container, then remove only that temporary
container. Do not copy anything into `/usr` or install the container's DEBs on the
host. Run the extracted binary with its matching private `lib` directory:

```bash
/usr/bin/python3 prototypes/dolphin-bridge/receiver.py \
  --dolphin build/dolphin-probe/bin/dolphin \
  --library-dir build/dolphin-probe/lib/x86_64-linux-gnu \
  --seconds 180 --report /tmp/fw-clicked-uri.json
```

The receiver opens a private Dolphin with scratch tabs **Tab A / Tab B**, each
containing the same filenames. New reports must not already exist. First select
`previous selection.txt` with the left button, then middle-click `report.txt`,
`report.csv` and `unicode-æøå.txt` without first selecting them, in both tabs.
Compare each printed ACCEPTED relative path against the tab/file clicked.
Do not count fixture membership alone as proof that the right file was clicked.

It exits after the chosen duration (maximum 300 s), closes only its child and
removes scratch files. Ctrl+C also enters cleanup. The test uses private XDG
config/state/cache/data directories, not your normal Dolphin preferences.

```bash
/usr/bin/python3 prototypes/dolphin-bridge/test_receiver.py
```

Remaining acceptance: real middle-click/touchpad, active-tab correctness, large
and grouped folders, cancellation of stale requests and conversion integration.
Previously demonstrated KWin placement is separate; this prototype does not yet
display a Filewheel wheel. Do not claim stock-Dolphin or general Wayland support.
