# kotaemon

An open-source tool for chatting with your documents. Built with both end users and
developers in mind.

https://github.com/Cinnamon/kotaemon/assets/25688648/815ecf68-3a02-4914-a0dd-3f8ec7e75cd9

[Source Code](https://github.com/Cinnamon/kotaemon) |
[Live Demo](https://huggingface.co/spaces/lone17/kotaemon-app)

[User Guide](https://cinnamon.github.io/kotaemon/) |
[Developer Guide](https://cinnamon.github.io/kotaemon/development/) |
[Feedback](https://github.com/Cinnamon/kotaemon/issues)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-31013/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![built with Codeium](https://codeium.com/badges/main)](https://codeium.com)

This project would like to appeal to both end users who want to do QA on their
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

```yml
+----------------------------------------------------------------------------+
| End users: Those who use apps built with `kotaemon`.                       |
| (You use an app like the one in the demo above)                            |
|     +----------------------------------------------------------------+     |
|     | Developers: Those who built with `kotaemon`.                   |     |
|     | (You have `import kotaemon` somewhere in your project)         |     |
|     |     +----------------------------------------------------+     |     |
|     |     | Contributors: Those who make `kotaemon` better.    |     |     |
|     |     | (You make PR to this repo)                         |     |     |
|     |     +----------------------------------------------------+     |     |
|     +----------------------------------------------------------------+     |
+----------------------------------------------------------------------------+
```

This repository is under active development. Feedback, issues, and PRs are highly
appreciated. Your input is valuable as it helps us persuade our business guys to support
open source.

## Installation

### For end users

This document is intended for developers. If you just want to install and use the app as
it, please follow the [User Guide](https://cinnamon.github.io/kotaemon/).

### For developers

```shell
# Create a environment
python -m venv kotaemon-env

# Activate the environment
source kotaemon-env/bin/activate

# Install the package
pip install git+https://github.com/Cinnamon/kotaemon.git
```

### For Contributors

```shell
# Clone the repo
git clone git@github.com:Cinnamon/kotaemon.git

# Create a environment
python -m venv kotaemon-env

# Activate the environment
source kotaemon-env/bin/activate
cd kotaemon

# Install the package in editable mode
pip install -e "libs/kotaemon[all]"
pip install -e "libs/ktem"
pip install -e "."

# Setup pre-commit
pre-commit install
```

## Creating your application

In order to create your own application, you need to prepare these files:

- `flowsettings.py`
- `app.py`
- `.env` (Optional)

### `flowsettings.py`

This file contains the configuration of your application. You can use the example
[here](https://github.com/Cinnamon/kotaemon/blob/main/libs/ktem/flowsettings.py) as the
starting point.

### `app.py`

This file is where you create your Gradio app object. This can be as simple as:

```python
from ktem.main import App

app = App()
demo = app.make()
demo.launch()
```

### `.env` (Optional)

This file provides another way to configure your models and credentials.

<details markdown>

<summary>Configure model via the .env file</summary>

Alternatively, you can configure the models via the `.env` file with the information needed to connect to the LLMs. This file is located in
the folder of the application. If you don't see it, you can create one.

Currently, the following providers are supported:

#### OpenAI

In the `.env` file, set the `OPENAI_API_KEY` variable with your OpenAI API key in order
to enable access to OpenAI's models. There are other variables that can be modified,
please feel free to edit them to fit your case. Otherwise, the default parameter should
work for most people.

```shell
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_API_KEY=<your OpenAI API key here>
OPENAI_CHAT_MODEL=gpt-3.5-turbo
OPENAI_EMBEDDINGS_MODEL=text-embedding-ada-002
```

#### Azure OpenAI

For OpenAI models via Azure platform, you need to provide your Azure endpoint and API
key. Your might also need to provide your developments' name for the chat model and the
embedding model depending on how you set up Azure development.

```shell
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-35-turbo
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=text-embedding-ada-002
```

#### Local models

- Pros:
- Privacy. Your documents will be stored and process locally.
- Choices. There are a wide range of LLMs in terms of size, domain, language to choose
  from.
- Cost. It's free.
- Cons:
- Quality. Local models are much smaller and thus have lower generative quality than
  paid APIs.
- Speed. Local models are deployed using your machine so the processing speed is
  limited by your hardware.

##### Find and download a LLM

You can search and download a LLM to be ran locally from the [Hugging Face
Hub](https://huggingface.co/models). Currently, these model formats are supported:

- GGUF

You should choose a model whose size is less than your device's memory and should leave
about 2 GB. For example, if you have 16 GB of RAM in total, of which 12 GB is available,
then you should choose a model that takes up at most 10 GB of RAM. Bigger models tend to
give better generation but also take more processing time.

Here are some recommendations and their size in memory:

- [Qwen1.5-1.8B-Chat-GGUF](https://huggingface.co/Qwen/Qwen1.5-1.8B-Chat-GGUF/resolve/main/qwen1_5-1_8b-chat-q8_0.gguf?download=true):
  around 2 GB

##### Enable local models

To add a local model to the model pool, set the `LOCAL_MODEL` variable in the `.env`
file to the path of the model file.

```shell
LOCAL_MODEL=<full path to your model file>
```

Here is how to get the full path of your model file:

- On Windows 11: right click the file and select `Copy as Path`.
</details>

## Start your application

Simply run the following command:

```shell
python app.py
```

The app will be automatically launched in your browser.

![Chat tab](https://raw.githubusercontent.com/Cinnamon/kotaemon/main/docs/images/chat-tab.png)

## Customize your application

Please refer to the [Developer Guide](https://cinnamon.github.io/kotaemon/development/)
for more details.
