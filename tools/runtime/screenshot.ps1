<#
.SYNOPSIS
  Captures the full screen (or a specific window by title substring) to a PNG.
  Uses .NET GDI+ directly — no external tools needed.

.EXAMPLE
  .\screenshot.ps1 -OutPath "C:\temp\shot.png"
  .\screenshot.ps1 -OutPath "C:\temp\shot.png" -WindowTitleContains "Indiana"
#>
param(
    [Parameter(Mandatory=$true)][string]$OutPath,
    [string]$WindowTitleContains = ""
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
}
"@

if ($WindowTitleContains -ne "") {
    $proc = Get-Process | Where-Object { $_.MainWindowTitle -like "*$WindowTitleContains*" } | Select-Object -First 1
    if (-not $proc) {
        Write-Error "No window found with title containing '$WindowTitleContains'. Open windows: $((Get-Process | Where-Object {$_.MainWindowTitle -ne ''}).MainWindowTitle -join ', ')"
        exit 1
    }
    $hwnd = $proc.MainWindowHandle
    [Win32]::SetForegroundWindow($hwnd) | Out-Null
    Start-Sleep -Milliseconds 300
    $rect = New-Object Win32+RECT
    [Win32]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
    $x = $rect.Left
    $y = $rect.Top
    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top
} else {
    $bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
    $x = $bounds.X
    $y = $bounds.Y
    $width = $bounds.Width
    $height = $bounds.Height
}

if ($width -le 0 -or $height -le 0) {
    Write-Error "Invalid capture size ${width}x${height} - window may be minimized."
    exit 1
}

$bmp = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bmp)
$graphics.CopyFromScreen($x, $y, 0, 0, (New-Object System.Drawing.Size $width, $height))
$bmp.Save($OutPath, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bmp.Dispose()
Write-Output "Saved screenshot: $OutPath ($width x $height)"
