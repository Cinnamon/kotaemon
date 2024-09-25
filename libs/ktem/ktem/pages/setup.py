import json

import gradio as gr
import requests
from ktem.app import BasePage
from ktem.embeddings.manager import embedding_models_manager as embeddings
from ktem.llms.manager import llms
from theflow.settings import settings as flowsettings

KH_DEMO_MODE = getattr(flowsettings, "KH_DEMO_MODE", False)
DEFAULT_OLLAMA_URL = "http://localhost:11434/api"


DEMO_MESSAGE = (
    "This is a public space. Please use the "
    '"Duplicate Space" function on the top right '
    "corner to setup your own space."
)


def pull_model(name: str, stream: bool = True):
    payload = {"name": name}
    headers = {"Content-Type": "application/json"}

    response = requests.post(
        DEFAULT_OLLAMA_URL + "/pull", json=payload, headers=headers, stream=stream
    )

    # Check if the request was successful
    response.raise_for_status()

    if stream:
        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode("utf-8"))
                yield data
                if data.get("status") == "success":
                    break
    else:
        data = response.json()

    return data


class SetupPage(BasePage):

    public_events = ["onFirstSetupComplete"]

    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        gr.Markdown(f"# Welcome to {self._app.app_name} first setup!")
        self.radio_model = gr.Radio(
            [
                ("Cohere API (*free registration* available) - recommended", "cohere"),
                ("OpenAI API (for more advance models)", "openai"),
                ("Local LLM (for completely *private RAG*)", "ollama"),
            ],
            label="Select your model provider",
            value="cohere",
            info=(
                "Note: You can change this later. "
                "If you are not sure, go with the first option "
                "which fits most normal users."
            ),
            interactive=True,
        )

        with gr.Column(visible=False) as self.openai_option:
            gr.Markdown(
                (
                    "#### OpenAI API Key\n\n"
                    "(create at https://platform.openai.com/api-keys)"
                )
            )
            self.openai_api_key = gr.Textbox(
                show_label=False, placeholder="OpenAI API Key"
            )

        with gr.Column(visible=True) as self.cohere_option:
            gr.Markdown(
                (
                    "#### Cohere API Key\n\n"
                    "(register your free API key "
                    "at https://dashboard.cohere.com/api-keys)"
                )
            )
            self.cohere_api_key = gr.Textbox(
                show_label=False, placeholder="Cohere API Key"
            )

        with gr.Column(visible=False) as self.ollama_option:
            gr.Markdown(
                (
                    "#### Setup Ollama\n\n"
                    "Download and install Ollama from "
                    "https://ollama.com/"
                )
            )

        self.setup_log = gr.HTML(
            show_label=False,
        )

        with gr.Row():
            self.btn_finish = gr.Button("Proceed", variant="primary")
            self.btn_skip = gr.Button(
                "I am an advance user. Skip this.", variant="stop"
            )

    def on_register_events(self):
        onFirstSetupComplete = gr.on(
            triggers=[
                self.btn_finish.click,
                self.cohere_api_key.submit,
                self.openai_api_key.submit,
            ],
            fn=self.update_model,
            inputs=[self.cohere_api_key, self.openai_api_key, self.radio_model],
            outputs=[self.setup_log],
            show_progress="hidden",
        )
        if not KH_DEMO_MODE:
            onSkipSetup = gr.on(
                triggers=[self.btn_skip.click],
                fn=lambda: None,
                inputs=[],
                show_progress="hidden",
                outputs=[self.radio_model],
            )

            for event in self._app.get_event("onFirstSetupComplete"):
                onSkipSetup = onSkipSetup.success(**event)

        onFirstSetupComplete = onFirstSetupComplete.success(
            fn=self.update_default_settings,
            inputs=[self.radio_model, self._app.settings_state],
            outputs=self._app.settings_state,
        )
        for event in self._app.get_event("onFirstSetupComplete"):
            onFirstSetupComplete = onFirstSetupComplete.success(**event)

        self.radio_model.change(
            fn=self.switch_options_view,
            inputs=[self.radio_model],
            show_progress="hidden",
            outputs=[self.cohere_option, self.openai_option, self.ollama_option],
        )

    def update_model(
        self,
        cohere_api_key,
        openai_api_key,
        radio_model_value,
    ):
        # skip if KH_DEMO_MODE
        if KH_DEMO_MODE:
            raise gr.Error(DEMO_MESSAGE)

        log_content = ""
        if not radio_model_value:
            gr.Info("Skip setup models.")
            yield gr.value(visible=False)
            return

        if radio_model_value == "cohere":
            if cohere_api_key:
                llms.update(
                    name="cohere",
                    spec={
                        "__type__": "kotaemon.llms.chats.LCCohereChat",
                        "model_name": "command-r-plus-08-2024",
                        "api_key": cohere_api_key,
                    },
                    default=True,
                )
                embeddings.update(
                    name="cohere",
                    spec={
                        "__type__": "kotaemon.embeddings.LCCohereEmbeddings",
                        "model": "embed-multilingual-v3.0",
                        "cohere_api_key": cohere_api_key,
                        "user_agent": "default",
                    },
                    default=True,
                )
        elif radio_model_value == "openai":
            if openai_api_key:
                llms.update(
                    name="openai",
                    spec={
                        "__type__": "kotaemon.llms.ChatOpenAI",
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-4o",
                        "api_key": openai_api_key,
                        "timeout": 20,
                    },
                    default=True,
                )
                embeddings.update(
                    name="openai",
                    spec={
                        "__type__": "kotaemon.embeddings.OpenAIEmbeddings",
                        "base_url": "https://api.openai.com/v1",
                        "model": "text-embedding-3-large",
                        "api_key": openai_api_key,
                        "timeout": 10,
                        "context_length": 8191,
                    },
                    default=True,
                )
        elif radio_model_value == "ollama":
            llms.update(
                name="ollama",
                spec={
                    "__type__": "kotaemon.llms.ChatOpenAI",
                    "base_url": "http://localhost:11434/v1/",
                    "model": "llama3.1:8b",
                    "api_key": "ollama",
                },
                default=True,
            )
            embeddings.update(
                name="ollama",
                spec={
                    "__type__": "kotaemon.embeddings.OpenAIEmbeddings",
                    "base_url": "http://localhost:11434/v1/",
                    "model": "nomic-embed-text",
                    "api_key": "ollama",
                },
                default=True,
            )

            # download required models through ollama
            llm_model_name = llms.get("ollama").model  # type: ignore
            emb_model_name = embeddings.get("ollama").model  # type: ignore

            try:
                for model_name in [emb_model_name, llm_model_name]:
                    log_content += f"- Downloading model `{model_name}` from Ollama<br>"
                    yield log_content

                    pre_download_log = log_content

                    for response in pull_model(model_name):
                        complete = response.get("completed", 0)
                        total = response.get("total", 0)
                        if complete > 0 and total > 0:
                            ratio = int(complete / total * 100)
                            log_content = (
                                pre_download_log
                                + f"- {response.get('status')}: {ratio}%<br>"
                            )
                        else:
                            if "pulling" not in response.get("status", ""):
                                log_content += f"- {response.get('status')}<br>"

                        yield log_content
            except Exception as e:
                log_content += (
                    "Make sure you have download and installed Ollama correctly."
                    f"Got error: {str(e)}"
                )
                yield log_content
                raise gr.Error("Failed to download model from Ollama.")

        # test models connection
        llm_output = emb_output = None

        # LLM model
        log_content += f"- Testing LLM model: {radio_model_value}<br>"
        yield log_content

        llm = llms.get(radio_model_value)  # type: ignore
        log_content += "- Sending a message `Hi`<br>"
        yield log_content
        try:
            llm_output = llm("Hi")
        except Exception as e:
            log_content += (
                f"<mark style='color: yellow; background: red'>- Connection failed. "
                f"Got error:\n {str(e)}</mark>"
            )

        if llm_output:
            log_content += (
                "<mark style='background: green; color: white'>- Connection success. "
                "</mark><br>"
            )
        yield log_content

        if llm_output:
            # embedding model
            log_content += f"- Testing Embedding model: {radio_model_value}<br>"
            yield log_content

            emb = embeddings.get(radio_model_value)
            assert emb, f"Embedding model {radio_model_value} not found."

            log_content += "- Sending a message `Hi`<br>"
            yield log_content
            try:
                emb_output = emb("Hi")
            except Exception as e:
                log_content += (
                    f"<mark style='color: yellow; background: red'>"
                    "- Connection failed. "
                    f"Got error:\n {str(e)}</mark>"
                )

            if emb_output:
                log_content += (
                    "<mark style='background: green; color: white'>"
                    "- Connection success. "
                    "</mark><br>"
                )
            yield log_content

        if llm_output and emb_output:
            gr.Info("Setup models completed successfully!")
        else:
            raise gr.Error(
                "Setup models failed. Please verify your connection and API key."
            )

    def update_default_settings(self, radio_model_value, default_settings):
        # revise default settings
        # reranking llm
        default_settings["index.options.1.reranking_llm"] = radio_model_value
        if radio_model_value == "ollama":
            default_settings["index.options.1.use_llm_reranking"] = False

        return default_settings

    def switch_options_view(self, radio_model_value):
        components_visible = [gr.update(visible=False) for _ in range(3)]

        values = ["cohere", "openai", "ollama", None]
        assert radio_model_value in values, f"Invalid value {radio_model_value}"

        if radio_model_value is not None:
            idx = values.index(radio_model_value)
            components_visible[idx] = gr.update(visible=True)

        return components_visible
