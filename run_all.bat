@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ═══════════════════════════════════════════════
echo   Visual Dashboard System — 一键运行
echo   %date% %time%
echo ═══════════════════════════════════════════════

set PYTHON=C:\Users\bai_b\.conda\envs\visual-dashboard-system\python.exe
cd /d "%~dp0"

echo.
echo [1/5] 清理旧的系统数据文件 ...
%PYTHON% -c "import os;root=r'data\sheets\系统数据清理';d=os.walk(root);[os.remove(os.path.join(r,f)) for r,_,fs in d for f in fs if f.endswith('.xlsx')];print('  ✅ 已清空')"

echo.
echo [2/5] 年基线清洗 ...
%PYTHON% -m engine.yearly_baseline.run
if %ERRORLEVEL% neq 0 echo  ⚠️ 年基线异常 & goto :end

echo.
echo [3/5] 收入/回款清洗 ...
%PYTHON% -m engine.income_payment.run
if %ERRORLEVEL% neq 0 echo  ⚠️ 收入/回款清洗异常 & goto :end

echo.
echo [4/5] 销售拆分 ...
%PYTHON% -m engine.sales.run
if %ERRORLEVEL% neq 0 echo  ⚠️ 销售拆分异常 & goto :end

echo.
echo [5/5] 渲染看板 + 汇总Excel ...
%PYTHON% -m processors.run
if %ERRORLEVEL% neq 0 echo  ⚠️ 渲染异常 & goto :end

echo.
echo ═══════════════════════════════════════════════
echo  ✅ 全部完成！
echo  输出文件:
for %%f in ("output\看板_*.html") do echo   看板: %%f
for %%f in ("output\data_*.xlsx") do echo   总表: %%f
echo ═══════════════════════════════════════════════
start "" "output"

:end
echo.
pause
