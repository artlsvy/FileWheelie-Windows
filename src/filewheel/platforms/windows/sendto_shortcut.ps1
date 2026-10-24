param(
    [Parameter(Mandatory = $true)][ValidateSet('stage', 'install', 'remove')][string]$Action,
    [Parameter(Mandatory = $true)][string]$PlanFile
)
$ErrorActionPreference = 'Stop'
try {
    $plan = Get-Content -LiteralPath $PlanFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($plan.description -ne 'Filewheel explicit-path diagnostic v1' -or
        $plan.name -ne 'Filewheel diagnostic.lnk') { throw 'Invalid shortcut plan' }
    if ($Action -eq 'stage') {
        $directory = $plan.stage_directory
    } else {
        $directory = [Environment]::GetFolderPath([Environment+SpecialFolder]::SendTo)
        if ([string]::IsNullOrWhiteSpace($directory)) { throw 'Personal SendTo folder unavailable' }
    }
    $shortcutPath = Join-Path $directory $plan.name
    $shell = New-Object -ComObject WScript.Shell
    try {
        if (Test-Path -LiteralPath $shortcutPath) {
            $existing = $shell.CreateShortcut($shortcutPath)
            try {
                $owned = $existing.Description -ceq $plan.description -and
                    [string]::Equals($existing.TargetPath, $plan.target, [StringComparison]::OrdinalIgnoreCase) -and
                    [string]::Equals($existing.WorkingDirectory, $plan.working_directory, [StringComparison]::OrdinalIgnoreCase) -and
                    $existing.Arguments -ceq $plan.arguments
                if (-not $owned) { throw 'Existing shortcut differs; refusing to overwrite or remove it' }
            } finally {
                [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($existing)
            }
            if ($Action -eq 'remove') {
                Remove-Item -LiteralPath $shortcutPath
                Write-Output "Removed: $shortcutPath"
            } else {
                Write-Output "Already configured: $shortcutPath"
            }
            exit 0
        }
        if ($Action -eq 'remove') {
            Write-Output 'Filewheel Send to shortcut is not installed'
            exit 0
        }
        if (-not (Test-Path -LiteralPath $plan.target -PathType Leaf)) { throw 'Python executable missing' }
        if (-not (Test-Path -LiteralPath $plan.working_directory -PathType Container)) { throw 'Project root missing' }
        [void][IO.Directory]::CreateDirectory($directory)
        [void][IO.Directory]::CreateDirectory($plan.output_directory)
        # Save to our own new name, then move without replacement. This also
        # preserves a shortcut created by somebody else after the existence check.
        $temporaryShortcut = Join-Path $directory ('filewheel-stage-' + [guid]::NewGuid().ToString('N') + '.lnk')
        try {
            $shortcut = $shell.CreateShortcut($temporaryShortcut)
            try {
                $shortcut.TargetPath = $plan.target
                $shortcut.Arguments = $plan.arguments
                $shortcut.WorkingDirectory = $plan.working_directory
                $shortcut.Description = $plan.description
                $shortcut.Save()
            } finally {
                [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shortcut)
            }
            [IO.File]::Move($temporaryShortcut, $shortcutPath)
        } finally {
            if (Test-Path -LiteralPath $temporaryShortcut) {
                Remove-Item -LiteralPath $temporaryShortcut
            }
        }
        Write-Output "Created: $shortcutPath"
    } finally {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell)
    }
} catch {
    Write-Error 'Filewheel shortcut operation failed; no existing differing shortcut was replaced'
    exit 1
}
