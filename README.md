# kotaemon

[Documentation](https://cinnamon.github.io/kotaemon/)

Build and use local RAG-based Question Answering (QA) applications.

This repository would like to appeal to both end users who want to do QA on their
documents and developers who want to build their own QA pipeline.

- For end users:
  - A local Question Answering UI for RAG-based QA.
  - Supports LLM API providers (OpenAI, AzureOpenAI, Cohere, etc) and local LLMs
    (currently only GGUF format is supported via `llama-cpp-python`).
  - Easy installation scripts, no environment setup required.
- For developers:
  - A framework for building your own RAG-based QA pipeline.
  - See your RAG pipeline in action with the provided UI (built with Gradio).
  - Share your pipeline so that others can use it.

This repository is under active development. Feedback, issues, and PRs are highly
appreciated. Your input is valuable as it helps us persuade our business guys to support
open source.

## Installation

### Manual installation

- Clone the repo

  ```shell
  git clone git@github.com:Cinnamon/kotaemon.git
  cd kotaemon
  ```

- Install the environment

  - Create a conda environment (python >= 3.10 is recommended)

    ```shell
    conda create -n kotaemon python=3.10
    conda activate kotaemon

    # install dependencies
    cd libs/kotaemon
    pip install -e ".[all]"
    ```

  - Or run the installer (one of the `scripts/run_*` scripts depends on your OS), then
    you will have all the dependencies installed as a conda environment at
    `install_dir/env`.

    ```shell
    conda activate install_dir/env
    ```

- Pre-commit

  ```shell
  pre-commit install
  ```

- Test

  ```shell
  pytest tests
  ```

### From installation scripts

1. Clone the repository.
2. Navigate to the `scripts` folder and start an installer that matches your OS:
   - Linux: `run_linux.sh`
   - Windows: `run_windows.bat`
   - macOS: `run_macos.sh`
3. After the installation, the installer will ask to launch the ktem's UI,answer to continue.
4. If launched, the application will be available at `http://localhost:7860/`.
5. The conda environment is located in the `install_dir/env` folder.

Here is the setup and update strategy:

- **Run the `run_*` script**: This setup environment, including downloading Miniconda (in case Conda is not available in your machine) and installing necessary dependencies in `install_dir` folder.
- **Launch the UI**: To launch the ktem's UI after initial setup or any changes, simply run `run_*` script again.
- **Reinstall dependencies**: Simply delete the `install_dir/env` folder and run `run_*`
  script again. The script will recreate the folder with fresh dependencies.
