param(
    [string]$Destination = '',
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($Destination)) {
    $codexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
    $Destination = Join-Path $codexRoot 'skills'
}
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceSkill = Join-Path $repoRoot 'plugins\painterx\skills\painterx'
$target = Join-Path ([IO.Path]::GetFullPath($Destination)) 'painterx'
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
if ((Test-Path -LiteralPath $target) -and -not $Force) { throw "Target exists: $target (pass -Force to replace it)" }
if (Test-Path -LiteralPath $target) {
    $backup = "$target.backup.$([DateTime]::Now.ToString('yyyyMMddHHmmss'))"
    Move-Item -LiteralPath $target -Destination $backup
    Write-Output "Existing skill moved to: $backup"
}
New-Item -ItemType Directory -Force -Path $target | Out-Null
& robocopy $sourceSkill $target /E /XD .venv __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed with exit code $LASTEXITCODE" }
Write-Output "INSTALL_OK|skill=$target"
