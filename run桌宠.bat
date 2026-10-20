@echo off
rem 源码方式启动桌宠(需要 Python 3 + PyQt5)
rem 分享给别人时,请优先使用打包好的 桌宠.exe,无需安装任何环境
cd /d "%~dp0"
where pyw.exe >nul 2>nul
if %errorlevel%==0 (
    start "" pyw.exe -3 pet.py
) else (
    where pythonw.exe >nul 2>nul
    if %errorlevel%==0 (
        start "" pythonw.exe pet.py
    ) else (
        echo [错误] 未找到 Python。请安装 Python 3,或直接运行打包好的 桌宠.exe
        pause
    )
)
