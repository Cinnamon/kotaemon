from __future__ import annotations

from typing import Any, AsyncGenerator

import anyio
from gradio import ChatInterface
from gradio.components import Component, get_component_instance
from gradio.events import on
from gradio.helpers import special_args
from gradio.routes import Request


class ChatBlock(ChatInterface):
    """The ChatBlock subclasses ChatInterface to provide extra functionalities:

    - Show additional outputs to the chat interface
    - Disallow blank user message
    """

    def __init__(
        self,
        *args,
        additional_outputs: str | Component | list[str | Component] | None = None,
        **kwargs,
    ):
        if additional_outputs:
            if not isinstance(additional_outputs, list):
                additional_outputs = [additional_outputs]
            self.additional_outputs = [
                get_component_instance(i) for i in additional_outputs  # type: ignore
            ]
        else:
            self.additional_outputs = []

        super().__init__(*args, **kwargs)

    async def _submit_fn(
        self,
        message: str,
        history_with_input: list[list[str | None]],
        request: Request,
        *args,
    ) -> tuple[Any, ...]:
        input_args = args[: -len(self.additional_outputs)]
        output_args = args[-len(self.additional_outputs) :]
        if not message:
            return history_with_input, history_with_input, *output_args

        history = history_with_input[:-1]
        inputs, _, _ = special_args(
            self.fn, inputs=[message, history, *input_args], request=request
        )

        if self.is_async:
            response = await self.fn(*inputs)
        else:
            response = await anyio.to_thread.run_sync(
                self.fn, *inputs, limiter=self.limiter
            )

        output = []
        if self.additional_outputs:
            text = response[0]
            output = response[1:]
        else:
            text = response

        history.append([message, text])
        return history, history, *output

    async def _stream_fn(
        self,
        message: str,
        history_with_input: list[list[str | None]],
        *args,
    ) -> AsyncGenerator:
        raise NotImplementedError("Stream function not implemented for ChatBlock")

    def _display_input(
        self, message: str, history: list[list[str | None]]
    ) -> tuple[list[list[str | None]], list[list[str | None]]]:
        """Stop displaying the input message if the message is a blank string"""
        if not message:
            return history, history
        return super()._display_input(message, history)

    def _setup_events(self) -> None:
        """Include additional outputs in the submit event"""
        submit_fn = self._stream_fn if self.is_generator else self._submit_fn
        submit_triggers = (
            [self.textbox.submit, self.submit_btn.click]
            if self.submit_btn
            else [self.textbox.submit]
        )
        submit_event = (
            on(
                submit_triggers,
                self._clear_and_save_textbox,
                [self.textbox],
                [self.textbox, self.saved_input],
                api_name=False,
                queue=False,
            )
            .then(
                self._display_input,
                [self.saved_input, self.chatbot_state],
                [self.chatbot, self.chatbot_state],
                api_name=False,
                queue=False,
            )
            .then(
                submit_fn,
                [self.saved_input, self.chatbot_state]
                + self.additional_inputs
                + self.additional_outputs,
                [self.chatbot, self.chatbot_state] + self.additional_outputs,
                api_name=False,
            )
        )
        self._setup_stop_events(submit_triggers, submit_event)

        if self.retry_btn:
            retry_event = (
                self.retry_btn.click(
                    self._delete_prev_fn,
                    [self.chatbot_state],
                    [self.chatbot, self.saved_input, self.chatbot_state],
                    api_name=False,
                    queue=False,
                )
                .then(
                    self._display_input,
                    [self.saved_input, self.chatbot_state],
                    [self.chatbot, self.chatbot_state],
                    api_name=False,
                    queue=False,
                )
                .then(
                    submit_fn,
                    [self.saved_input, self.chatbot_state]
                    + self.additional_inputs
                    + self.additional_outputs,
                    [self.chatbot, self.chatbot_state] + self.additional_outputs,
                    api_name=False,
                )
            )
            self._setup_stop_events([self.retry_btn.click], retry_event)

        if self.undo_btn:
            self.undo_btn.click(
                self._delete_prev_fn,
                [self.chatbot_state],
                [self.chatbot, self.saved_input, self.chatbot_state],
                api_name=False,
                queue=False,
            ).then(
                lambda x: x,
                [self.saved_input],
                [self.textbox],
                api_name=False,
                queue=False,
            )

        if self.clear_btn:
            self.clear_btn.click(
                lambda: ([], [], None),
                None,
                [self.chatbot, self.chatbot_state, self.saved_input],
                queue=False,
                api_name=False,
            )

    def _setup_api(self) -> None:
        api_fn = self._api_stream_fn if self.is_generator else self._api_submit_fn

        self.fake_api_btn.click(
            api_fn,
            [self.textbox, self.chatbot_state] + self.additional_inputs,
            [self.textbox, self.chatbot_state] + self.additional_outputs,
            api_name="chat",
        )
