@echo off
rem ============================================
rem  Visual Dashboard System — 图形化运行入口
rem  双击本文件弹出运行控制台窗口（免安装）
rem  Author: naohua168 <bai_bai168@qq.com>
rem
rem  启动链（2026-09-24 抗误报改造）：
rem    ① 找到 pythonw.exe → scripts\launcher.pyw（无控制台窗口）
rem    ② 没找到 Python → 直接用 PowerShell 启动图形控制台
rem  说明：旧方案用 VBS 隐藏窗口 + ExecutionPolicy Bypass，
rem        该组合极易被 360/火绒等安全软件误判为木马，已停用。
rem ============================================
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set PYTHONW=

rem 1) 内置 Python 运行时（交付包自带，免安装）
if exist "%~dp0runtime\python\pythonw.exe" set PYTHONW=%~dp0runtime\python\pythonw.exe
if defined PYTHONW goto :launch_python

rem 2) 本机 Conda 环境
if exist "C:\Users\%USERNAME%\.conda\envs\visual-dashboard-system\pythonw.exe" set PYTHONW=C:\Users\%USERNAME%\.conda\envs\visual-dashboard-system\pythonw.exe
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
start "" "%PYTHONW%" "%~dp0scripts\launcher.pyw"
exit /b
