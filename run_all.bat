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
REM 配置同步：Excel 编辑器 → JSON（改配置后自动生效）
REM ============================================
echo ═══ 配置同步 ═══
if exist "config\配置编辑器.xlsx" (
    if exist "scripts\config_excel_to_json.py" (
        "%PYTHON%" scripts\config_excel_to_json.py
        if %ERRORLEVEL% neq 0 (
            echo [警告] 配置同步失败，请检查 config\配置编辑器.xlsx 中的配置是否合法！
            echo    （日期格式 / 模式 / 动态策略有误时生成器会拒绝写回）
            pause
            exit /b %ERRORLEVEL%
        )
    ) else (
        echo [跳过] scripts\config_excel_to_json.py 不存在
    )
) else (
    echo [跳过] config\配置编辑器.xlsx 不存在
)
echo.

REM ============================================
echo ═══ Phase 0: 年基线清洗 ═══
"%PYTHON%" -m engine.yearly_baseline.run
if %ERRORLEVEL% neq 0 (
    echo [警告] 年基线清洗异常，继续执行后续步骤...
    echo          （年度同比功能将降级为不显示，其余页面不受影响）
    echo.
)

REM ============================================
echo ═══ Phase 1+2: 收入/回款清洗 ═══
"%PYTHON%" -m engine.income_payment.run
if %ERRORLEVEL% neq 0 (
    echo [错误] 收入/回款清洗失败！
    echo.
    echo   修复后可用以下命令从本步骤续跑：
    echo     "%PYTHON%" main.py --from=clean
    pause
    exit /b %ERRORLEVEL%
)

REM ============================================
echo ═══ Phase 3: 销售拆分 ═══
"%PYTHON%" -m engine.sales.run
if %ERRORLEVEL% neq 0 (
    echo [错误] 销售拆分失败！
    echo.
    echo   修复后可用以下命令从本步骤续跑：
    echo     "%PYTHON%" main.py --from=split
    pause
    exit /b %ERRORLEVEL%
)

REM ============================================
echo ═══ Phase 4: 渲染看板 + 汇总Excel ═══
"%PYTHON%" -m processors.run
if %ERRORLEVEL% neq 0 (
    echo [错误] 渲染失败！
    echo.
    echo   修复后可用以下命令从本步骤续跑：
    echo     "%PYTHON%" main.py --from=render
    pause
    exit /b %ERRORLEVEL%
)

REM ============================================
echo ═══ Phase 5: 看板质量验证 ═══
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
for %%f in ("output\数据\data_*.xlsx")  do echo     ▪ 总表: %%f
echo.
echo   运行日志: logs\
echo.
start "" "output"

:end
pause
