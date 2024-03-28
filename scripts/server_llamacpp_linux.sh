#!/bin/bash

# functions used in the main code execution
function print_highlight() {
    local message="${1}"
    echo "" && echo "******************************************************"
    echo $message
    echo "******************************************************" && echo ""
}

function path_sanity_check() {
    echo "Path sanity checking"
    if [[ $PWD =~ \  ]]; then
        print_highlight "This script relies on Miniconda which can't be silently installed under a path with spaces. Please run it from a path without spaces."
        exit 1
    fi
}

function deactivate_environment() {
    echo "Deactivate existing environment(s)"
    # deactivate existing conda envs as needed to avoid conflicts
    { conda deactivate && conda deactivate && conda deactivate; } 2>/dev/null
}

function check_conda_existence() {
    echo "Check for conda existence"
    conda_exists="F"

    # figure out whether conda exists
    if "$CONDA_ROOT_PREFIX/bin/conda" --version &>/dev/null; then conda_exists="T"; fi

    # verify if conda is installed by the main app, if not then raise error
    if [ "$conda_exists" == "F" ]; then
        # test the conda binary
        print_highlight "conda is not installed, seems like the app wasn't installed correctly."
        exit
    fi
}

function create_conda_environment() {
    # create the environment if needed
    if [ ! -e "$INSTALL_ENV_DIR" ]; then
        echo "Create conda environment"
        "$CONDA_ROOT_PREFIX/bin/conda" create -y -k --prefix "$INSTALL_ENV_DIR" python="$PYTHON_VERSION" || {
            echo && print_highlight "Conda environment creation failed." && exit 1
        }
    fi

    # check if conda environment was actually created
    if [ ! -e "$INSTALL_ENV_DIR/bin/python" ]; then
        print_highlight "Conda environment was not correctly created."
        exit 1
    fi
}

function isolate_environment() {
    echo "Isolate environment"
    export PYTHONNOUSERSITE=1
    unset PYTHONPATH
    unset PYTHONHOME
}

function activate_environment() {
    echo "Activate conda environment"
    source "$CONDA_ROOT_PREFIX/etc/profile.d/conda.sh" # otherwise conda complains about 'shell not initialized' (needed when running in a script)
    conda activate "$INSTALL_ENV_DIR"
}

# main code execution

cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo "Changed the current directory to: $(pwd)"

path_sanity_check
deactivate_environment

# config
ENV_NAME="llama-cpp-python-server"
PYTHON_VERSION="3.10"
CONDA_ROOT_PREFIX="$(pwd)/install_dir/conda"
INSTALL_ENV_DIR="$(pwd)/install_dir/server_envs/${ENV_NAME}"

check_conda_existence
create_conda_environment
isolate_environment
activate_environment

# install dependencies
# ver 0.2.56 produces segment error for /embeddings on MacOS
python -m pip install llama-cpp-python[server]==0.2.55

# start the server with passed params
python -m llama_cpp.server $@

conda deactivate
