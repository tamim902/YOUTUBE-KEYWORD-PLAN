<#
.SYNOPSIS
    Sets up an automated daily backup task in Windows Task Scheduler for YouTube Keyword Studio.

.DESCRIPTION
    This script registers a Windows Scheduled Task that executes:
        python -m src.storage.cli_backup
    every day at the specified time (default: 03:00 AM).
    
    The task creates a consistent SQLite backup, packages source files,
    validates the manifest checksums, and uploads to Google Drive if connected.

.NOTES
    Prerequisite: Windows PC must be powered on or awake for scheduled execution.
    To view registered tasks: Run 'taskschd.msc' in Windows Run.
    To remove task: schtasks /delete /tn "YouTubeKeywordStudioDailyBackup" /f
#>

param (
    [string]$TaskName = "YouTubeKeywordStudioDailyBackup",
    [string]$ScheduleTime = "03:00",
    [switch]$Uninstall = $false
)

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if ($Uninstall) {
    Write-Host "[INFO] Removing Windows Scheduled Task '$TaskName'..." -ForegroundColor Yellow
    schtasks.exe /delete /tn $TaskName /f
    Write-Host "[SUCCESS] Task '$TaskName' removed successfully." -ForegroundColor Green
    exit 0
}

# Determine Python interpreter
if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
} else {
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PythonExe) {
        Write-Error "Python executable not found. Please activate your virtual environment or install Python."
        exit 1
    }
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  YouTube Keyword Studio - Windows Backup Task Setup" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Project Directory: $ProjectRoot"
Write-Host "Python Executable: $PythonExe"
Write-Host "Scheduled Daily:   $ScheduleTime"
Write-Host "Task Name:         $TaskName"
Write-Host ""

$ActionArgument = "-m src.storage.cli_backup --note `"Windows Task Scheduler Daily`""

# Register via schtasks.exe (works cleanly across all Windows versions without requiring elevated PowerShell cmdlets)
$SchtasksCmd = "schtasks.exe /create /tn `"$TaskName`" /tr `"\`"$PythonExe\`" $ActionArgument`" /sc daily /st $ScheduleTime /f"

Write-Host "[INFO] Registering Windows Scheduled Task..." -ForegroundColor Yellow
Invoke-Expression $SchtasksCmd

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] Daily automated backup task registered successfully!" -ForegroundColor Green
    Write-Host "• The backup will run daily at $ScheduleTime whenever your PC is on."
    Write-Host "• To test the task immediately:" -ForegroundColor Cyan
    Write-Host "    schtasks /run /tn `"$TaskName`""
    Write-Host "• To inspect in Windows GUI:" -ForegroundColor Cyan
    Write-Host "    taskschd.msc"
    Write-Host "• To uninstall:" -ForegroundColor Cyan
    Write-Host "    powershell -ExecutionPolicy Bypass -File scripts\setup_windows_backup_task.ps1 -Uninstall"
    Write-Host "==========================================================" -ForegroundColor Cyan
} else {
    Write-Error "Failed to register scheduled task. Please run PowerShell as Administrator."
}
