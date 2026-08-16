$Action = New-ScheduledTaskAction -Execute "C:\Users\Mughees Siddiqui\Desktop\DEADMAN.SYS\backend\start_scheduler.bat"
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -WakeToRun
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U
Register-ScheduledTask -TaskName "DEADMAN_SYS_Scheduler" -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force
Start-ScheduledTask -TaskName "DEADMAN_SYS_Scheduler"
Write-Host "Scheduled task DEADMAN_SYS_Scheduler registered and started."
