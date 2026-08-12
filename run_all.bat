@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Visual Dashboard System — 一键运行

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

echo [错误] 未找到 Python 解释器！请先安装 Python 3.12+ 或配置 Conda 环境。
pause
exit /b 1

:found_python
echo.
echo ═══ 预检 ═══
%PYTHON% main.py --dry-run
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
echo ═══ Phase 0: 年基线清洗 ═══
%PYTHON% -m engine.yearly_baseline.run
if %ERRORLEVEL% neq 0 (
    echo [警告] 年基线清洗异常，继续执行后续步骤...
    echo.
)

REM ============================================
echo ═══ Phase 1+2: 收入/回款清洗 ═══
%PYTHON% -m engine.income_payment.run
if %ERRORLEVEL% neq 0 (
    echo [错误] 收入/回款清洗失败！
    pause
    exit /b %ERRORLEVEL%
)

REM ============================================
echo ═══ Phase 3: 销售拆分 ═══
%PYTHON% -m engine.sales.run
if %ERRORLEVEL% neq 0 (
    echo [错误] 销售拆分失败！
    pause
    exit /b %ERRORLEVEL%
)

REM ============================================
echo ═══ Phase 4: 渲染看板 + 汇总Excel ═══
%PYTHON% -m processors.run
if %ERRORLEVEL% neq 0 (
    echo [错误] 渲染失败！
    pause
    exit /b %ERRORLEVEL%
)

REM ============================================
echo ═══ Phase 5: 看板质量验证 ═══
if exist "scripts\verify_dashboard.py" (
    %PYTHON% scripts\verify_dashboard.py
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
