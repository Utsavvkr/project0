$ErrorActionPreference = 'Stop'

$flutterDir = "C:\flutter"
$zipUrl = "https://storage.googleapis.com/flutter_infra_release/releases/stable/windows/flutter_windows_3.24.5-stable.zip"
$zipPath = "$env:TEMP\flutter_windows.zip"

if (-not (Test-Path "$flutterDir\bin\flutter.bat")) {
    Write-Host "Downloading Flutter SDK (3.24.5 stable) using curl..."
    curl.exe -L --retry 5 --retry-delay 5 $zipUrl -o $zipPath
    Write-Host "Extracting Flutter SDK to C:\..."
    Expand-Archive -Path $zipPath -DestinationPath "C:\" -Force
    Remove-Item -Path $zipPath -Force
} else {
    Write-Host "Flutter SDK already exists at C:\flutter"
}

# Add to current session path
$env:Path = "C:\flutter\bin;" + $env:Path

# Add to User Environment Path permanently
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*C:\flutter\bin*") {
    [Environment]::SetEnvironmentVariable("Path", "C:\flutter\bin;$userPath", "User")
    Write-Host "Added C:\flutter\bin to user PATH permanently."
}

Write-Host "Verifying Flutter installation..."
flutter --version
