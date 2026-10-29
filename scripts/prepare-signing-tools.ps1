$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$manifest = Get-Content (Join-Path $repoRoot 'packaging/native-artifacts.json') -Raw | ConvertFrom-Json
$toolRoot = Join-Path $repoRoot 'build/release-tools'
if (Test-Path -LiteralPath $toolRoot) {
    throw "Release tool staging already exists: $toolRoot"
}
[void](New-Item -ItemType Directory -Path $toolRoot)

function Get-PinnedArtifact {
    param([string]$Name, [object]$Artifact, [string]$Extension)
    $download = Join-Path $toolRoot ($Name + $Extension)
    & curl.exe -fL --retry 3 --retry-delay 2 --output $download $Artifact.url
    if ($LASTEXITCODE -ne 0) { throw "Download failed: $Name" }
    $actual = (Get-FileHash -LiteralPath $download -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $Artifact.sha256.ToLowerInvariant()) {
        throw "SHA-256 mismatch for $Name; expected $($Artifact.sha256), got $actual"
    }
    return $download
}

$officeMsi = Get-PinnedArtifact -Name 'libreoffice' -Artifact $manifest.libreoffice -Extension '.msi'
$officeExtract = Join-Path $toolRoot 'libreoffice-extracted'
[void](New-Item -ItemType Directory -Path $officeExtract)
$msiArgs = '/a "' + $officeMsi + '" /qn TARGETDIR="' + $officeExtract + '"'
$msi = Start-Process -FilePath 'msiexec.exe' -ArgumentList $msiArgs -Wait -PassThru -WindowStyle Hidden
if ($msi.ExitCode -ne 0) { throw "LibreOffice MSI extraction failed: $($msi.ExitCode)" }
$officeExe = @(Get-ChildItem -LiteralPath $officeExtract -Filter 'soffice.exe' -Recurse -File)
if ($officeExe.Count -ne 1) { throw "Expected one LibreOffice executable; found $($officeExe.Count)" }
$officeRoot = $officeExe[0].Directory.Parent.FullName
if (-not (Test-Path -LiteralPath (Join-Path $officeRoot 'license.txt'))) {
    throw 'Extracted LibreOffice license file is missing'
}

$pandocZip = Get-PinnedArtifact -Name 'pandoc' -Artifact $manifest.pandoc -Extension '.zip'
$pandocExtract = Join-Path $toolRoot 'pandoc-extracted'
Expand-Archive -LiteralPath $pandocZip -DestinationPath $pandocExtract
$pandocExe = @(Get-ChildItem -LiteralPath $pandocExtract -Filter 'pandoc.exe' -Recurse -File)
if ($pandocExe.Count -ne 1) { throw "Expected one Pandoc executable; found $($pandocExe.Count)" }
$pandocRoot = $pandocExe[0].Directory.FullName
if (-not (Test-Path -LiteralPath (Join-Path $pandocRoot 'COPYRIGHT.txt'))) {
    throw 'Extracted Pandoc copyright file is missing'
}

$ffmpegArchive = Get-PinnedArtifact -Name 'ffmpeg' -Artifact $manifest.ffmpeg -Extension '.7z'
$sevenZip = Get-Command '7z.exe' -ErrorAction SilentlyContinue
if ($sevenZip) { $sevenZipPath = $sevenZip.Source }
else { $sevenZipPath = 'C:\Program Files\7-Zip\7z.exe' }
if (-not (Test-Path -LiteralPath $sevenZipPath -PathType Leaf)) {
    throw '7-Zip is required to extract the pinned FFmpeg archive'
}
$ffmpegExtract = Join-Path $toolRoot 'ffmpeg-extracted'
[void](New-Item -ItemType Directory -Path $ffmpegExtract)
& $sevenZipPath x -y "-o$ffmpegExtract" $ffmpegArchive | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'FFmpeg extraction failed' }
$ffmpegExe = @(Get-ChildItem -LiteralPath $ffmpegExtract -Filter 'ffmpeg.exe' -Recurse -File)
if ($ffmpegExe.Count -ne 1) { throw "Expected one FFmpeg executable; found $($ffmpegExe.Count)" }
$ffmpegRoot = Join-Path $toolRoot 'ffmpeg'
[void](New-Item -ItemType Directory -Path $ffmpegRoot)
Copy-Item -LiteralPath $ffmpegExe[0].FullName -Destination (Join-Path $ffmpegRoot 'ffmpeg.exe')
$ffmpegPackage = $ffmpegExe[0].Directory.Parent.FullName
$ffmpegLicense = @('LICENSE', 'COPYING.GPLv3') | ForEach-Object {
    Join-Path $ffmpegPackage $_
} | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $ffmpegLicense) { throw 'FFmpeg archive has no distribution license' }
Copy-Item -LiteralPath $ffmpegLicense -Destination (Join-Path $ffmpegRoot 'COPYING.GPLv3')

Write-Output "LibreOffice: $officeRoot"
Write-Output "Pandoc: $pandocRoot"
Write-Output "FFmpeg: $(Join-Path $ffmpegRoot 'ffmpeg.exe')"
if ($env:GITHUB_OUTPUT) {
    Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "libreoffice=$officeRoot"
    Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "pandoc=$pandocRoot"
    Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "ffmpeg=$(Join-Path $ffmpegRoot 'ffmpeg.exe')"
}
