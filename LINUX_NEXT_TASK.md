# Completed: cross-platform0.3.1 released through GitHub Actions

Release: https://github.com/artlsvy/FileWheelie-Windows/releases/tag/v0.3.1
Both platform jobs passed in producer run41131902385; publisher run41133689982
successfully released those exact CI artifacts. Both installers, build manifests,
SHA-256 checksums and GitHub provenance attestations are available. Application
source tagv0.3.1 remains416dac5; CI-only build/publish tags preserve that source.
Evidence: linux-evidence/release-0.3.1.json. Local143 passed /4 intentional skips.
No workstation binaries substituted. No main merge or source tag rewrite.

The initial Linux host smoke failed; runner desktop dependencies and retained
failure logs were added, and retry passed. Initial publish assumed flat artifact
paths; scripts/assemble_release.py fixes nested layouts with3 regression checks.
The recovery workflow is pinned to verified producer artifacts and their attested
digests. RELEASING.md records the source/build separation and provenance limits.

Current user request complete: branch committed/pushed, README updated, release
published. Further work requires a new task; GNOME integration remains deferred.
Preserve unrelated untracked assets/ui/wheel.jpg and wheel (2).pdf/.png.
