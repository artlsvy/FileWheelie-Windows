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

    gh attestation verify FilewheelSetup.exe --repo artlsvy/fileconverter
    gh attestation verify Filewheel-Linux-x86_64.AppImage --repo artlsvy/fileconverter

The standalone build workflows remain manually runnable on a selected branch;
manual runs produce CI artifacts, not public releases. Future release tags must
be explicitly added to the publish workflow's tag allowlist.
