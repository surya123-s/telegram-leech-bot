<#
register_service.ps1
Creates / updates the TelegramLeechBot Windows service using NSSM.

Usage example (Admin):
.\register_service.ps1 -InstallDir "C:\telegram-leech-bot" -BotToken "123:ABC" -AllowedUsers "123456,789012"
#>

param(
    [string]$InstallDir = "C:\telegram-leech-bot",
    [string]$ServiceName = "TelegramLeechBot",
    [string]$BotToken = $env:BOT_TOKEN,
    [string]$AllowedUsers = $env:ALLOWED_USERS,
    [int]$MaxConcurrentDownloads = 2,
    [long]$MaxFileSizeBytes = 2147483648
)

if (-not (Test-Path $InstallDir)) {
    throw "InstallDir does not exist: $InstallDir"
}

$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssm) {
    # try default choco path
    $nssm = "C:\ProgramData\chocolatey\lib\nssm\tools\nssm.exe"
    if (-not (Test-Path $nssm)) {
        throw "nssm not found. Ensure nssm is installed and in PATH."
    }
}

$pythonExe = (Get-Command python).Source
$botScript = Join-Path $InstallDir "bot.py"

if (-not (Test-Path $botScript)) {
    throw "bot.py not found in $InstallDir"
}

# install or update service
& $nssm install $ServiceName $pythonExe $botScript

# set startup dir
& $nssm set $ServiceName AppDirectory $InstallDir

# set environment variables for the service
if ($BotToken) { & $nssm set $ServiceName AppEnvironmentExtra "BOT_TOKEN=$BotToken" }
if ($AllowedUsers) { & $nssm set $ServiceName AppEnvironmentExtra $("ALLOWED_USERS=" + $AllowedUsers) }
& $nssm set $ServiceName AppEnvironmentExtra $("MAX_CONCURRENT_DOWNLOADS=" + $MaxConcurrentDownloads)
& $nssm set $ServiceName AppEnvironmentExtra $("MAX_FILE_SIZE_BYTES=" + $MaxFileSizeBytes)

# set stdout/stderr file
$logPath = Join-Path $InstallDir "bot.log"
& $nssm set $ServiceName AppStdout $logPath
& $nssm set $ServiceName AppStderr $logPath
& $nssm set $ServiceName AppRotateFiles 1

# start service
& $nssm start $ServiceName

Write-Host "Service $ServiceName installed/updated and started."
