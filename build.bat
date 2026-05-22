@echo off
chcp 65001 >nul
title 编译驱动检测工具

echo.
echo  ╔══════════════════════════════════════╗
echo  ║     驱动检测与修复工具  编译脚本      ║
echo  ╚══════════════════════════════════════╝
echo.

:: ── 检查 Python ──────────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  [错误] 未找到 Python，请先安装 Python 3.8+
    echo  下载地址: https://www.python.org/downloads/
    pause & exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  Python 版本: %%v

:: ── 安装 PyInstaller ─────────────────────────────────────────────────────────
echo.
echo  正在安装/更新 PyInstaller...
python -m pip install --upgrade pyinstaller --quiet
if errorlevel 1 (
    echo  [错误] PyInstaller 安装失败
    pause & exit /b 1
)

:: ── 编译 ─────────────────────────────────────────────────────────────────────
echo.
echo  开始编译（首次可能需要 1~3 分钟）...
echo.

set ICON_OPT=
if exist icon.ico set ICON_OPT=--icon=icon.ico

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "驱动检测与修复工具" ^
    --uac-admin ^
    %ICON_OPT% ^
    driver_doctor.py

if errorlevel 1 (
    echo.
    echo  [错误] 编译失败，请查看上方输出信息
    pause & exit /b 1
)

:: ── 完成 ─────────────────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════╗
echo  ║        编译成功！                    ║
echo  ║  输出文件: dist\驱动检测与修复工具.exe ║
echo  ╚══════════════════════════════════════╝
echo.

:: 将 exe 复制到当前目录方便使用
if exist "dist\驱动检测与修复工具.exe" (
    copy "dist\驱动检测与修复工具.exe" "驱动检测与修复工具.exe" >nul
    echo  已将 exe 复制到当前目录。
)

pause
