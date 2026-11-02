# Build UKRAINIAN.asi (x86) from native/asi with the MSVC x86 toolset.
#   -SmokeTest    load the ASI on an unsupported host, run UTF-8 name regressions
#   -TextureTest  build texture_test.exe (byte-compares the C++ texture patcher; needs game/)
#   -Legacy       old dinput8.dll proxy mode (research builds before 0.1.8)
#   -FontUpscaleExperiment  legacy proxy with the Font 1 x2 experiment (see experiments/font1-x2)
# Output: build/native/<mode>/  — never committed.
param([string]$Python = 'python', [switch]$SmokeTest, [switch]$TextureTest, [switch]$Legacy,
      [switch]$FontUpscaleExperiment)
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Source = Join-Path $PSScriptRoot 'asi'
$Version = (Get-Content -LiteralPath (Join-Path $RepoRoot 'VERSION') -TotalCount 1).Trim()
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Invalid VERSION: $Version" }
$Mode = 'asi'
if ($Legacy) { $Mode = 'legacy-proxy' }
if ($FontUpscaleExperiment) { $Mode = 'font-upscale-experiment' }
$BuildDir = Join-Path $RepoRoot "build/native/$Mode/obj"
$DistDir = Join-Path $RepoRoot "build/native/$Mode"
$OutputName = 'UKRAINIAN.asi'
$Definition = Join-Path $Source 'ukrainian.def'
if ($Mode -ne 'asi') { $OutputName = 'dinput8.dll'; $Definition = Join-Path $Source 'dinput8.def' }
New-Item -ItemType Directory -Force -Path $BuildDir, $DistDir | Out-Null

& $Python (Join-Path $Source 'generate_strings.py') (Join-Path $BuildDir 'pc_strings.h')
if ($LASTEXITCODE -ne 0) { throw 'String generation failed' }

$VsWhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$VsRoot = & $VsWhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $VsRoot) { throw 'Visual Studio C++ x86 build tools are required (see docs/setup.md)' }
$Toolset = Get-ChildItem (Join-Path $VsRoot 'VC\Tools\MSVC') -Directory | Sort-Object Name -Descending | Select-Object -First 1
$SdkRoot = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10'
$Sdk = Get-ChildItem (Join-Path $SdkRoot 'Include') -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'um\Windows.h') } | Sort-Object Name -Descending | Select-Object -First 1
if (-not $Sdk) { throw 'Windows 10/11 SDK is required (see docs/setup.md)' }
$CompilerDir = Join-Path $Toolset.FullName 'bin\Hostx64\x86'
$Includes = @("/I$BuildDir", "/I$Source", "/I$(Join-Path $Toolset.FullName 'include')",
    "/I$(Join-Path $Sdk.FullName 'ucrt')", "/I$(Join-Path $Sdk.FullName 'shared')", "/I$(Join-Path $Sdk.FullName 'um')")
$LibPaths = @("/LIBPATH:$(Join-Path $Toolset.FullName 'lib\x86')",
    "/LIBPATH:$(Join-Path $SdkRoot "Lib\$($Sdk.Name)\ucrt\x86")",
    "/LIBPATH:$(Join-Path $SdkRoot "Lib\$($Sdk.Name)\um\x86")")
$Defines = @()
Set-Content -LiteralPath (Join-Path $BuildDir 'ua_version.h') -Value "#define UA_VERSION `"$Version`"" -Encoding ascii
if ($Mode -eq 'asi') { $Defines += @('/DUAP_EXPERIMENT', '/DUAP_ASI') }
if ($FontUpscaleExperiment) { $Defines += '/DFONT_UPSCALE_EXPERIMENT' }
$Common = @('/nologo', '/MT', '/O2', '/W4', '/WX', '/utf-8', '/Brepro', '/D_WIN32_WINNT=0x0601') + $Defines + $Includes

function Invoke-Cl([string[]]$Arguments, [string]$What) {
    & (Join-Path $CompilerDir 'cl.exe') @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$What failed" }
}

$PreviousPath = $env:PATH
try {
    $env:PATH = "$CompilerDir;$PreviousPath"
    $Output = Join-Path $DistDir $OutputName
    Invoke-Cl (@('/LD') + $Common + @("/Fo$(Join-Path $BuildDir 'proxy.obj')", "/Fe$Output",
        (Join-Path $Source 'proxy.cpp'), '/link', '/MACHINE:X86', '/DYNAMICBASE', '/NXCOMPAT', '/Brepro',
        "/DEF:$Definition", "/IMPLIB:$(Join-Path $BuildDir 'plugin.lib')") + $LibPaths +
        @('kernel32.lib', 'bcrypt.lib')) 'Plugin compilation'

    if ($Mode -eq 'asi') {
        # A second ASI proves two plugins coexist under the loader (used by tools/live-tests).
        Invoke-Cl (@('/LD') + $Common + @("/Fo$(Join-Path $BuildDir 'coexistence_probe.obj')",
            "/Fe$(Join-Path $BuildDir 'ZZ_UAP_COEXISTENCE.asi')", (Join-Path $Source 'coexistence_probe.cpp'),
            '/link', '/MACHINE:X86', "/DEF:$Definition", "/IMPLIB:$(Join-Path $BuildDir 'probe.lib')") + $LibPaths +
            @('kernel32.lib', 'bcrypt.lib')) 'Coexistence probe compilation'
    }
    if ($TextureTest) {
        Invoke-Cl ($Common + @("/Fo$(Join-Path $BuildDir 'texture_test.obj')", "/Fe$(Join-Path $BuildDir 'texture_test.exe')",
            (Join-Path $Source 'texture_test.cpp'), '/link', '/MACHINE:X86') + $LibPaths + @('kernel32.lib', 'bcrypt.lib')) 'Texture test compilation'
        & $Python -m ua test-textures --exe (Join-Path $BuildDir 'texture_test.exe')
        if ($LASTEXITCODE -ne 0) { throw 'Texture patcher byte comparison failed' }
    }
    if ($SmokeTest) {
        if ($Mode -eq 'asi') {
            Invoke-Cl ($Common + @("/Fo$(Join-Path $BuildDir 'custom_name_test.obj')", "/Fe$(Join-Path $BuildDir 'custom_name_test.exe')",
                (Join-Path $Source 'custom_name_test.cpp'), '/link', '/MACHINE:X86') + $LibPaths + @('kernel32.lib', 'bcrypt.lib')) 'Custom-name test compilation'
            & (Join-Path $BuildDir 'custom_name_test.exe')
            if ($LASTEXITCODE -ne 0) { throw 'Custom-name UTF-8 regression failed' }
            $SmokeSource = Join-Path $Source 'smoke_test.cpp'
        } else {
            $SmokeSource = Join-Path $Source 'proxy_smoke_test.cpp'
        }
        Invoke-Cl (@('/nologo', '/MT', '/W4', '/WX', '/utf-8') + $Includes + @("/Fo$(Join-Path $BuildDir 'smoke_test.obj')",
            "/Fe$(Join-Path $BuildDir 'smoke_test.exe')", $SmokeSource, '/link', '/MACHINE:X86') + $LibPaths +
            @('kernel32.lib', 'dxguid.lib')) 'Smoke test compilation'
        & (Join-Path $BuildDir 'smoke_test.exe') $Output
        if ($LASTEXITCODE -ne 0) { throw 'Plugin smoke test failed' }
        $TestLog = Join-Path $DistDir 'legoindy-ua-pc.log'
        if (-not ((Get-Content -LiteralPath $TestLog -Tail 1) -like 'SKIP: unsupported executable SHA-256*')) {
            throw 'Unsupported-host guard did not report the expected result'
        }
        Remove-Item -LiteralPath $TestLog
    }
} finally { $env:PATH = $PreviousPath }
Get-FileHash -LiteralPath $Output -Algorithm SHA256 | Format-List Path, Hash
