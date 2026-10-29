# Code signing policy

## Current status

The v0.3 installer is unsigned. Do not interpret its SHA-256 checksum as a
publisher signature. SignPath Foundation signing is planned; no Filewheel
download is described as SignPath-signed until its Authenticode signature has
been verified and the signed release has been published.

Once the project is approved: **Free code signing provided by
[SignPath.io](https://signpath.io), certificate by
[SignPath Foundation](https://signpath.org).** The Windows publisher shown for
those releases will be SignPath Foundation.

## Maintainers and approval

- Committer and reviewer: [@artlsvy](https://github.com/artlsvy).
- Release signing approver: [@artlsvy](https://github.com/artlsvy).
- Changes from other contributors must be reviewed before they enter a release.
- The maintainer enables multifactor authentication on GitHub and SignPath.
- Every signing request requires manual approval after the build and artifact
  provenance have been reviewed.

## What may be signed

- Filewheel's own executable and Windows installer, built by a public release
  workflow from a tagged commit in this repository.
- The corresponding version, product name, source revision, and dependency
  checksums must be recorded with each release.
- Bundled upstream tools retain their own signatures or unsigned status. The
  Filewheel signing identity must not be used to sign third-party binaries.
- Artifacts built on a personal computer are not submitted for Foundation
  signing. The current locally built v0.3 installer is outside this policy.

The release workflow will verify pinned Python packages and native tool
downloads, build the installer, request SignPath signing, verify the returned
Authenticode signature, then publish the signed asset and its new SHA-256.

## Privacy and system changes

Filewheel converts files locally. It will not transfer information to other
networked systems unless the user explicitly requests such a transfer. Its
installer offers optional login startup, desktop shortcut, and Explorer Send to
entries; it also provides a Windows uninstall entry. See [README.md](README.md)
and [INSTALL.md](INSTALL.md) for details.

## Verify a future signed download

Download the installer from the project's GitHub release. Compare its SHA-256
with the release checksum, then run:

```powershell
Get-AuthenticodeSignature .\FilewheelSetup.exe |
  Select-Object Status, @{Name='Publisher';Expression={$_.SignerCertificate.Subject}}
```

For a release advertised as SignPath-signed, `Status` must be `Valid` and the
publisher must be SignPath Foundation. A checksum alone cannot establish the
publisher's identity.
