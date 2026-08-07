@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Visual Dashboard System — 打包交付

set ROOT=%~dp0
cd /d "%ROOT%"

REM 获取当前日期
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set DT=%%I
set PKG_DATE=%DT:~0,8%
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

REM 配置
xcopy /e /i /q /y "config" "%PKG_DIR%\config" >nul

REM 入口文件
copy /y "main.py" "%PKG_DIR%\main.py" >nul
copy /y "run_all.bat" "%PKG_DIR%\run_all.bat" >nul
copy /y "requirements.txt" "%PKG_DIR%\requirements.txt" >nul
copy /y "pytest.ini" "%PKG_DIR%\pytest.ini" >nul
copy /y "README.md" "%PKG_DIR%\README.md" >nul

REM 测试
if exist "tests" xcopy /e /i /q /y "tests" "%PKG_DIR%\tests" >nul

REM 文档
if exist "docs" xcopy /e /i /q /y "docs" "%PKG_DIR%\docs" >nul

echo [2/4] 创建目录骨架...

REM data 骨架（数据本身不打包，只保留目录结构）
mkdir "%PKG_DIR%\data"
mkdir "%PKG_DIR%\data\raw"
mkdir "%PKG_DIR%\data\raw\财务端数据"
mkdir "%PKG_DIR%\data\raw\运营端数据"
mkdir "%PKG_DIR%\data\raw\往年收入数据"
mkdir "%PKG_DIR%\data\raw\往年回款数据"
mkdir "%PKG_DIR%\data\raw\客户名单"

REM mappings 只打包部门映射（不含客户名单敏感数据）
mkdir "%PKG_DIR%\data\mappings"
mkdir "%PKG_DIR%\data\mappings\部门事业部映射"
if exist "data\mappings\部门事业部映射\部门事业部映射.json" (
    copy /y "data\mappings\部门事业部映射\部门事业部映射.json" "%PKG_DIR%\data\mappings\部门事业部映射\" >nul
)

REM 手动维护指标表目录
mkdir "%PKG_DIR%\data\sheets"
mkdir "%PKG_DIR%\data\sheets\手动维护"
mkdir "%PKG_DIR%\data\sheets\手动维护\年度收入总指标"
mkdir "%PKG_DIR%\data\sheets\手动维护\年度回款总指标"
mkdir "%PKG_DIR%\data\sheets\手动维护\季度收入指标"
mkdir "%PKG_DIR%\data\sheets\手动维护\季度回款指标"
mkdir "%PKG_DIR%\data\sheets\手动维护\月度收入指标"
mkdir "%PKG_DIR%\data\sheets\手动维护\月度回款指标"

REM 输出目录
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
echo ║  包含:                                              ║
echo ║  ▪ engine/      清洗引擎 (16 模块)                  ║
echo ║  ▪ processors/  渲染层 (21 模块)                    ║
echo ║  ▪ config/      配置文件                            ║
echo ║  ▪ tests/       测试用例                            ║
echo ║  ▪ main.py      调度器入口                          ║
echo ║  ▪ run_all.bat  双击运行                            ║
echo ╠══════════════════════════════════════════════════════╣
echo ║  不包含（需自行准备）:                              ║
echo ║  ▪ data/raw/    原始 Excel（财务端/运营端/往年/客户名单）║
echo ║  ▪ data/sheets/ 手工维护指标表                      ║
echo ║  ▪ data/mappings/客户名单/  JSON（首次运行自动生成）  ║
echo ╚══════════════════════════════════════════════════════╝
echo.

REM 清理临时目录
if exist "%PKG_DIR%" rmdir /s /q "%PKG_DIR%"

pause
