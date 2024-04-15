# kotaemon

![demo](https://raw.githubusercontent.com/Cinnamon/kotaemon/main/docs/images/chat-demo.gif)

[Source Code](https://github.com/Cinnamon/kotaemon) |
[Demo](https://huggingface.co/spaces/lone17/kotaemon-app)

[User Guide](https://cinnamon.github.io/kotaemon/) |
[Developer Guide](https://cinnamon.github.io/kotaemon/development/) |
[Feedback](https://github.com/Cinnamon/kotaemon/issues)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-31013/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![built with Codeium](https://codeium.com/badges/main)](https://codeium.com)

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

## Setting up

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

Please refer to the [Developer Guide](https://cinnamon.github.io/kotaemon/development/)
for more details.
