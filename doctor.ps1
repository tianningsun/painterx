param(
    [switch]$RequireIllustratorOpen,
    [switch]$Json
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$codexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
$skillRoot = Join-Path $codexRoot 'skills\painterx'
$python = Join-Path $skillRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'py'; $prefix = @('-3') } else { $prefix = @() }
$arguments = @($prefix + @((Join-Path $repoRoot 'doctor.py'), '--skill-root', $skillRoot))
if ($RequireIllustratorOpen) { $arguments += '--require-illustrator-open' }
if ($Json) { $arguments += '--json' }
& $python @arguments
exit $LASTEXITCODE
