# Tagged cross-platform release

The Linux branch retains the shared Windows code. A release tag points to one
commit; GitHub releases are repository-wide, not separate per branch. v0.3.1 is
built from feat/linux-port without merging into or changing main.

Pushing tag v0.3.1 runs publish-release.yml. It calls independent Linux and
Windows build workflows at that same commit. Both must finish build, frozen
smoke checks, provenance attestation and artifact upload before publication.
No workstation binaries are uploaded. A failed job prevents release publication;
inspect its logs, fix source on the branch and arrange a fresh release tag/version
rather than silently moving a published tag. A failed run can be rerun for transient
runner/download failures from the Actions page.

Linux uses the Ubuntu22.04 baseline Docker build, hashed Python/native downloads,
actual AppImage checks and an offline Debian12 runtime with no Python/converter
tools installed. Windows builds on windows-2025/Python3.14 with pinned inputs,
Inno Setup and a frozen Quick/conversion check. Native versions/manifests and
source metadata accompany downloads. Mutable apt repositories and runner images
mean this is not a bit-identical rebuild guarantee.

Build jobs have contents-read and OIDC/attestation write permissions. Only the
final publishing job has contents-write. Attestations link binaries to the
workflow/source, not absence of malware. Windows binaries are not Authenticode
signed. Review license/source obligations before wider redistribution; preserve
the embedded notices/source and native tool materials.

Verify downloads with SHA256SUMS.txt and:

    gh attestation verify FilewheelSetup.exe --repo artlsvy/FileWheelie-Windows
    gh attestation verify Filewheel-Linux-x86_64.AppImage --repo artlsvy/FileWheelie-Windows

The standalone build workflows remain manually runnable on a selected branch;
manual runs produce CI artifacts, not public releases. Future release tags must
be explicitly added to the publish workflow's tag allowlist.

## CI-only retries of 0.3.1

The initial Windows job passed; the Linux container checks passed but its hosted
AppImage smoke failed. Build tags `build-v0.3.1-*` allow CI configuration/runtime
fixes without moving the original v0.3.1 source tag. Both reusable workflows
explicitly check out v0.3.1, while their orchestration comes from the build tag.
The publish job still targets the original v0.3.1 release. Manifests record the
checked-out application source; attestations record the orchestrating workflow.
No version tag is rewritten and no workstation binaries replace CI output.

## Completed publication recovery

Both builds succeeded in producer run41131902385. Its publishing step failed on
a nested Linux artifact layout. scripts/assemble_release.py now accepts flat and
nested layouts and rejects missing/ambiguous files. The narrowly scoped
publish-031-artifacts.yml is triggered by publish-v0.3.1-* tags. It verifies the
fixed producer SHA/event, both successful platform jobs/attestations, downloads
those exact run artifacts, and checks installer hashes against the recorded
attestation digests before creating v0.3.1. Run41133689982 published successfully.
This avoids rebuilding or retagging accepted application source. Future versions
should use the ordinary gated pipeline, not these fixed-version recovery paths.
