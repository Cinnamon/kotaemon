import pickle
from datetime import datetime
from pathlib import Path

import gradio as gr
from theflow.storage import storage

from kotaemon.chatbot import ChatConversation
from kotaemon.contribs.promptui.base import get_component
from kotaemon.contribs.promptui.export import export
from kotaemon.contribs.promptui.ui.blocks import ChatBlock

from ..logs import ResultLog

USAGE_INSTRUCTION = """## How to use:

1. Set the desired parameters.
2. Click "New chat" to start a chat session with the supplied parameters. This
    set of parameters will persist until the end of the chat session. During an
    ongoing chat session, changing the parameters will not take any effect.
3. Chat and interact with the chat bot on the right panel. You can add any
    additional input (if any), and they will be supplied to the chatbot.
4. During chat, the log of the chat will show up in the "Output" tabs. This is
    empty by default, so if you want to show the log here, tell the AI developers
    to configure the UI settings.
5. When finishing chat, select your preference in the radio box. Click "End chat".
    This will save the chat log and the preference to disk.
6. To compare the result of different run, click "Export" to get an Excel
    spreadsheet summary of different run.

## Support:

In case of errors, you can:

- PromptUI instruction:
    https://github.com/Cinnamon/kotaemon/wiki/Utilities#prompt-engineering-ui
- Create bug fix and make PR at: https://github.com/Cinnamon/kotaemon
- Ping any of @john @tadashi @ian @jacky in Slack channel #llm-productization

## Contribute:

- Follow installation at: https://github.com/Cinnamon/kotaemon/
"""


def construct_chat_ui(
    config, func_new_chat, func_chat, func_end_chat, func_export_to_excel
) -> gr.Blocks:
    """Construct the prompt engineering UI for chat

    Args:
        config: the UI config
        func_new_chat: the function for starting a new chat session
        func_chat: the function for chatting interaction
        func_end_chat: the function for ending and saving the chat
        func_export_to_excel: the function to export the logs to excel

    Returns:
        the UI object
    """
    inputs, outputs, params = [], [], []
    for name, component_def in config.get("inputs", {}).items():
        if "params" not in component_def:
            component_def["params"] = {}
        component_def["params"]["interactive"] = True
        component = get_component(component_def)
        if hasattr(component, "label") and not component.label:  # type: ignore
            component.label = name  # type: ignore

        inputs.append(component)

    for name, component_def in config.get("params", {}).items():
        if "params" not in component_def:
            component_def["params"] = {}
        component_def["params"]["interactive"] = True
        component = get_component(component_def)
        if hasattr(component, "label") and not component.label:  # type: ignore
            component.label = name  # type: ignore

        params.append(component)

    for idx, component_def in enumerate(config.get("outputs", [])):
        if "params" not in component_def:
            component_def["params"] = {}
        component_def["params"]["interactive"] = False
        component = get_component(component_def)
        if hasattr(component, "label") and not component.label:  # type: ignore
            component.label = f"Output {idx}"  # type: ignore

        outputs.append(component)

    sess = gr.State(value=None)
    chatbot = gr.Chatbot(label="Chatbot", show_copy_button=True)
    chat = ChatBlock(
        func_chat, chatbot=chatbot, additional_inputs=[sess], additional_outputs=outputs
    )
    param_state = gr.Textbox(interactive=False)

    with gr.Blocks(analytics_enabled=False, title="Welcome to PromptUI") as demo:
        sess.render()
        with gr.Accordion(label="HOW TO", open=False):
            gr.Markdown(USAGE_INSTRUCTION)
        with gr.Row():
            run_btn = gr.Button("New chat")
            run_btn.click(
                func_new_chat,
                inputs=params,
                outputs=[
                    chat.chatbot,
                    chat.chatbot_state,
                    chat.saved_input,
                    param_state,
                    sess,
                    *outputs,
                ],
            )
            with gr.Accordion(label="End chat", open=False):
                likes = gr.Radio(["like", "dislike", "neutral"], value="neutral")
                save_log = gr.Checkbox(
                    value=True,
                    label="Save log",
                    info="If saved, log can be exported later",
                    show_label=True,
                )
                end_btn = gr.Button("End chat")
                end_btn.click(
                    func_end_chat,
                    inputs=[likes, save_log, sess],
                    outputs=[param_state, sess],
                )
            with gr.Accordion(label="Export", open=False):
                exported_file = gr.File(
                    label="Output file", show_label=True, height=100
                )
                export_btn = gr.Button("Export")
                export_btn.click(func_export_to_excel, inputs=[], outputs=exported_file)

        with gr.Row():
            with gr.Column():
                with gr.Tab("Params"):
                    for component in params:
                        component.render()
                    with gr.Accordion(label="Session state", open=False):
                        param_state.render()

                with gr.Tab("Outputs"):
                    for component in outputs:
                        component.render()
            with gr.Column():
                chat.render()

    return demo.queue()


def build_chat_ui(config, pipeline_def):
    """Build the chat UI

    Args:
        config: the UI config
        pipeline_def: the pipeline definition

    Returns:
        the UI object
    """
    output_dir: Path = Path(storage.url(pipeline_def().config.store_result))
    exported_dir = output_dir.parent / "exported"
    exported_dir.mkdir(parents=True, exist_ok=True)

    resultlog = getattr(pipeline_def, "_promptui_resultlog", ResultLog)
    allowed_resultlog_callbacks = {i for i in dir(resultlog) if not i.startswith("__")}

    def new_chat(*args):
        """Start a new chat function

        Args:
            *args: the pipeline init params

        Returns:
            new empty states
        """
        gr.Info("Starting new session...")
        param_dicts = {
            name: value for name, value in zip(config["params"].keys(), args)
        }
        for key in param_dicts.keys():
            if config["params"][key].get("component").lower() == "file":
                param_dicts[key] = param_dicts[key].name

        # TODO: currently hard-code as ChatConversation
        pipeline = pipeline_def()
        session = ChatConversation(bot=pipeline)
        session.set(param_dicts)
        session.start_session()

        param_state_str = "\n".join(
            f"- {name}: {value}" for name, value in param_dicts.items()
        )

        gr.Info("New chat session started.")
        return (
            [],
            [],
            None,
            param_state_str,
            session,
            *[None] * len(config.get("outputs", [])),
        )

    def chat(message, history, session, *args):
        """The chat interface

        # TODO: wrap the input and output of this chat function so that it
        work with more types of chat conversation than simple text

        Args:
            message: the message from the user
            history: the gradio history of the chat
            session: the chat object session
            *args: the additional inputs

        Returns:
            the response from the chatbot
        """
        if session is None:
            raise gr.Error(
                "No active chat session. Please set the params and click New chat"
            )

        pred = session(message)
        text_response = pred.content

        additional_outputs = []
        for output_def in config.get("outputs", []):
            value = session.last_run.logs(output_def["step"])
            getter = output_def.get("getter", None)
            if getter and getter in allowed_resultlog_callbacks:
                value = getattr(resultlog, getter)(value)
            additional_outputs.append(value)

        return text_response, *additional_outputs

    def end_chat(preference: str, save_log: bool, session):
        """End the chat session

        Args:
            preference: the preference of the user
            save_log: whether to save the result
            session: the chat object session

        Returns:
            the new empty state
        """
        gr.Info("Ending session...")
        session.end_session()
        output_dir: Path = (
            Path(storage.url(session.config.store_result)) / session.last_run.id()
        )

        if not save_log:
            if output_dir.exists():
                import shutil

                shutil.rmtree(output_dir)

            session = None
            param_state = ""
            gr.Info("End session without saving log.")
            return param_state, session

        # add preference result to progress
        with (output_dir / "progress.pkl").open("rb") as fi:
            progress = pickle.load(fi)
            progress["preference"] = preference
        with (output_dir / "progress.pkl").open("wb") as fo:
            pickle.dump(progress, fo)

        # get the original params
        param_dicts = {name: session.getx(name) for name in config["params"].keys()}
        with (output_dir / "params.pkl").open("wb") as fo:
            pickle.dump(param_dicts, fo)

        session = None
        param_state = ""
        gr.Info("End session and save log.")
        return param_state, session

    def export_func():
        name = (
            f"{pipeline_def.__module__}.{pipeline_def.__name__}_{datetime.now()}.xlsx"
        )
        path = str(exported_dir / name)
        gr.Info(f"Begin exporting {name}...")
        try:
            export(config=config, pipeline_def=pipeline_def, output_path=path)
        except Exception as e:
            raise gr.Error(f"Failed to export. Please contact project's AIR: {e}")
        gr.Info(f"Exported {name}. Please go to the `Exported file` tab to download")
        return path

    demo = construct_chat_ui(
        config=config,
        func_new_chat=new_chat,
        func_chat=chat,
        func_end_chat=end_chat,
        func_export_to_excel=export_func,
    )
    return demo
