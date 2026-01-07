' ============================================
' Templonix Lite Silent Launcher
' ============================================
' This VBScript starts the MCP server silently in the background without showing a console window. Perfect for Task Scheduler.
'
' USAGE:
'   - Add to Task Scheduler to run at login
'   - The server runs invisibly in the background
'
' TO STOP THE SERVER:
'   - Open Task Manager > Details tab
'   - Find and end the "python.exe" process running app.py
' ============================================

' CONFIGURATION - Update this path as needed
Dim ProjectRoot
ProjectRoot = "C:\Development\Templonix_Lite"

' Create shell object
Set WshShell = CreateObject("WScript.Shell")

' Build the command
Dim Command
Command = "cmd /c cd /d """ & ProjectRoot & """ && .venv\Scripts\activate.bat && python templonix_mcp\app.py"

' Run hidden (0 = hidden, False = don't wait)
WshShell.Run Command, 0, False

Set WshShell = Nothing
