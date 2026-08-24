@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Visual Dashboard System — 打包交付

set ROOT=%~dp0
cd /d "%ROOT%"

REM 获取当前日期（用 PowerShell，兼容 Win11 无 wmic）
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd')"`) do set PKG_DATE=%%I
if "%PKG_DATE%"=="" set PKG_DATE=%date:~0,4%%date:~5,2%%date:~8,2%
set PKG_NAME=Visual-Dashboard-System_v%PKG_DATE%
set PKG_DIR=%ROOT%%PKG_NAME%

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║       打包交付 — %PKG_NAME%         ║
echo ╚══════════════════════════════════════════════════════╝
echo.

REM 清理旧打包
if exist "%PKG_DIR%" rmdir /s /q "%PKG_DIR%"
if exist "%PKG_NAME%.zip" del /q "%PKG_NAME%.zip"

REM 创建打包目录
mkdir "%PKG_DIR%"

echo [1/4] 复制核心代码...

REM 引擎层
xcopy /e /i /q /y "engine" "%PKG_DIR%\engine" >nul

REM 渲染层
xcopy /e /i /q /y "processors" "%PKG_DIR%\processors" >nul

REM 配置（含 配置编辑器.xlsx / cleaning_config.json / 客户销售归属.json / 展示规则）
xcopy /e /i /q /y "config" "%PKG_DIR%\config" >nul

REM 入口文件
copy /y "main.py" "%PKG_DIR%\main.py" >nul
copy /y "run_all.bat" "%PKG_DIR%\run_all.bat" >nul
copy /y "package.bat" "%PKG_DIR%\package.bat" >nul
copy /y "requirements.txt" "%PKG_DIR%\requirements.txt" >nul
copy /y "pytest.ini" "%PKG_DIR%\pytest.ini" >nul
copy /y "README.md" "%PKG_DIR%\README.md" >nul

REM 脚本工具（配置同步 + 看板验证）
if exist "scripts" xcopy /e /i /q /y "scripts" "%PKG_DIR%\scripts" >nul

REM 测试
if exist "tests" xcopy /e /i /q /y "tests" "%PKG_DIR%\tests" >nul

REM 文档
if exist "docs" xcopy /e /i /q /y "docs" "%PKG_DIR%\docs" >nul

echo [2/4] 复制系统数据 + 创建目录骨架...

REM ── 原始数据（完整复制，接收方可直接用）──
if exist "data\raw" xcopy /e /i /q /y "data\raw" "%PKG_DIR%\data\raw" >nul
if not exist "data\raw" mkdir "%PKG_DIR%\data\raw"

REM ── 映射（部门事业部 + 客户名单）──
if exist "data\mappings" xcopy /e /i /q /y "data\mappings" "%PKG_DIR%\data\mappings" >nul
if not exist "data\mappings" mkdir "%PKG_DIR%\data\mappings"

REM ── 手工维护指标表（完整复制，接收方可直接用）──
if exist "data\sheets\手动维护" xcopy /e /i /q /y "data\sheets\手动维护" "%PKG_DIR%\data\sheets\手动维护" >nul
if not exist "data\sheets\手动维护" mkdir "%PKG_DIR%\data\sheets\手动维护"

REM ── 系统数据清理（清洗引擎自动写入，仅建空骨架）──
mkdir "%PKG_DIR%\data\sheets\系统数据清理"
mkdir "%PKG_DIR%\data\sheets\系统数据清理\当年累计收入"
mkdir "%PKG_DIR%\data\sheets\系统数据清理\当年累计回款"
mkdir "%PKG_DIR%\data\sheets\系统数据清理\季度累计收入"
mkdir "%PKG_DIR%\data\sheets\系统数据清理\季度累计回款"
mkdir "%PKG_DIR%\data\sheets\系统数据清理\月收入"
mkdir "%PKG_DIR%\data\sheets\系统数据清理\月回款"
mkdir "%PKG_DIR%\data\sheets\系统数据清理\销售收入"
mkdir "%PKG_DIR%\data\sheets\系统数据清理\销售回款"
mkdir "%PKG_DIR%\data\sheets\系统数据清理\往年收入"
mkdir "%PKG_DIR%\data\sheets\系统数据清理\往年回款"

REM ── 输出目录（渲染后生成，仅建空骨架）──
mkdir "%PKG_DIR%\output"
mkdir "%PKG_DIR%\output\看板"
mkdir "%PKG_DIR%\output\数据"
mkdir "%PKG_DIR%\logs"

echo [3/4] 清理 __pycache__...
for /d /r "%PKG_DIR%" %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul

echo [4/4] 压缩 ZIP...
powershell -NoProfile -Command "Compress-Archive -Path '%PKG_DIR%' -DestinationPath '%PKG_NAME%.zip' -Force"

REM 计算大小
for %%A in ("%PKG_NAME%.zip") do set ZSIZE=%%~zA
set /a ZMB=!ZSIZE! / 1024 / 1024

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║  ✅ 打包完成！                                     ║
echo ╠══════════════════════════════════════════════════════╣
echo ║  📦 %PKG_NAME%.zip (!ZMB! MB)  ║
echo ╠══════════════════════════════════════════════════════╣
echo ║  包含（完整环境，可解压即用）:                      ║
echo ║  ▪ engine/      清洗引擎 (11 模块)                  ║
echo ║  ▪ processors/  渲染层 (20 模块)                    ║
echo ║  ▪ scripts/     工具脚本 (配置同步 + 看板验证)       ║
echo ║  ▪ config/      配置（含配置编辑器.xlsx）            ║
echo ║  ▪ tests/       测试用例 (15 文件)                  ║
echo ║  ▪ main.py      调度器入口                          ║
echo ║  ▪ run_all.bat  双击运行                            ║
echo ║  ▪ docs/        部署指南 + 设计文档                  ║
echo ║  ▪ data/raw/    原始数据（财务端/运营端/往年/客户名单）║
echo ║  ▪ data/mappings/ 映射（部门 + 客户名单）           ║
echo ║  ▪ data/sheets/手动维护/  6张指标表                 ║
echo ║  ▪ Chart.js 已本地化 (离线可用)                    ║
echo ╠══════════════════════════════════════════════════════╣
echo ║  不包含（运行后自动生成）:                          ║
echo ║  ▪ data/sheets/系统数据清理/  清洗中间产物           ║
echo ║  ▪ output/        看板 + 数据总表                   ║
echo ║  ▪ logs/          运行日志                          ║
echo ╚══════════════════════════════════════════════════════╝
echo.

REM 清理临时目录
if exist "%PKG_DIR%" rmdir /s /q "%PKG_DIR%"

pause
