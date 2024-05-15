@ECHO off

:: Main script execution
CD /D "%~dp0\.."

SET app_version=latest
SET install_dir=%CD%\install_dir
SET conda_root=%install_dir%\conda
SET env_dir=%install_dir%\env

ECHO %CD%| FINDSTR /C:" " >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    ECHO The current workdir has whitespace which can lead to unintended behaviour. Please modify your path and continue later.
    GOTO :end
)

CALL :print_highlight "Activating conda environment"
CALL :activate_environment
IF ERRORLEVEL 1 GOTO :end

CALL :print_highlight "Updating Kotaemon to latest"
CALL :update_latest
IF ERRORLEVEL 1 GOTO :end

CALL :deactivate_environment
GOTO :end_success


:activate_environment
:: deactivate existing conda env(s) to avoid conflicts
( CALL conda deactivate && CALL conda deactivate && CALL conda deactivate ) 2> nul

CALL "%env_dir%\python.exe" --version >nul 2>&1 || (
    ECHO The environment appears to be broken. You may need to remove %env_dir% and run the installer again.
    GOTO :exit_func_with_error
)

CALL "%conda_root%\condabin\conda.bat" activate %env_dir% || (
    ECHO Failed to activate environment. You may need to remove %env_dir% and run the installer again.
    GOTO :exit_func_with_error
)
ECHO Activate conda environment at %env_dir%

GOTO :eof

:deactivate_environment
:: Conda deactivate if we are in the right env
IF "%CONDA_PREFIX%" == "%env_dir%" (
    CALL "%conda_root%\condabin\conda.bat" deactivate
    ECHO Deactivate conda environment at %env_dir%
)
GOTO :eof

:update_latest
FOR /F "tokens=1,2" %%a in ('pip list') do if "%%a"=="kotaemon-app" set current_version=%%b
ECHO Current version %current_version%

IF EXIST "pyproject.toml" (
    ECHO Source files detected. Please perform git pull manually.
    CALL :deactivate_environment
    GOTO :exit_func_with_error
) ELSE (
    ECHO Installing version: %app_version%
    @REM Work around for versioning control
    python -m pip install git+https://github.com/Cinnamon/kotaemon.git@"%app_version%"#subdirectory=libs/kotaemon
    python -m pip install git+https://github.com/Cinnamon/kotaemon.git@"%app_version%"#subdirectory=libs/ktem
    python -m pip install --no-deps git+https://github.com/Cinnamon/kotaemon.git@"%app_version%"
) || (
    ECHO. && ECHO Update failed. You may need to run the update again.
    CALL :deactivate_environment
    GOTO :exit_func_with_error
)

CALL :print_highlight "Update successfully."
FOR /F "tokens=1,2" %%a in ('pip list') do if "%%a"=="kotaemon-app" set updated_version=%%b
ECHO Updated version %updated_version%
ECHO %updated_version% > VERSION
GOTO :eof

:print_highlight
ECHO. && ECHO ******************************************************
ECHO %~1
ECHO ****************************************************** && ECHO.
GOTO :eof

:exit_func_with_error
:: Called inside functions when error happens, then back to the main routine with error code 1
EXIT /B 1

:end_success
:: Exit the script main routine with error code 0 (success)
ECHO Script completed successfully.
PAUSE
EXIT /B 0

:end
:: Exit the script main routine with error code 1 (fail)
PAUSE
EXIT /B 1
