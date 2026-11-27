param(
    [Parameter(Mandatory=$true)][string]$AdminHome,
    [Parameter(Mandatory=$true)][ValidateSet('board','backup','monitor')][string]$Job,
    [Parameter(Mandatory=$true)][ValidateSet('enable','disable','status')][string]$Mode
)
$ErrorActionPreference = 'Stop'
$cfg = Get-Content -LiteralPath (Join-Path $AdminHome 'admin.json') -Raw | ConvertFrom-Json
$name = $cfg.task_prefix + '-' + $Job
$existing = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
if ($Mode -eq 'status') {
    @{ registered = [bool]$existing; state = $(if ($existing) { [string]$existing.State } else { 'Absent' }) } | ConvertTo-Json -Compress
    exit 0
}
if ($Mode -eq 'disable') {
    if ($existing) {
        for ($n=0; $n -lt 20 -and (Get-ScheduledTask -TaskName $name).State -eq 'Running'; $n++) { Start-Sleep -Milliseconds 250 }
        if ((Get-ScheduledTask -TaskName $name).State -eq 'Running') { throw 'Scheduled job is active; wait before disabling it.' }
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
    }
    @{registered=$false} | ConvertTo-Json -Compress
    exit 0
}
if ($existing) { @{registered=$true} | ConvertTo-Json -Compress; exit 0 }
$pythonw = Join-Path (Split-Path $cfg.python) 'pythonw.exe'
$python = $(if (Test-Path -LiteralPath $pythonw) { $pythonw } else { $cfg.python })
$command = $(if ($Job -eq 'board') { 'start --wait' } else { $Job })
$arguments = '-B "' + (Join-Path $AdminHome 'helpers\win_admin.py') + '" --home "' + $AdminHome + '" ' + $command
$action = New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $AdminHome
$principal = New-ScheduledTaskPrincipal -UserId $cfg.owner_sid -LogonType Interactive -RunLevel Limited
if ($Job -eq 'board') {
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $cfg.owner_sid
    $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
} elseif ($Job -eq 'backup') {
    $trigger = New-ScheduledTaskTrigger -Daily -At '03:00'
    $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
} else {
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Minutes 5)
    $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
}
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Optional per-user RCP/M administration' | Out-Null
@{registered=$true} | ConvertTo-Json -Compress
