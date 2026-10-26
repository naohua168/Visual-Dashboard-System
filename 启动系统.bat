@echo off
rem ============================================
rem  Visual Dashboard System — 图形化运行入口
rem  双击本文件弹出运行控制台窗口（免安装）
rem  Author: naohua168 <bai_bai168@qq.com>
rem
rem  启动链（2026-10-19 改为 Python 原生界面）：
rem    ① 找到 pythonw.exe → bin\app.py（tkinter 图形控制台，无控制台窗口）
rem    ② 没找到 Python → 回退 PowerShell 启动旧版图形控制台（scripts\dashboard_launcher.ps1）
rem  说明：旧方案用 VBS 隐藏窗口 + ExecutionPolicy Bypass，
rem        该组合极易被 360/火绒等安全软件误判为木马，已停用。
rem ============================================
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set PYTHONW=

rem 0) 用户自定义解释器目录（config\python_path.txt）—— 设了就优先用，没设则往下自动探测
set "PY_DIR="
if exist "%~dp0config\python_path.txt" (
    for /f "usebackq eol=# tokens=*" %%L in ("%~dp0config\python_path.txt") do (
        set "PY_DIR=%%L"
        goto :got_pydir
    )
)
:got_pydir
if defined PY_DIR (
    if exist "%PY_DIR%\pythonw.exe" set "PYTHONW=%PY_DIR%\pythonw.exe"
    if not defined PYTHONW echo [警告] config\python_path.txt 里的路径无效: %PY_DIR%（继续自动探测）
)
if defined PYTHONW goto :launch_python

rem 1) 内置 Python 运行时（交付包自带，免安装）
if exist "%~dp0runtime\python\pythonw.exe" set "PYTHONW=%~dp0runtime\python\pythonw.exe"
if defined PYTHONW goto :launch_python

rem 2) 本机 Conda 环境（系统内置变量 %USERPROFILE%，不写死盘符/目录）
if exist "%USERPROFILE%\.conda\envs\visual-dashboard-system\pythonw.exe" set "PYTHONW=%USERPROFILE%\.conda\envs\visual-dashboard-system\pythonw.exe"
if defined PYTHONW goto :launch_python

rem 3) 系统 PATH 中的 pythonw
for %%p in (pythonw.exe) do (
    where %%p >nul 2>&1
    if !errorlevel!==0 set PYTHONW=%%p
)
if defined PYTHONW goto :launch_python

rem 4) 回退：PowerShell 直接启动图形控制台（会短暂出现控制台窗口，之后自动消失）
start "" powershell.exe -NoProfile -STA -ExecutionPolicy RemoteSigned -File "%~dp0scripts\dashboard_launcher.ps1"
exit /b

:launch_python
rem 内置运行时(runtime)不含 tkinter → 先检测，不可用则回退传统 WPF 控制台
"%PYTHONW%" -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    start "" powershell.exe -NoProfile -STA -ExecutionPolicy RemoteSigned -File "%~dp0scripts\dashboard_launcher.ps1"
) else (
    start "" "%PYTHONW%" "%~dp0bin\app.py"
)
exit /b
