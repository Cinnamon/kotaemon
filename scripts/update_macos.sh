#!/bin/bash

# functions for better code organization
function check_path_for_spaces() {
    if [[ $PWD =~ \  ]]; then
        echo "The current workdir has whitespace which can lead to unintended behaviour. Please modify your path and continue later."
        exit 1
    fi
}

function activate_conda_env() {
    # deactivate the current env(s) to avoid conflicts
    { conda deactivate && conda deactivate && conda deactivate; } 2>/dev/null

    # check if conda env is broken (because of interruption during creation)
    if [ ! -f "$env_dir/bin/python" ]; then
        echo "Conda environment appears to be broken. You may need to remove $env_dir and run the installer again."
        exit 1
    fi

    source "$conda_root/etc/profile.d/conda.sh" # conda init
    conda activate "$env_dir" || {
        echo "Failed to activate environment. Please remove $env_dir and run the installer again"
        exit 1
    }
    echo "Activate conda environment at $CONDA_PREFIX"
}

function deactivate_conda_env() {
    # Conda deactivate if we are in the right env
    if [ "$CONDA_PREFIX" == "$env_dir" ]; then
        conda deactivate
        echo "Deactivate conda environment at $env_dir"
    fi
}

function update_latest() {
    current_version=$(pip list | awk '/kotaemon-app/ {print $2}')
    echo "Current version $current_version"

    if [ -f "pyproject.toml" ]; then
        echo "Source files detected. Please perform git pull manually."
        deactivate_environment
        exit 1
    else
        echo "Installing version: $app_version"
        # Work around for versioning control
        python -m pip install "git+https://github.com/Cinnamon/kotaemon.git@$app_version#subdirectory=libs/kotaemon"
        python -m pip install "git+https://github.com/Cinnamon/kotaemon.git@$app_version#subdirectory=libs/ktem"
        python -m pip install --no-deps git+https://github.com/Cinnamon/kotaemon.git@$app_version
        if [ $? -ne 0 ]; then
            echo
            echo "Update failed. You may need to run the update again."
            deactivate_environment
            exit 1
        fi
    fi
}

function print_highlight() {
    local message="${1}"
    echo "" && echo "******************************************************"
    echo $message
    echo "******************************************************" && echo ""
}

# Main script execution

# move two levels up from the dir where this script resides
cd "$(dirname "${BASH_SOURCE[0]}")" && cd ..

app_version="latest"
install_dir="$(pwd)/install_dir"
conda_root="${install_dir}/conda"
env_dir="${install_dir}/env"

check_path_for_spaces

print_highlight "Activating conda environment"
activate_conda_env

print_highlight "Updating Kotaemon to latest"
update_latest

deactivate_conda_env

read -p "Press enter to continue"
