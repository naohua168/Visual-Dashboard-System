@echo off
rem ============================================
rem  Visual Dashboard System — 图形化运行入口
rem  双击本文件弹出运行控制台窗口（免安装）
rem  Author: naohua168 <bai_bai168@qq.com>
rem ============================================
cd /d "%~dp0"
start "" wscript.exe "%~dp0scripts\_launch_hidden.vbs"
exit /b
