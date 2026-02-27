#!/bin/bash

# Kotaemon UV Installation Script
# This script provides a faster and simpler alternative to conda-based installation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'  
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function print_header() {
    echo -e "\n${BLUE}======================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================================${NC}\n"
}

function print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

function print_error() {
    echo -e "${RED}✗ $1${NC}"
}

function check_path_for_spaces() {
    if [[ $PWD =~ \  ]]; then
        print_error "The current workdir has whitespace which can lead to unintended behaviour. Please modify your path and continue later."
        exit 1
    fi
}

function check_python_version() {
    print_success "uv will automatically manage Python 3.10 - no manual Python installation needed!"
}

function install_uv() {
    if command -v uv &> /dev/null; then
        print_success "uv is already installed"
        return 0
    fi
    
    print_header "Installing uv package manager"
    
    if command -v curl &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget &> /dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        print_error "Neither curl nor wget is available. Please install one of them."
        exit 1
    fi
    
    # Add uv to PATH for current session
    export PATH="$HOME/.local/bin:$PATH"
    
    if command -v uv &> /dev/null; then
        print_success "uv installed successfully"
    else
        print_error "uv installation failed"
        exit 1
    fi
}

function setup_environment() {
    print_header "Setting up Python environment with uv"
    
    # Create virtual environment with Python 3.10 (uv will download Python if needed)
    if [[ ! -d ".venv" ]]; then
        print_success "Creating virtual environment with Python 3.10 (uv will download if needed)..."
        uv venv --python 3.10
        print_success "Created virtual environment"
    else
        print_warning "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    print_success "Activated virtual environment"
}

function install_dependencies() {
    print_header "Installing dependencies"
    
    # Use the exact same approach as conda scripts for compatibility
    print_success "Installing kotaemon with exact dependency resolution..."
    
    # Install in the exact same order as the original conda script
    uv pip install -e "libs/kotaemon[all]"
    uv pip install -e "libs/ktem"
    
    # Fix known version conflicts mentioned in the README
    print_success "Resolving known version conflicts..."
    uv pip uninstall hnswlib chroma-hnswlib -y 2>/dev/null || true
    uv pip install chroma-hnswlib
    
    print_success "Dependencies installed successfully"
}

function setup_pdfjs() {
    print_header "Setting up PDF.js viewer"
    
    local pdfjs_dir="libs/ktem/ktem/assets/prebuilt/pdfjs-4.0.379-dist"
    
    if [[ -d "$pdfjs_dir" ]]; then
        print_warning "PDF.js already exists, skipping download"
        return 0
    fi
    
    if [[ -f "scripts/download_pdfjs.sh" ]]; then
        bash scripts/download_pdfjs.sh "$pdfjs_dir"
        print_success "PDF.js setup completed"
    else
        print_warning "PDF.js download script not found. You may need to set this up manually."
    fi
}

function setup_env_file() {
    print_header "Setting up environment configuration"
    
    if [[ ! -f ".env" && -f ".env.example" ]]; then
        cp .env.example .env
        print_success "Created .env file from template"
        print_warning "Please edit .env file to configure your API keys"
    elif [[ -f ".env" ]]; then
        print_warning ".env file already exists"
    else
        print_warning "No .env.example found. You may need to configure environment variables manually."
    fi
}

function launch_app() {
    print_header "Launching Kotaemon"
    
    print_success "Starting the application..."
    print_warning "The app will be automatically launched in your browser"
    print_warning "Default username and password are both 'admin'"
    
    # Set PDF.js environment variable if directory exists
    local pdfjs_dir="libs/ktem/ktem/assets/prebuilt/pdfjs-4.0.379-dist"
    if [[ -d "$pdfjs_dir" ]]; then
        export PDFJS_PREBUILT_DIR="$pdfjs_dir"
    fi
    
    python app.py
}

function main() {
    print_header "Kotaemon UV-based Installation"
    
    # Move to project root
    cd "$(dirname "${BASH_SOURCE[0]}")" && cd ..
    
    check_path_for_spaces
    check_python_version
    install_uv
    setup_environment
    install_dependencies
    setup_pdfjs
    setup_env_file
    
    print_success "Installation completed successfully!"
    echo
    print_warning "To launch the application in the future, run:"
    echo -e "  ${BLUE}cd $(pwd)${NC}"
    echo -e "  ${BLUE}source .venv/bin/activate${NC}"
    echo -e "  ${BLUE}python app.py${NC}"
    echo
    
    read -p "Do you want to launch the application now? [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        launch_app
    else
        print_success "You can launch the application later using the commands above."
    fi
}

# Run main function
main "$@"