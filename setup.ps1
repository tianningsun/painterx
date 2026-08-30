param(
    [string]$Destination = '',
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($Destination)) {
    $codexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
    $Destination = Join-Path $codexRoot 'skills'
}
& (Join-Path $repoRoot 'install.ps1') -Destination $Destination -Force:$Force
$skillRoot = Join-Path ([IO.Path]::GetFullPath($Destination)) 'painterx'
& py -3 -m venv (Join-Path $skillRoot '.venv')
$python = Join-Path $skillRoot '.venv\Scripts\python.exe'
& $python -m pip install --disable-pip-version-check -r (Join-Path $repoRoot 'requirements.lock')
& $python (Join-Path $repoRoot 'doctor.py') --skill-root $skillRoot
Write-Output "SETUP_OK|version=0.4.0-desktop.3|skill=$skillRoot"
Write-Output 'Restart Codex and start a new task before first use.'
