<div align="center">

# kotaemon

A clean, customizable, open-source RAG UI designed for interacting with your documents. Ideally for both end users and developers.

![Preview](https://raw.githubusercontent.com/Cinnamon/kotaemon/main/docs/images/preview-graph.png)

[Live Demo](https://huggingface.co/spaces/cin-model/kotaemon-demo) |
[User Guide](https://cinnamon.github.io/kotaemon/) |
[Developer Guide](https://cinnamon.github.io/kotaemon/development/) |
[Feedback](https://github.com/Cinnamon/kotaemon/issues)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-31013/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
<a href='https://github.com/cinnamon/kotaemon/pkgs/container/kotaemon'><img src="https://img.shields.io/badge/docker_pull-kotaemon:latest-blue" alt="docker pull ghcr.io/cinnamon/kotaemon:latest"></a>
![download](https://img.shields.io/github/downloads/Cinnamon/kotaemon/total.svg?label=downloads&color=blue)
[![built with Codeium](https://codeium.com/badges/main)](https://codeium.com)
<a href='https://huggingface.co/spaces/cin-model/kotaemon-demo'><img src='https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue'></a>
<a href="https://hellogithub.com/en/repository/d3141471a0244d5798bc654982b263eb" target="_blank"><img src="https://abroad.hellogithub.com/v1/widgets/recommend.svg?rid=f3536f6e521043c3b300175d454fd346&claim_uid=RLiD9UZ1rEHNaMf&theme=small" alt="Featured｜HelloGitHub" /></a>

</div>
<br>

## <div align="center">🤖 Introduction</div>

This project serves as a functional RAG UI for both end users who want to do QA on their
documents and developers who want to build their own RAG pipeline.

- **For end users/non-tech-savvy users**:
  - Provides a clean and minimalistic UI for RAG-based question answering on your private documents.
  - Offer clear citations to verify LLM answer correctness, with direct highlighting on source PDFs for a pleasant browsing experience.
  - Supports various LLM API providers (OpenAI, AzureOpenAI, Cohere, Groq, etc.) and local LLMs (via `ollama` and `llama-cpp-python`).
  - Include easy installation scripts for hassle-free setup.
- **For developers/researchers**:
  - Provides a clean yet functional baseline that can be directly used in your work or a quick demo/personal project.
  - Offer a framework for building your own RAG-based document QA pipeline.
  - Allows customization and visualization of your RAG pipeline with the provided UI (built with <a href='https://github.com/gradio-app/gradio'>Gradio <img src='https://img.shields.io/github/stars/gradio-app/gradio'></a>).
  - Includes a theme for those using Gradio for development: [kotaemon-gradio-theme](https://github.com/lone17/kotaemon-gradio-theme).

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

\*_This repository is under active development. Feedback, issues, and PRs are highly appreciated._
<br>

## <div align="center">🚀 Key Features</div>

- **Host your own document QA (RAG) web-UI**. Support multi-user login, organize your files in private / public collections, collaborate and share your favorite chat with others.

- **Organize your LLM & Embedding models**. Support both local LLMs & popular API providers (OpenAI, Azure, Ollama, Groq).

- **Hybrid RAG pipeline**. Sane default RAG pipeline with hybrid (full-text & vector) retriever + re-ranking to ensure best retrieval quality.

- **Multi-modal QA support**. Perform Question Answering on multiple documents with figures & tables support. Support multi-modal document parsing (selectable options on UI).

- **Advance citations with document preview**. By default the system will provide detailed citations to ensure the correctness of LLM answers. View your citations (incl. relevant score) directly in the _in-browser PDF viewer_ with highlights. Warning when retrieval pipeline return low relevant articles.

- **Support complex reasoning methods**. Use question decomposition to answer your complex / multi-hop question. Support agent-based reasoning with ReAct, ReWOO and other agents.

- **Configurable settings UI**. You can adjust most important aspects of retrieval & generation process on the UI (incl. prompts).

- **Extensible**. Being built on Gradio, you are free to customize / add any UI elements as you like. Also, we aim to support multiple strategies for document indexing & retrieval. `GraphRAG` indexing pipeline is provided as an example.

![Preview](https://raw.githubusercontent.com/Cinnamon/kotaemon/main/docs/images/preview.png)
<br>

## <div align="center">⚙️ Installation</div>

### For end users

Please follow the non-technical [User Guide](https://cinnamon.github.io/kotaemon/) to setup and run Kotaemon as a normal application.
Use the most recent release `.zip` file to include latest features and bug-fixes.

### For developers

#### 📦 With Docker (recommended)

- Use this command to launch the server

  ```
  docker run \
  -e GRADIO_SERVER_NAME=0.0.0.0 \
  -e GRADIO_SERVER_PORT=7860 \
  -p 7860:7860 -it --rm \
  ghcr.io/cinnamon/kotaemon:latest
  ```

- Navigate to `http://localhost:7860/` to access the web UI.

#### 🧩 Without Docker

- Clone and install the required packages on a fresh python environment.

  ```shell
  # optional (setup env)
  conda create -n kotaemon python=3.10
  conda activate kotaemon

  # clone this repo
  git clone https://github.com/Cinnamon/kotaemon
  cd kotaemon

  pip install -e "libs/kotaemon[all]"
  pip install -e "libs/ktem"
  ```

- View and edit your environment variables (API keys, end-points) in `.env`

- _(Optional)_ To enable in-browser PDF_JS viewer:

  - Download [PDF_JS_DIST](https://github.com/mozilla/pdf.js/releases/download/v4.0.379/pdfjs-4.0.379-dist.zip),
  - Create a folder named `prebuilt` (if yet existed) in `libs/ktem/ktem/assets/`
  - Extract the downloaded files into `libs/ktem/ktem/assets/prebuilt`

    <img src="https://github.com/user-attachments/assets/e47e6b02-b026-416f-b63e-6ac565994711" alt="pdf-setup">

- Start the web server:

  ```shell
  python app.py
  ```

- The app will be automatically launched in your browser.

- First time log in: **username:** `admin` | **password:** `admin` (You can setup additional users directly on the UI later)

  ![image](https://github.com/user-attachments/assets/ee374d3e-9c99-4880-a928-6b0ead4684a4)

- Voilà!

  ![Chat tab](https://github.com/user-attachments/assets/6a64e5f8-1349-4131-9b4d-24808420a28c)

<br>

## <div align="center">🏠 Setup local models (for local/private RAG)</div>

See [Local model setup](docs/local_model.md)

<br>

## <div align="center">🎨 Customize your application</div>

By default, all application data are stored in `./ktem_app_data` folder. You can backup or copy this folder to move your installation to a new machine.

For advanced users or in specific use-cases, you can customize these files: `flowsettings.py`, `.env`

- **`flowsettings.py`**

  - This file contains the configuration of your application. You can use the example [here](flowsettings.py) as the starting point.

    <details>

    <summary>Notable settings</summary>

    ```
    # setup your preferred document store (with full-text search capabilities)
    KH_DOCSTORE=(Elasticsearch | LanceDB | SimpleFileDocumentStore)

    # setup your preferred vectorstore (for vector-based search)
    KH_VECTORSTORE=(ChromaDB | LanceDB | InMemory)

    # Enable / disable multimodal QA
    KH_REASONINGS_USE_MULTIMODAL=True

    # Setup your new reasoning pipeline or modify existing one.
    KH_REASONINGS = [
        "ktem.reasoning.simple.FullQAPipeline",
        "ktem.reasoning.simple.FullDecomposeQAPipeline",
        "ktem.reasoning.react.ReactAgentPipeline",
        "ktem.reasoning.rewoo.RewooAgentPipeline",
    ]
    )
    ```

  </details>

- **`.env`**

  - This file provides another way to configure your models and credentials.

        <details markdown>

        <summary>Configure model via the .env file</summary>

        Alternatively, you can configure the models via the `.env` file with the information needed to connect to the LLMs. This file is located in
        the folder of the application. If you don't see it, you can create one.

        Currently, the following providers are supported:

        ### OpenAI

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

        ### Azure OpenAI

        - For OpenAI models via Azure platform, you need to provide your Azure endpoint and API key. Your might also need to provide your developments' name for the chat model and the embedding model depending on how you set up Azure development.

          ```shell
          AZURE_OPENAI_ENDPOINT=
          AZURE_OPENAI_API_KEY=
          OPENAI_API_VERSION=2024-02-15-preview
          AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-35-turbo
          AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=text-embedding-ada-002
          ```

        ### Local models

        #### Using ollama OpenAI compatible server

        - Install [ollama](https://github.com/ollama/ollama) and start the application.

        - Pull your model (e.g):

          ```
          ollama pull llama3.1:8b
          ollama pull nomic-embed-text
          ```

        - Set the model names on web UI and make it as default.

          ![Models](https://raw.githubusercontent.com/Cinnamon/kotaemon/main/docs/images/models.png)

        #### Using GGUF with llama-cpp-python

        - You can search and download a LLM to be ran locally from the [Hugging Face Hub](https://huggingface.co/models). Currently, these model formats are supported:

          - GGUF

        - You should choose a model whose size is less than your device's memory and should leave
        about 2 GB. For example, if you have 16 GB of RAM in total, of which 12 GB is available,
        then you should choose a model that takes up at most 10 GB of RAM. Bigger models tend to
        give better generation but also take more processing time.

        - Here are some recommendations and their size in memory:

          - [Qwen1.5-1.8B-Chat-GGUF](https://huggingface.co/Qwen/Qwen1.5-1.8B-Chat-GGUF/resolve/main/qwen1_5-1_8b-chat-q8_0.gguf?download=true):
          around 2 GB

          - Add a new LlamaCpp model with the provided model name on the web uI.

        </details>

    <br>

## <div align="center">👤 Adding your own RAG pipeline</div>

#### Custom reasoning pipeline

- First, check the default pipeline implementation in
  [here](libs/ktem/ktem/reasoning/simple.py). You can make quick adjustment to how the default QA pipeline work.

- Next, if you feel comfortable adding new pipeline, add new `.py` implementation in `libs/ktem/ktem/reasoning/` and later include it in `flowssettings` to enable it on the UI.

#### Custom indexing pipeline

- Check sample implementation in `libs/ktem/ktem/index/file/graph`

- _(more instruction WIP)._

<br>

## <div align="center">💻 Developer guide</div>

Please refer to the [Developer Guide](https://cinnamon.github.io/kotaemon/development/)
for more details.

<br>

## <div align="center">🫶 Contributors</div>

We truly value your feedback! Our projects, Kotaemon, thrive thanks to the incredible support from our community.

<a href="https://github.com/Cinnamon/kotaemon/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Cinnamon/kotaemon" />
</a>

<br>

## <div align="center">⭐ Star History</div>

<a href="https://star-history.com/#Cinnamon/kotaemon&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=Cinnamon/kotaemon&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=Cinnamon/kotaemon&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=Cinnamon/kotaemon&type=Date" />
 </picture>
</a>
