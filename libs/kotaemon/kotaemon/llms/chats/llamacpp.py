from typing import TYPE_CHECKING, Iterator, Optional, cast

from kotaemon.base import BaseMessage, HumanMessage, LLMInterface, Param

from .base import ChatLLM

if TYPE_CHECKING:
    from llama_cpp import CreateChatCompletionResponse as CCCR
    from llama_cpp import Llama


class LlamaCppChat(ChatLLM):
    """Wrapper around the llama-cpp-python's Llama model"""

    model_path: Optional[str] = Param(
        help="Path to the model file. This is required to load the model.",
    )
    repo_id: Optional[str] = Param(
        help="Id of a repo on the HuggingFace Hub in the form of `user_name/repo_name`."
    )
    filename: Optional[str] = Param(
        help="A filename or glob pattern to match the model file in the repo."
    )
    chat_format: str = Param(
        help=(
            "Chat format to use. Please refer to llama_cpp.llama_chat_format for a "
            "list of supported formats. If blank, the chat format will be auto-"
            "inferred."
        ),
        required=True,
    )
    lora_base: Optional[str] = Param(None, help="Path to the base Lora model")
    n_ctx: Optional[int] = Param(512, help="Text context, 0 = from model")
    n_gpu_layers: Optional[int] = Param(
        0,
        help="Number of layers to offload to GPU. If -1, all layers are offloaded",
    )
    use_mmap: Optional[bool] = Param(
        True,
        help=(),
    )
    vocab_only: Optional[bool] = Param(
        False,
        help="If True, only the vocabulary is loaded. This is useful for debugging.",
    )

    _role_mapper: dict[str, str] = {
        "human": "user",
        "system": "system",
        "ai": "assistant",
    }

    @Param.auto()
    def client_object(self) -> "Llama":
        """Get the llama-cpp-python client object"""
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python is not installed. "
                "Please install it using `pip install llama-cpp-python`"
            )

        errors = []
        if not self.model_path and (not self.repo_id or not self.filename):
            errors.append(
                "- `model_path` or `repo_id` and `filename` are required to load the"
                " model"
            )

        if not self.chat_format:
            errors.append(
                "- `chat_format` is required to know how to format the chat messages. "
                "Please refer to llama_cpp.llama_chat_format for a list of supported "
                "formats."
            )
        if errors:
            raise ValueError("\n".join(errors))

        if self.model_path:
            return Llama(
                model_path=cast(str, self.model_path),
                chat_format=self.chat_format,
                lora_base=self.lora_base,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                use_mmap=self.use_mmap,
                vocab_only=self.vocab_only,
            )
        else:
            return Llama.from_pretrained(
                repo_id=self.repo_id,
                filename=self.filename,
                chat_format=self.chat_format,
                lora_base=self.lora_base,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                use_mmap=self.use_mmap,
                vocab_only=self.vocab_only,
            )

    def prepare_message(
        self, messages: str | BaseMessage | list[BaseMessage]
    ) -> list[dict]:
        input_: list[BaseMessage] = []

        if isinstance(messages, str):
            input_ = [HumanMessage(content=messages)]
        elif isinstance(messages, BaseMessage):
            input_ = [messages]
        else:
            input_ = messages

        output_ = [
            {"role": self._role_mapper[each.type], "content": each.content}
            for each in input_
        ]

        return output_

    def invoke(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> LLMInterface:

        pred: "CCCR" = self.client_object.create_chat_completion(
            messages=self.prepare_message(messages),
            stream=False,
        )

        return LLMInterface(
            content=pred["choices"][0]["message"]["content"] if pred["choices"] else "",
            candidates=[
                c["message"]["content"]
                for c in pred["choices"]
                if c["message"]["content"]
            ],
            completion_tokens=pred["usage"]["completion_tokens"],
            total_tokens=pred["usage"]["total_tokens"],
            prompt_tokens=pred["usage"]["prompt_tokens"],
        )

    def stream(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> Iterator[LLMInterface]:
        pred = self.client_object.create_chat_completion(
            messages=self.prepare_message(messages),
            stream=True,
        )
        for chunk in pred:
            if not chunk["choices"]:
                continue

            if "content" not in chunk["choices"][0]["delta"]:
                continue

            yield LLMInterface(content=chunk["choices"][0]["delta"]["content"])
