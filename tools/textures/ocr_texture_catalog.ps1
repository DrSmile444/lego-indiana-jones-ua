param([string]$CatalogPath = (Join-Path $PSScriptRoot '..\graphics\texture-catalog'), [int]$Scale = 1, [string]$IdsFile = '')
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Storage.FileAccessMode, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime]
$asyncMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
} | Select-Object -First 1
function Await-WinRT($operation, [Type]$resultType) {
    $task = $asyncMethod.MakeGenericMethod($resultType).Invoke($null, @($operation))
    $task.Wait()
    $task.Result
}
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('en-US'))
if (-not $engine) { throw 'English Windows OCR is unavailable' }
$CatalogPath = (Resolve-Path -LiteralPath $CatalogPath).Path
$inventory = Get-Content -LiteralPath (Join-Path $CatalogPath 'inventory.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($IdsFile) {
    $wantedIds = @(Get-Content -LiteralPath $IdsFile)
    $inventory.textures = @($inventory.textures | Where-Object { $_.id -in $wantedIds })
}
$results = [System.Collections.Generic.List[object]]::new()
$index = 0
foreach ($texture in $inventory.textures) {
    $index++
    $path = Join-Path $CatalogPath ('all\' + $texture.id + '.png')
    $stream = $null
    $bitmap = $null
    try {
        $file = Await-WinRT ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile])
        $stream = Await-WinRT ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $decoder = Await-WinRT ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        if ($Scale -gt 1) {
            $null = [Windows.Graphics.Imaging.BitmapTransform, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
            $transform = [Windows.Graphics.Imaging.BitmapTransform]::new()
            $factor = [Math]::Min($Scale, 2048.0 / [Math]::Max($decoder.PixelWidth, $decoder.PixelHeight))
            $transform.ScaledWidth = [uint32]([Math]::Max(1, $decoder.PixelWidth * $factor))
            $transform.ScaledHeight = [uint32]([Math]::Max(1, $decoder.PixelHeight * $factor))
            $bitmap = Await-WinRT ($decoder.GetSoftwareBitmapAsync(
                [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8,
                [Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied, $transform,
                [Windows.Graphics.Imaging.ExifOrientationMode]::IgnoreExifOrientation,
                [Windows.Graphics.Imaging.ColorManagementMode]::DoNotColorManage
            )) ([Windows.Graphics.Imaging.SoftwareBitmap])
        } else {
            $bitmap = Await-WinRT ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        }
        $result = Await-WinRT ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        $results.Add([pscustomobject]@{ id=$texture.id; text=$result.Text; lines=@($result.Lines | ForEach-Object {$_.Text}) })
    } catch {
        $results.Add([pscustomobject]@{ id=$texture.id; text=''; error=$_.Exception.Message })
    } finally {
        if ($bitmap) { $bitmap.Dispose() }
        if ($stream) { $stream.Dispose() }
    }
    if ($index % 50 -eq 0) { Write-Output "OCR $index / $($inventory.textures.Count)" }
}
$outputName = if ($Scale -gt 1) { 'ocr-enlarged.json' } else { 'ocr.json' }
$results | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $CatalogPath $outputName) -Encoding UTF8
Write-Output "OCR finished: $($results.Count) textures"
