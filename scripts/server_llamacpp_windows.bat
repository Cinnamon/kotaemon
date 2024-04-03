@echo off

@rem main code execution

call :print_highlight "Starting inference server for llama-cpp"

cd /D "%~dp0\.."
echo "Change the current directory to: %cd%"

call :path_sanity_check
call :deactivate_environment

@rem config
set ENV_NAME=llama-cpp-python-server
set PYTHON_VERSION=3.10
set CONDA_ROOT_PREFIX=%cd%\install_dir\conda
set INSTALL_ENV_DIR=%cd%\install_dir\server_envs\%ENV_NAME%

echo "Python version: %PYTHON_VERSION%"
echo "Conda prefix: %CONDA_ROOT_PREFIX%"
echo "Environment path: %INSTALL_ENV_DIR%"

@rem handle conda environment
call :check_conda_existence
call :create_conda_environment
call :isolate_environment
call :activate_environment

@rem install dependencies
@rem ver 0.2.56 produces segment error for /embeddings on MacOS
call python -m pip install llama-cpp-python[server]==0.2.55

@REM @rem start the server with passed params
call python -m llama_cpp.server %*
call conda deactivate

goto :end
@rem the end of main code execution


@rem below are the functions used in the above execution


:print_highlight
echo.
echo ******************************************************
echo %~1
echo ******************************************************
echo.
goto :eof


:path_sanity_check
echo "Path sanity checking"
echo "%cd%"| findstr /C:" " >nul ^
&& (call :print_highlight "This script relies on Miniconda which can not be silently installed under a path with spaces." ^
&& goto :end)
goto :eof


:deactivate_environment
echo "Deactivate existing environment(s)"
(call conda deactivate && call conda deactivate && call conda deactivate) 2>nul
goto :eof


:check_conda_existence
echo "Check for conda existence"
set conda_exists=F

@rem figure out whether conda exists
call "%CONDA_ROOT_PREFIX%\_conda.exe" --version >nul 2>&1
if "%ERRORLEVEL%" EQU "0" set conda_exists=T

@rem verify if conda is installed by the main app, if not then raise error
if "%conda_exists%" == "F" (
	call :print_highlight "conda is not installed, seems like the app wasn't installed correctly."
    goto :end
)
goto :eof


:create_conda_environment
@rem create the environment if needed
if not exist "%INSTALL_ENV_DIR%" (
    echo "Create conda environment"
	call "%CONDA_ROOT_PREFIX%\_conda.exe" create ^
        --no-shortcuts -y -k --prefix "%INSTALL_ENV_DIR%" python="%PYTHON_VERSION%" || ^
    ( echo. && call :print_highlight "Conda environment creation failed." && goto :end )
)

@rem check if conda environment was actually created
if not exist "%INSTALL_ENV_DIR%\python.exe" (
    call :print_highlight "Conda environment was not correctly created."
    goto :end
)
goto :eof


:isolate_environment
echo "Isolate environment"
set PYTHONNOUSERSITE=1
set PYTHONPATH=
set PYTHONHOME=
goto :eof


:activate_environment
echo "Activate conda environment"
call "%CONDA_ROOT_PREFIX%\condabin\conda.bat" activate "%INSTALL_ENV_DIR%" || ^
( echo. && call :print_highlight "Miniconda hook not found." && goto :end )
goto :eof


:end
