@ECHO off

:: Main script execution
CD /D "%~dp0\.."

SET /p app_version=<"%CD%\VERSION" || SET app_version=latest
SET install_dir=%CD%\install_dir
SET conda_root=%install_dir%\conda
SET env_dir=%install_dir%\env
SET python_version=3.10
SET miniconda_download_url=https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe

SET git_install_dir=%install_dir%\Git
SET seven_zip_dir=%install_dir%\7zip
:: Determine if the machine is 32-bit or 64-bit
IF "%PROCESSOR_ARCHITECTURE%"=="x86" (
    SET seven_zip_url=https://7-zip.org/a/7z2408.exe
    SET git_download_url=https://github.com/git-for-windows/git/releases/download/v2.46.0.windows.1/PortableGit-2.46.0-32-bit.7z.exe
) ELSE (
    SET seven_zip_url=https://7-zip.org/a/7z2408-x64.exe
    SET git_download_url=https://github.com/git-for-windows/git/releases/download/v2.46.0.windows.1/PortableGit-2.46.0-64-bit.7z.exe
)

ECHO %CD%| FINDSTR /C:" " >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    ECHO The current workdir has whitespace which can lead to unintended behaviour. Please modify your path and continue later.
    GOTO :end
)

IF NOT EXIST "%install_dir%" ( MKDIR "%install_dir%" )

CALL :print_highlight "Setting up Git"
CALL :download_and_install_git
IF ERRORLEVEL 1 GOTO :end

:: Temporarily add Portable Git to PATH
SET "PATH=%git_install_dir%\bin;%PATH%"

CALL :print_highlight "Setting up Miniconda"
CALL :download_and_install_miniconda
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

CALL :print_highlight "Downloading and extracting PDF.js"
CALL :download_and_extract_pdf_js
IF ERRORLEVEL 1 GOTO :end

CALL :print_highlight "Launching Kotaemon in your browser, please wait..."
CALL :launch_ui

CALL :deactivate_environment
GOTO :end_success

:download_and_install_7zip
:: Check if 7-Zip is installed
IF NOT EXIST "%seven_zip_dir%\7z.exe" (
    ECHO Downloading 7-Zip from %seven_zip_url%
    CALL curl -Lk "%seven_zip_url%" -o "%install_dir%\7zip_installer.exe" || (
        ECHO. && ECHO Failed to download 7-Zip. Aborting...
        GOTO :exit_func_with_error
    )
    ECHO Installing 7-Zip to %seven_zip_dir%
    CALL "%install_dir%\7zip_installer.exe" /S /D=%seven_zip_dir%
    DEL "%install_dir%\7zip_installer.exe"
)
ECHO 7-Zip is installed at %seven_zip_dir%

GOTO :eof

:uninstall_7zip
IF EXIST "%seven_zip_dir%\Uninstall.exe" (
    CALL "%seven_zip_dir%\Uninstall.exe" /S
) ELSE (
    ECHO. && ECHO Uninstaller not found. Manually deleting 7-Zip directory...
    RMDIR /S /Q "%seven_zip_dir%"
)

GOTO :eof

:download_and_install_git
:: Check if Git is already installed
CALL "%git_install_dir%\bin\git.exe" --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO Install 7-Zip to extract Portable Git. It will be uninstalled automatically after Git installation. && ECHO.
    CALL :download_and_install_7zip
    IF ERRORLEVEL 1 GOTO :end

    ECHO. && ECHO Downloading Portable Git from %git_download_url%
    CALL curl -Lk "%git_download_url%" -o "%install_dir%\portable_git.7z.exe" || (
        ECHO. && ECHO Failed to download Git. Aborting...
        GOTO :exit_func_with_error
    )

    ECHO Extracting Git to %git_install_dir%...
    CALL "%seven_zip_dir%\7z.exe" x "%install_dir%\portable_git.7z.exe" -o"%git_install_dir%" -y >nul || (
        ECHO. && ECHO Failed to extract Git. Aborting...
        GOTO :exit_func_with_error
    )
    DEL "%install_dir%\portable_git.7z.exe"

    ECHO. && ECHO Uninstalling 7-Zip...
    CALL :uninstall_7zip
    IF ERRORLEVEL 1 GOTO :end
)
ECHO Git is installed at %git_install_dir%
:: Recheck Git installation
CALL "%git_install_dir%\bin\git.exe" --version || (
    ECHO. && ECHO Git not found. Aborting...
    GOTO :exit_func_with_error
)

SET "PATH=%git_install_dir%\bin;%PATH%"
ECHO Git is added to PATH for this session

GOTO :eof

:download_and_install_miniconda
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

:: Recheck conda
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
:: Deactivate existing conda env(s) to avoid conflicts
IF EXIST "%conda_root%\condabin\conda.bat" (
    CALL "%conda_root%\condabin\conda.bat" deactivate
    CALL "%conda_root%\condabin\conda.bat" deactivate
    CALL "%conda_root%\condabin\conda.bat" deactivate
)

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

:download_and_extract_pdf_js
:: Download and extract a ZIP file from a URL to a destination directory

REM Define variables
set "pdf_js_version=4.0.379"
set "pdf_js_dist_name=pdfjs-%pdf_js_version%-dist"
set "pdf_js_dist_url=https://github.com/mozilla/pdf.js/releases/download/v%pdf_js_version%/%pdf_js_dist_name%.zip"
for /f "delims=" %%i in ('cd') do set "current_dir=%%i"
set "target_pdf_js_dir=%current_dir%\libs\ktem\ktem\assets\prebuilt\%pdf_js_dist_name%"

REM Create the target directory if it does not exist (including parent folders)
if not exist "%target_pdf_js_dir%" (
    echo Creating directory %target_pdf_js_dir%
    mkdir "%target_pdf_js_dir%"
) else (
    echo Directory already exists: %target_pdf_js_dir%
    GOTO :eof
)

REM Download the ZIP file using PowerShell
set "zip_file=%temp%\downloaded.zip"
echo Downloading %url% to %zip_file%
powershell -Command "Invoke-WebRequest -Uri '%pdf_js_dist_url%' -OutFile '%zip_file%'"


REM Extract the ZIP file using PowerShell
echo Extracting %zip_file% to %dest_dir%
powershell -Command "Expand-Archive -Path '%zip_file%' -DestinationPath '%target_pdf_js_dir%'"

REM Clean up the downloaded ZIP file
del "%zip_file%"
echo Download and extraction completed successfully.

goto :eof

:setup_local_model
python "%CD%\scripts\serve_local.py"
GOTO :eof

:launch_ui
:: Workaround for diskcache path with folder start with .
SET THEFLOW_TEMP_PATH=flow_tmp
SET PDFJS_PREBUILT_DIR=%target_pdf_js_dir%
ECHO Starting Kotaemon UI... (prebuilt PDF.js is at %PDFJS_PREBUILT_DIR%)
CALL python -Xutf8 "%CD%\app.py" || ( ECHO. && ECHO Will exit now... && GOTO :exit_func_with_error )
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
