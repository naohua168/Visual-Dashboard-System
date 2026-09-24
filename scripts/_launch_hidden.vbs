' Hidden launcher for dashboard_launcher.ps1 (WPF GUI)
' 注意:WPF 需要 STA 线程,必须加 -STA
' Author: naohua168 <bai_bai168@qq.com>
Set sh = CreateObject("WScript.Shell")
base = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
cmd = "powershell -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File """ & base & "dashboard_launcher.ps1"""
sh.Run cmd, 0, False
