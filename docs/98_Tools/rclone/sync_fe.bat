@echo off
chcp 65001 >nul
REM ============================================================================
REM Rclone Bisync - MathBattle-FE
REM ============================================================================

setlocal enabledelayedexpansion

set REMOTE_NAME=google_driver
set REMOTE_FOLDER=MathBattle
set LOCAL_FOLDER=D:\3_CODING\MathBattle\MathBattle-FE\docs

echo.
echo ============================================================================
echo Sync: %REMOTE_FOLDER% ^<-^> %LOCAL_FOLDER%
echo ============================================================================
echo.

where rclone >nul 2>&1
if errorlevel 1 (
    echo ❌ Lỗi: Rclone chưa được cài đặt
    pause
    exit /b 1
)

if not exist "%LOCAL_FOLDER%" (
    echo ⚠ Tạo folder: %LOCAL_FOLDER%
    mkdir "%LOCAL_FOLDER%"
)

set "REMOTE_PATH=%REMOTE_NAME%:%REMOTE_FOLDER%"

echo.
echo Chọn chiều Sync:
echo.
echo   1. PULL (Drive ^-^> Máy tính)
echo   2. PUSH (Máy tính ^-^> Drive)
echo   3. BISYNC (Hai chiều - tự động)
echo.
set /p SYNC_MODE="Nhập lựa chọn (1/2/3) [mặc định: 3]: "
if "%SYNC_MODE%"=="" set SYNC_MODE=3

echo.
if "%SYNC_MODE%"=="1" (
    echo Mode: PULL - Lấy từ Drive về máy tính
    set SYNC_CMD=rclone sync "!REMOTE_PATH!" "%LOCAL_FOLDER%" --progress -v
) else if "%SYNC_MODE%"=="2" (
    echo Mode: PUSH - Đẩy từ máy tính lên Drive
    set SYNC_CMD=rclone sync "%LOCAL_FOLDER%" "!REMOTE_PATH!" --progress -v
) else if "%SYNC_MODE%"=="3" (
    echo Mode: BISYNC - Đồng bộ hai chiều
    set SYNC_CMD=rclone bisync "!REMOTE_PATH!" "%LOCAL_FOLDER%" --progress -v
) else (
    echo ❌ Lựa chọn không hợp lệ!
    pause
    exit /b 1
)

echo.
echo Đang sync...
echo.

!SYNC_CMD!

if errorlevel 1 (
    echo.
    echo ⚠ Lỗi sync, tự động chạy RESYNC...
    echo.
    
    rclone bisync "!REMOTE_PATH!" "%LOCAL_FOLDER%" --resync --progress -v
    
    if errorlevel 1 (
        echo.
        echo ❌ Lỗi cả resync!
    ) else (
        echo.
        echo ✓ Resync hoàn thành!
    )
) else (
    echo.
    echo ✓ Sync hoàn thành!
)

echo.
pause
