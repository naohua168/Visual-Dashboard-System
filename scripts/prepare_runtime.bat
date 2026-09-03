@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Visual Dashboard System — 构建内置运行时

REM ============================================
REM 构建内置 Python 运行时 (runtime\python)
REM 作用：把 Python 解释器 + 全部依赖库打包进项目，
REM       让接收方"解压即用"，无需安装任何环境。
REM 说明：首次打包前运行一次即可；runtime 已存在时自动跳过下载。
REM ============================================

set ROOT=%~dp0..
cd /d "%ROOT%"

REM 版本配置（嵌入式 Python 从 python.org 下载）
set PY_VER=3.12.10
set PY_EMBED_URL=https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-embed-amd64.zip
set EMBED_DIR=runtime\python
set PTH_FILE=%EMBED_DIR%\python%PY_VER:~0,1%%PY_VER:~2,1%%PY_VER:~4,1%._pth

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║   构建内置运行时（解压即用，免安装）                  ║
echo ╚══════════════════════════════════════════════════════╝
echo.

REM 0) 检测宿主机 Python（仅用于 pip 把依赖装进内置运行时）
set HOST_PY=
for %%p in (python python3) do (
    where %%p >nul 2>&1
    if !errorlevel!==0 (
        set HOST_PY=%%p
        goto :host_found
    )
)
:host_found
if not defined HOST_PY (
    echo [错误] 未找到 python 命令，无法用 pip 安装依赖到内置运行时。
    echo       请先安装 Python 3.12+ 后再运行本脚本。
    exit /b 1
)

REM 1) 下载 + 解压嵌入式 Python
if exist "%EMBED_DIR%\python.exe" (
    echo [跳过] %EMBED_DIR% 已存在（如需重建请先删除 runtime\python 目录）
) else (
    echo [1/4] 下载嵌入式 Python %PY_VER% ...
    powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PY_EMBED_URL%' -OutFile '%TEMP%\python-embed.zip'"
    if errorlevel 1 (
        echo [错误] 下载失败，请检查网络后重试。
        exit /b 1
    )
    echo [2/4] 解压到 %EMBED_DIR% ...
    if not exist "%EMBED_DIR%" mkdir "%EMBED_DIR%"
    powershell -NoProfile -Command "Expand-Archive -Path '%TEMP%\python-embed.zip' -DestinationPath '%EMBED_DIR%' -Force"
    del /q "%TEMP%\python-embed.zip" >nul 2>&1
)

REM 2) 启用 site-packages + 项目根目录（嵌入式 Python 默认不加载第三方包，
REM    且 _pth 存在时 -m 模式不会自动把当前目录加入 sys.path，需显式加 ..\..）
echo [3/4] 配置 site-packages 加载 ...
> "%PTH_FILE%" echo python312.zip
>> "%PTH_FILE%" echo .
>> "%PTH_FILE%" echo Lib\site-packages
>> "%PTH_FILE%" echo ..\..
>> "%PTH_FILE%" echo.
>> "%PTH_FILE%" echo # Uncomment to run site.main() automatically
>> "%PTH_FILE%" echo import site

REM 3) 安装依赖到内置运行时
echo [4/4] 安装依赖（pandas / openpyxl / xlrd）...
if not exist "%EMBED_DIR%\Lib\site-packages" mkdir "%EMBED_DIR%\Lib\site-packages"
%HOST_PY% -m pip install --target "%EMBED_DIR%\Lib\site-packages" --no-compile pandas openpyxl xlrd
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查 pip 是否可用。
    exit /b 1
)

REM 4) 验证
echo.
echo ─── 运行时验证 ───
"%EMBED_DIR%\python.exe" -c "import sys, pandas, openpyxl, xlrd; print('Python', sys.version.split()[0], '| pandas', pandas.__version__, '| openpyxl', openpyxl.__version__, '| xlrd', xlrd.__version__)"
if errorlevel 1 (
    echo [错误] 运行时验证失败！
    exit /b 1
)

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║  ✅ 内置运行时构建完成！                             ║
echo ║  现在运行 package.bat 打包，接收方即可解压即用。     ║
echo ╚══════════════════════════════════════════════════════╝
echo.
pause
