#!/bin/bash

# functions for better code organization
function check_path_for_spaces() {
    if [[ $PWD =~ \  ]]; then
        echo "The current workdir has whitespace which can lead to unintended behaviour. Please modify your path and continue later."
        exit 1
    fi
}

function install_miniconda() {
    # Miniconda installer is limited to two main architectures: x86_64 and arm64
    local sys_arch=$(uname -m)
    case "${sys_arch}" in
    x86_64*) sys_arch="x86_64" ;;
    arm64*) sys_arch="aarch64" ;;
    aarch64*) sys_arch="aarch64" ;;
    *) {
        echo "Unknown system architecture: ${sys_arch}! This script runs only on x86_64 or arm64"
        exit 1
    } ;;
    esac

    # if miniconda has not been installed, download and install it
    if ! "${conda_root}/bin/conda" --version &>/dev/null; then
        if [ ! -d "$install_dir/miniconda_installer.sh" ]; then
            echo "Downloading Miniconda from $miniconda_url"
            local miniconda_url="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-${sys_arch}.sh"

            mkdir -p "$install_dir"
            curl -Lk "$miniconda_url" >"$install_dir/miniconda_installer.sh"
        fi

        echo "Installing Miniconda to $conda_root"
        chmod u+x "$install_dir/miniconda_installer.sh"
        bash "$install_dir/miniconda_installer.sh" -b -p "$conda_root"
        rm -rf "$install_dir/miniconda_installer.sh"
    fi
    echo "Miniconda is installed at $conda_root"

    # test conda
    echo "Conda version: "
    "$conda_root/bin/conda" --version || {
        echo "Conda not found. Will exit now..."
        exit 1
    }
}

function create_conda_env() {
    local python_version="${1}"

    if [ ! -d "${env_dir}" ]; then
        echo "Creating conda environment with python=$python_version in $env_dir"
        "${conda_root}/bin/conda" create -y -k --prefix "$env_dir" python="$python_version" || {
            echo "Failed to create conda environment."
            echo "Will delete the ${env_dir} (if exist) and exit now..."
            rm -rf $env_dir
            exit 1
        }
    else
        echo "Conda environment exists at $env_dir"
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
        echo "Failed to activate environment. Please remove $env_dir and run the installer again."
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

function install_dependencies() {
    if pip list 2>/dev/null | grep -q "kotaemon"; then
        echo "Requirements are already installed"
    else
        local kotaemon_root="$(pwd)/libs/kotaemon"
        local ktem_root="$(pwd)/libs/ktem/"

        if [ -f "$(pwd)/VERSION" ]; then
            local app_version=$(<"$(pwd)/VERSION")
        else
            local app_version="latest"
        fi

        if [ -f "pyproject.toml" ]; then
            echo "Found pyproject.toml. Installing from source"
            echo "" && echo "Installing libs/kotaemon"
            python -m pip install -e "$kotaemon_root"
            echo "" && echo "Installing libs/ktem"
            python -m pip install -e "$ktem_root"

            python -m pip install --no-deps -e .
        else
            echo "Installing Kotaemon $app_version"
            # Work around for versioning control
            python -m pip install "git+https://github.com/Cinnamon/kotaemon.git@$app_version#subdirectory=libs/kotaemon"
            python -m pip install "git+https://github.com/Cinnamon/kotaemon.git@$app_version#subdirectory=libs/ktem"
            python -m pip install --no-deps "git+https://github.com/Cinnamon/kotaemon.git@$app_version"
        fi

        if ! pip list 2>/dev/null | grep -q "kotaemon"; then
            echo "Installation failed. You may need to run the installer again."
            deactivate_conda_env
            exit 1
        else
            print_highlight "Install finished successfully. Clear cache..."
            conda clean --all -y
            python -m pip cache purge

            print_highlight "Do you want to launch the web UI? [Y/N]"
            read -p "Input> " launch
            local launch=${launch,,}
            if [[ "$launch" != "yes" && "$launch" != "y" && "$launch" != "true" ]]; then
                echo "Will exit now..."
                deactivate_conda_env
                echo "Please run the installer again to launch the UI."
                exit 0
            fi
        fi
    fi
}

function setup_local_model() {
    python $(pwd)/scripts/serve_local.py
}

function download_and_unzip() {
    local url=$1
    local dest_dir=$2

    # Check if the destination directory exists, create if it doesn't
    if [ -d "$dest_dir" ]; then
        echo "Destination directory $dest_dir already exists. Skipping download."
        return
    fi

    mkdir -p "$dest_dir"

    # Download the ZIP file
    local zip_file="${dest_dir}/downloaded.zip"
    echo "Downloading $url to $zip_file"
    curl -L -o "$zip_file" "$url"

    # Unzip the file to the destination directory
    echo "Unzipping $zip_file to $dest_dir"
    unzip -o "$zip_file" -d "$dest_dir"

    # Clean up the downloaded ZIP file
    rm "$zip_file"
    echo "Download and unzip completed successfully."
}

function launch_ui() {
    local pdfjs_prebuilt_dir=$1
    PDFJS_PREBUILT_DIR="$pdfjs_prebuilt_dir" python $(pwd)/app.py || {
        echo "" && echo "Will exit now..."
        exit 1
    }
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

install_dir="$(pwd)/install_dir"
conda_root="${install_dir}/conda"
env_dir="${install_dir}/env"
python_version="3.10"

pdf_js_version="4.0.379"
pdf_js_dist_name="pdfjs-${pdf_js_version}-dist"
pdf_js_dist_url="https://github.com/mozilla/pdf.js/releases/download/v${pdf_js_version}/${pdf_js_dist_name}.zip"
target_pdf_js_dir="$(pwd)/libs/ktem/ktem/assets/prebuilt/${pdf_js_dist_name}"

check_path_for_spaces

print_highlight "Setting up Miniconda"
install_miniconda

print_highlight "Creating conda environment"
create_conda_env "$python_version"
activate_conda_env

print_highlight "Installing requirements"
install_dependencies

print_highlight "Downloading and unzipping PDF.js"
download_and_unzip $pdf_js_dist_url $target_pdf_js_dir

print_highlight "Setting up a local model"
setup_local_model

print_highlight "Launching Kotaemon in your browser, please wait..."
launch_ui $target_pdf_js_dir

deactivate_conda_env

read -p "Press enter to continue"
