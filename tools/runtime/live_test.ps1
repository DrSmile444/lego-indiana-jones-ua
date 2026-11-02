# Live test in a disposable COPY of the Steam game (default: local/test-game).
# Copies the built package from dist/<VERSION>/files, optionally breaks the UAP,
# and starts the game hidden. Then attach tools/runtime/verify_runtime.py --pid.
param([switch]$StopOnly, [ValidateSet('Valid','Missing','Corrupt')][string]$PackMode = 'Valid', [switch]$WithoutLocalization,
      [string]$TestGame)
$ErrorActionPreference = 'Stop'
$repoDirectory = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $TestGame) { $TestGame = Join-Path $repoDirectory 'local/test-game' }
$testDirectory = [IO.Path]::GetFullPath($TestGame)
$version = (Get-Content -LiteralPath (Join-Path $repoDirectory 'VERSION') -TotalCount 1).Trim()
$packageDirectory = Join-Path $repoDirectory "dist/$version/files"
if (-not (Test-Path -LiteralPath (Join-Path $testDirectory 'LEGOIndy.exe'))) { throw "No game copy in $testDirectory" }
$testExecutable = Join-Path $testDirectory 'LEGOIndy.exe'
foreach ($process in @(Get-Process LEGOIndy -ErrorAction SilentlyContinue)) {
    if ($process.Path -eq $testExecutable) {
        Stop-Process -Id $process.Id
        $process.WaitForExit(10000) | Out-Null
    }
}
Start-Sleep -Seconds 2
if ($StopOnly) { return }
Copy-Item -LiteralPath (Join-Path $packageDirectory 'dinput8.dll') -Destination (Join-Path $testDirectory 'dinput8.dll') -Force
Copy-Item -LiteralPath (Join-Path $packageDirectory 'scripts') -Destination $testDirectory -Recurse -Force
if ($WithoutLocalization) {
    $pluginPath = Join-Path $testDirectory 'scripts/UKRAINIAN.asi'
    Move-Item -LiteralPath $pluginPath -Destination ($pluginPath + '.disabled') -Force
}
$packPath = Join-Path $testDirectory 'scripts/UKRAINIAN.uap'
if ($PackMode -eq 'Missing') {
    Move-Item -LiteralPath $packPath -Destination ($packPath + '.disabled') -Force
} elseif ($PackMode -eq 'Corrupt') {
    $bytes = [IO.File]::ReadAllBytes($packPath)
    $bytes[$bytes.Length - 1] = $bytes[$bytes.Length - 1] -bxor 1
    [IO.File]::WriteAllBytes($packPath, $bytes)
}
# The game itself resolves some original assets relative to its working folder.
# UAP still lives in scripts and is resolved relative to the ASI module.
Start-Process -FilePath $testExecutable -WorkingDirectory $testDirectory -WindowStyle Hidden -Environment @{SteamAppId='32330';SteamGameId='32330'}
