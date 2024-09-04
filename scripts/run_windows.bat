@ECHO off

:: Main script execution
CD /D "%~dp0\.."

SET /p app_version=<"%CD%\VERSION" || SET app_version=latest
SET install_dir=%CD%\install_dir
SET conda_root=%install_dir%\conda
SET env_dir=%install_dir%\env
SET python_version=3.10
SET miniconda_download_url=https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe

SET git_install_dir=%install_dir%\git
SET git_download_url=https://github.com/git-for-windows/git/releases/download/v2.46.0.windows.1/Git-2.46.0-64-bit.exe

ECHO %CD%| FINDSTR /C:" " >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    ECHO The current workdir has whitespace which can lead to unintended behaviour. Please modify your path and continue later.
    GOTO :end
)

CALL :print_highlight "Setting up git"


CALL :print_highlight "Setting up Miniconda"
CALL :download_and_install_miniconda
:: check if function run fail, then exit the script
IF ERRORLEVEL 1 GOTO :end

CALL :print_highlight "Creating conda environment"
CALL :create_conda_environment
IF ERRORLEVEL 1 GOTO :end

CALL :activate_environment
IF ERRORLEVEL 1 GOTO :end

CALL :print_highlight "Installing Kotaemon"
CALL :install_dependencies
IF ERRORLEVEL 1 GOTO :end

CALL :print_highlight "Setting up a local model"
CALL :setup_local_model
IF ERRORLEVEL 1 GOTO :end

CALL :print_highlight "Launching Kotaemon in your browser, please wait..."
CALL :launch_ui

CALL :deactivate_environment
GOTO :end_success

:download_and_install_git
:: figure out whether git is installed
CALL git --version >nul 2>&1 
IF %ERRORLEVEL% NEQ 0 (
    :: TODO: Check 32-bit or 64-bit
    ECHO Downloading Git from %git_download_url%
    CALL curl -Lk "%git_download_url%" -o "%install_dir%\git_installer.exe" || (
        ECHO. && ECHO Failed to download Git. Aborting...
        GOTO :exit_func_with_error
    )
    ECHO Installing Git to %git_install_dir%
    CALL "%install_dir%\git_installer.exe" /VERYSILENT /NORESTART /NOCANCEL /SP- /DIR="%git_install_dir%" /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /NOICONS /COMPONENTS="icons,ext\reg\shellhere,assoc,assoc_sh"
    DEL "%install_dir%\git_installer.exe"
)

:download_and_install_miniconda
IF NOT EXIST "%install_dir%" ( MKDIR "%install_dir%" )

:: If conda has been installed at the %conda_root%, don't need to reinstall it
CALL "%conda_root%\_conda.exe" --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    IF NOT EXIST "%install_dir%\miniconda_installer.exe" (
        ECHO Downloading Miniconda from %miniconda_download_url%
        CALL curl -Lk "%miniconda_download_url%" -o "%install_dir%\miniconda_installer.exe" || (
            ECHO. && ECHO Failed to download Miniconda. Aborting...
            GOTO :exit_func_with_error
        )
    )
    ECHO Installing Miniconda to %conda_root%
    START /wait "" "%install_dir%\miniconda_installer.exe" /InstallationType=JustMe /NoShortcuts=1 /AddToPath=0 /RegisterPython=0 /NoRegistry=1 /S /D=%conda_root%
    DEL "%install_dir%\miniconda_installer.exe"
)
ECHO Conda is installed at %conda_root%

:: recheck conda
ECHO Conda version:
CALL "%conda_root%\_conda.exe" --version || ( ECHO. && ECHO Conda not found. Aborting... && GOTO :exit_func_with_error )

GOTO :eof

:create_conda_environment
:: Create new conda environment if it doesn't exist
IF NOT EXIST %env_dir% (
    ECHO Creating conda environment with python=%python_version% in %env_dir%
    :: Create conda environment. If the interruption happens, rollback and remove the env_dir
    CALL "%conda_root%\_conda.exe" create --no-shortcuts -y -k --prefix %env_dir% python=%python_version% || (
        ECHO. && ECHO Failed to create conda environment. Will delete the %env_dir% and abort now...
        RMDIR /s /q %env_dir%
        GOTO :exit_func_with_error
    )
    ECHO Conda environment created successfully
) ELSE (
    ECHO Conda environment exists at %env_dir%
)
GOTO :eof

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

:install_dependencies
pip list | findstr /C:"kotaemon" >NUL 2>&1
IF %ERRORLEVEL% == 0  (
    ECHO Dependencies are already installed
) ELSE (
    IF EXIST "pyproject.toml" (
        ECHO Found pyproject.toml. Installing from source...

        ECHO Installing libs\kotaemon
        python -m pip install -e "%CD%\libs\kotaemon"

        ECHO Installing libs\ktem
        python -m pip install -e "%CD%\libs\ktem"

        python -m pip install --no-deps -e .
    ) ELSE (
        ECHO Installing Kotaemon %app_version%
        @REM Work around for versioning control
        python -m pip install git+https://github.com/Cinnamon/kotaemon.git@"%app_version%"#subdirectory=libs/kotaemon
        python -m pip install git+https://github.com/Cinnamon/kotaemon.git@"%app_version%"#subdirectory=libs/ktem
        python -m pip install --no-deps git+https://github.com/Cinnamon/kotaemon.git@"%app_version%"
    )

    ( CALL pip list | findstr /C:"kotaemon" >NUL 2>&1 ) || (
        ECHO. && ECHO Installation failed. You may need to run the installer again.
        CALL :deactivate_environment
        GOTO :exit_func_with_error
    )

    CALL :print_highlight "Install successfully. Clear cache..."
    "%conda_root%\condabin\conda.bat" clean --all -y
    python -m pip cache purge
)
GOTO :eof

:setup_local_model
python "%CD%\scripts\serve_local.py"
GOTO :eof

:launch_ui
CALL python "%CD%\app.py" || ( ECHO. && ECHO Will exit now... && GOTO :exit_func_with_error )
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
