param(
    [ValidateSet('Probe', 'IsRunning', 'EnsureReady', 'Run')]
    [string]$Mode = 'Probe',
    [string]$BootstrapPath = '',
    [ValidateRange(25, 99)]
    [int]$MinimumIllustratorMajor = 25
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)

function Test-IllustratorRunning {
    $process = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match 'Illustrator' } | Select-Object -First 1
    return $null -ne $process
}

function Get-RegisteredVersion {
    $progIds = @('Illustrator.Application')
    for ($major = 40; $major -ge 25; $major--) { $progIds += "Illustrator.Application.$major" }
    foreach ($progId in $progIds) {
        $key = "Registry::HKEY_CLASSES_ROOT\$progId\CLSID"
        if (Test-Path -LiteralPath $key) {
            if ($progId -match '\.(\d+)$') { return $Matches[1] }
            return 'generic'
        }
    }
    return $null
}

function Connect-Illustrator {
    $progIds = @('Illustrator.Application')
    for ($major = 40; $major -ge $MinimumIllustratorMajor; $major--) { $progIds += "Illustrator.Application.$major" }
    $lastError = $null
    foreach ($progId in $progIds) {
        try {
            $application = New-Object -ComObject $progId
            $majorVersion = [int](([string]$application.Version -split '\.')[0])
            if ($majorVersion -lt $MinimumIllustratorMajor) {
                [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($application)
                continue
            }
            return $application
        } catch { $lastError = $_.Exception.Message }
    }
    throw "ILLUSTRATOR_NOT_INSTALLED|No compatible Illustrator COM registration was found. $lastError"
}

if ($Mode -eq 'IsRunning') {
    Write-Output ((Test-IllustratorRunning).ToString().ToLowerInvariant())
    exit 0
}
if ($Mode -eq 'Probe') {
    $registered = Get-RegisteredVersion
    if ($null -eq $registered) { Write-Error 'ILLUSTRATOR_NOT_INSTALLED'; exit 2 }
    Write-Output "REGISTERED|version=$registered"
    exit 0
}

$wasRunning = Test-IllustratorRunning
$illustrator = $null
try {
    $illustrator = Connect-Illustrator
    $created = $false
    if ($illustrator.Documents.Count -lt 1) {
        [void]$illustrator.Documents.Add()
        $created = $true
    }
    if ($Mode -eq 'EnsureReady') {
        Write-Output "READY|launched=$(((-not $wasRunning).ToString().ToLowerInvariant()))|created=$($created.ToString().ToLowerInvariant())|documents=$($illustrator.Documents.Count)|version=$($illustrator.Version)"
        exit 0
    }
    if ([string]::IsNullOrWhiteSpace($BootstrapPath) -or -not (Test-Path -LiteralPath $BootstrapPath -PathType Leaf)) {
        throw 'BOOTSTRAP_REQUIRED|Run mode needs a valid BootstrapPath.'
    }
    $javascript = [IO.File]::ReadAllText([IO.Path]::GetFullPath($BootstrapPath), [Text.Encoding]::UTF8)
    Write-Output ([string]$illustrator.DoJavaScript($javascript))
} finally {
    if ($null -ne $illustrator) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($illustrator) }
}
