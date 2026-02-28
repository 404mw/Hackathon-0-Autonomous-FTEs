' start-hidden.vbs
' Starts PM2 with all vault watchers.
' Processes use pythonw.exe so no console windows appear regardless.
'
' Usage:
'   Double-click to start (DRY_RUN=false, production mode)
'   Or import Scripts\task-scheduler\pm2_startup.xml into Task Scheduler
'   for automatic start at logon.
'
' To stop all processes afterwards:
'   Open any terminal and run: pm2 stop all

Option Explicit

Dim shell, vault, cmd
vault = "G:\Hackathons\GIAIC_Hackathons\AI_Employee_Vault"

Set shell = CreateObject("WScript.Shell")

' windowStyle 0 = hidden window for the cmd.exe launcher itself
cmd = "cmd /c pm2 start """ & vault & "\Scripts\pm2.config.js"" --env production"
shell.Run cmd, 0, False

Set shell = Nothing
