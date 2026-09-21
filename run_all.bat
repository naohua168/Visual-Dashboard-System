@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Visual Dashboard System — 一键运行

cd /d "%~dp0"

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║     Visual Dashboard System — 自动流水线           ║
echo ║     %date% %time%                    ║
echo ╚══════════════════════════════════════════════════════╝
echo.

REM ============================================
REM 自动检测 Python 解释器
REM ============================================
set PYTHON=

REM 0) 优先使用内置运行时（解压即用，无需安装 Python）
if exist "%~dp0runtime\python\python.exe" (
    set PYTHON=%~dp0runtime\python\python.exe
    echo [系统] 使用内置 Python 运行时（免安装）
    goto :found_python
)

REM 1) 尝试 Conda 环境
if exist "C:\Users\%USERNAME%\.conda\envs\visual-dashboard-system\python.exe" (
    set PYTHON=C:\Users\%USERNAME%\.conda\envs\visual-dashboard-system\python.exe
    echo [系统] 使用 Conda 环境: visual-dashboard-system
    goto :found_python
)

REM 2) 尝试系统 Python
for %%p in (python python3) do (
    where %%p >nul 2>&1
    if !errorlevel!==0 (
        set PYTHON=%%p
        echo [系统] 使用系统 Python: %%p
        goto :found_python
    )
)

echo [错误] 未找到 Python 解释器！
echo       请将解压包中的 runtime 目录保留完整，或安装 Python 3.12+ 后重试。
pause
exit /b 1

:found_python
echo.
echo ═══ 依赖检查 ═══
"%PYTHON%" -c "import pandas, openpyxl, xlrd" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo [错误] 缺少运行依赖（pandas / openpyxl / xlrd）！
    echo.
    echo   请先安装依赖：
    echo     "%PYTHON%" -m pip install -r requirements.txt
    echo.
    echo   或创建 Conda 环境：
    echo     conda create -n visual-dashboard-system python=3.12
    echo     conda activate visual-dashboard-system
    echo     pip install -r requirements.txt
    pause
    exit /b %ERRORLEVEL%
)
echo   ✅ 依赖正常
echo.

echo ═══ 预检 ═══
"%PYTHON%" main.py --dry-run
if %ERRORLEVEL% neq 0 (
    echo.
    echo [错误] 预检失败，请检查以下项目：
    echo   ▪ data\raw\财务端数据\   原始 Excel（收入/回款）
    echo   ▪ data\raw\运营端数据\   原始 Excel（收入/回款）
    echo   ▪ data\raw\往年收入数据\ 往年收入基线 Excel
    echo   ▪ data\raw\往年回款数据\ 往年回款基线 Excel
    echo   ▪ data\mappings\         部门事业部映射 / 客户名单
    echo   ▪ config\清洗配置\       cleaning_config.json
    pause
    exit /b %ERRORLEVEL%
)
echo.

REM ============================================
REM 主流程（顺序固定，勿颠倒）：
REM   ① 配置同步   配置编辑器.xlsx → JSON（时间/结算模式/展示规则/KPI/销售归属/字段映射）
REM   ② Phase 0    年基线清洗（往年收入/回款）
REM   ③ Phase 1+2  收入/回款清洗
REM   ④ Phase 3    销售拆分
REM   ⑤ Phase 4    渲染看板 + 数据总表
REM   由 main.py 统一调度，与「启动系统.bat」图形控制台走同一条链路
REM ============================================
echo   提示: 请先在 config\配置编辑器.xlsx 更新配置（时间/结算模式/展示规则/KPI/销售归属），保存后再运行
echo.
echo ═══ 主流程（由 main.py 调度）═══
"%PYTHON%" main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [错误] 主流程中断（详见上方输出或 logs\ 目录日志）
    echo.
    echo   续跑方式（按失败步骤选择）：
    echo     "%PYTHON%" main.py --from=config    配置同步(Excel-^>JSON)
    echo     "%PYTHON%" main.py --from=yearly    年基线清洗
    echo     "%PYTHON%" main.py --from=clean     收入/回款清洗
    echo     "%PYTHON%" main.py --from=split     销售拆分
    echo     "%PYTHON%" main.py --from=render    渲染看板
    echo.
    pause
    exit /b %ERRORLEVEL%
)

REM ============================================
echo ═══ Phase 5: 生成销售完成度汇总表 ═══
if exist "scripts\sales_summary_report.py" (
    "%PYTHON%" scripts\sales_summary_report.py
    if !ERRORLEVEL! neq 0 (
        echo [警告] 销售完成度汇总表生成失败！
    )
) else (
    echo [跳过] scripts\sales_summary_report.py 不存在
)
echo.

REM ============================================
echo ═══ Phase 6: 看板质量验证 ═══
if exist "scripts\verify_dashboard.py" (
    "%PYTHON%" scripts\verify_dashboard.py
    if %ERRORLEVEL% neq 0 (
        echo [警告] 看板验证发现问题，请检查 JS 语法或函数绑定！
    )
) else (
    echo [跳过] scripts\verify_dashboard.py 不存在
)
echo.

REM ============================================
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║  ✅ 全部完成！                                     ║
echo ╚══════════════════════════════════════════════════════╝
echo.
echo   输出文件:
for %%f in ("output\看板\看板_*.html") do echo     ▪ 看板: %%f
for %%f in ("output\数据\data_*.xlsx")  do echo     ▪ 数据总表: %%f
for %%f in ("output\销售完成度\销售完成度汇总_*.xlsx") do echo     ▪ 销售完成度: %%f
echo.
echo   运行日志: logs\
echo.
start "" "output"

:end
pause
