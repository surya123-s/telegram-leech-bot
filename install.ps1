<#
install.ps1
Run as Administrator in PowerShell (elevated).

Usage:
  .\install.ps1 -InstallDir "C:\telegram-leech-bot"

This script installs Chocolatey (if needed), python, ffmpeg, nssm, openssh,
then installs pip packages and yt-dlp.
#>

param(
    [string]$InstallDir = "C:\telegram-leech-bot"
)

function Ensure-Chocolatey {
    if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Host "Chocolatey not found. Installing Chocolatey..."
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    } else {
        Write-Host "Chocolatey found."
    }
}

function Install-Packages {
    Write-Host "Installing packages with choco..."
    choco install -y python ffmpeg nssm openssh
}

function Ensure-PipPackages {
    Write-Host "Installing Python packages..."
    # ensure pip in path
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) { throw "python not available in PATH after install. Check installation." }
    & python -m pip install --upgrade pip
    & python -m pip install pyrogram tgcrypto yt-dlp
}

function Prepare-InstallDir {
    if (!(Test-Path $InstallDir)) { New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null }
    Write-Host "Install directory: $InstallDir"
}

# main
Write-Host "Running install script..."
Ensure-Chocolatey
Install-Packages
Ensure-PipPackages
Prepare-InstallDir
Write-Host "Install complete. Place your bot files in $InstallDir and run register_service.ps1 to create the service."
