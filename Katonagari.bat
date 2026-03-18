@echo off
title PROJECT LAUNCHER v1.0
color 0A

:: ── CONFIG ──────────────────────────────────────────
set "PASSWORD=Makesure1233"
set "MAX_ATTEMPTS=3"
set "LOG_FILE=%~dp0launcher.log"
:: ────────────────────────────────────────────────────

set "attempts=0"
cls

:boot
cls
echo.
echo  [sys] Initializing secure environment...
ping -n 2 127.0.0.1 >nul
echo  [sys] Loading project registry...
ping -n 1 127.0.0.1 >nul
echo  [sys] Ready.
ping -n 1 127.0.0.1 >nul
goto auth

:auth
cls
echo.
echo  =============================================
echo        SECURE PROJECT LAUNCHER v1.0
echo  =============================================
echo.
echo  [!] Authentication required
echo.
set /p "INPUT_PASS=  Password: "

if "%INPUT_PASS%"=="%PASSWORD%" goto success

set /a attempts+=1
echo.
echo  [X] Access denied. Attempt %attempts% of %MAX_ATTEMPTS%.
echo  [%date% %time%] FAILED LOGIN ATTEMPT >> "%LOG_FILE%"
ping -n 2 127.0.0.1 >nul

if %attempts% geq %MAX_ATTEMPTS% goto lockout
goto auth

:lockout
cls
echo.
echo  =============================================
echo  [!!!]  ACCOUNT LOCKED — TOO MANY ATTEMPTS
echo  =============================================
echo.
echo  [%date% %time%] LOCKOUT TRIGGERED >> "%LOG_FILE%"
echo  Contact system administrator.
echo.
ping -n 4 127.0.0.1 >nul
exit

:success
echo.
echo  [OK] Access granted. Welcome.
echo  [%date% %time%] SUCCESSFUL LOGIN >> "%LOG_FILE%"
ping -n 2 127.0.0.1 >nul

:menu
cls
echo.
echo  =============================================
echo        MY PYTHON PROJECTS
echo  =============================================
echo  Session: %date% %time%
echo  User:    %USERNAME%
echo  =============================================
echo.
echo   [1]  Katonagari
echo   [2]  Project 2
echo   [3]  Project 3
echo.
echo   [L]  View login log
echo   [P]  Change password
echo   [0]  Exit
echo.
set /p choice="  Select: "

if /i "%choice%"=="1" goto Katonagari
if /i "%choice%"=="2" goto Project2
if /i "%choice%"=="3" goto Project3
if /i "%choice%"=="L" goto viewlog
if /i "%choice%"=="P" goto changepass
if /i "%choice%"=="0" goto quit
goto menu

:Katonagari
cls
echo  [>>] Launching Katonagari...
echo  [%date% %time%] LAUNCHED: Katonagari >> "%LOG_FILE%"
cd /d "D:\Personal Projects\Jetbrains\Pycharm\Katonagari"
call .venv\Scripts\activate
cmd /k "python app.py"
goto menu

:Project2
cls
echo  [>>] Launching Project 2...
echo  [%date% %time%] LAUNCHED: Project 2 >> "%LOG_FILE%"
cd /d "D:\path\to\project2"
call .venv\Scripts\activate
cmd /k "python main.py"
goto menu

:Project3
cls
echo  [>>] Launching Project 3...
echo  [%date% %time%] LAUNCHED: Project 3 >> "%LOG_FILE%"
cd /d "D:\path\to\project3"
call .venv\Scripts\activate
cmd /k "python main.py"
goto menu

:viewlog
cls
echo  =============================================
echo         ACTIVITY LOG
echo  =============================================
echo.
if exist "%LOG_FILE%" (
    type "%LOG_FILE%"
) else (
    echo  No log entries yet.
)
echo.
pause
goto menu

:changepass
cls
echo  =============================================
echo         CHANGE PASSWORD
echo  =============================================
echo.
set /p "OLD_PASS=  Current password: "
if not "%OLD_PASS%"=="%PASSWORD%" (
    echo.
    echo  [X] Wrong password.
    ping -n 2 127.0.0.1 >nul
    goto menu
)
set /p "NEW_PASS=  New password: "
set /p "CONFIRM_PASS=  Confirm new password: "
if not "%NEW_PASS%"=="%CONFIRM_PASS%" (
    echo.
    echo  [X] Passwords do not match.
    ping -n 2 127.0.0.1 >nul
    goto menu
)
set "PASSWORD=%NEW_PASS%"
echo.
echo  [OK] Password changed successfully.
echo  [%date% %time%] PASSWORD CHANGED >> "%LOG_FILE%"
ping -n 2 127.0.0.1 >nul
goto menu

:quit
cls
echo.
echo  [sys] Session terminated. Goodbye.
echo  [%date% %time%] SESSION ENDED >> "%LOG_FILE%"
ping -n 2 127.0.0.1 >nul
exit