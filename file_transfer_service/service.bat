@echo off
REM 文件传输服务管理脚本 (Windows)

set SERVICE_NAME=file-transfer-service
set PID_FILE=%TEMP%\file-transfer.pid

:menu
cls
echo ========================================
echo    文件传输服务管理
echo ========================================
echo 1. 启动服务
echo 2. 停止服务  
echo 3. 重启服务
echo 4. 查看状态
echo 5. 查看日志
echo 6. 退出
echo ========================================
echo.

choice /c 123456 /m "请选择操作"

if %errorlevel% == 1 goto start
if %errorlevel% == 2 goto stop
if %errorlevel% == 3 goto restart
if %errorlevel% == 4 goto status
if %errorlevel% == 5 goto logs
if %errorlevel% == 6 goto exit

:start
echo 启动文件传输服务...
start /b python app.py > %TEMP%\file-transfer.log 2>&1
echo 服务启动命令已执行
echo 访问地址: http://localhost:8080
timeout /t 3 >nul
goto menu

:stop
echo 停止文件传输服务...
taskkill /f /im python.exe /fi "WINDOWTITLE eq *app.py*" >nul 2>&1
echo 服务已停止
timeout /t 2 >nul
goto menu

:restart
echo 重启文件传输服务...
call :stop
timeout /t 2 >nul
call :start
goto menu

:status
echo 检查服务状态...
tasklist /fi "imagename eq python.exe" /fo csv | findstr "app.py" >nul
if %errorlevel% == 0 (
    echo ✅ 服务正在运行
    echo 访问地址: http://localhost:8080
) else (
    echo ⭕ 服务未运行
)
timeout /t 3 >nul
goto menu

:logs
echo 查看日志文件:
type %TEMP%\file-transfer.log
echo.
pause
goto menu

:exit
exit /b 0