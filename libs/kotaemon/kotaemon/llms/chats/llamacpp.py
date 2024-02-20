from typing import TYPE_CHECKING, Optional, cast

from kotaemon.base import BaseMessage, HumanMessage, LLMInterface, Param

from .base import ChatLLM

if TYPE_CHECKING:
    from llama_cpp import CreateChatCompletionResponse as CCCR
    from llama_cpp import Llama


class LlamaCppChat(ChatLLM):
    """Wrapper around the llama-cpp-python's Llama model"""

    model_path: Optional[str] = None
    chat_format: Optional[str] = None
    lora_base: Optional[str] = None
    n_ctx: int = 512
    n_gpu_layers: int = 0
    use_mmap: bool = True
    vocab_only: bool = False

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
        if not self.model_path:
            errors.append("- `model_path` is required to load the model")

        if not self.chat_format:
            errors.append(
                "- `chat_format` is required to know how to format the chat messages. "
                "Please refer to llama_cpp.llama_chat_format for a list of supported "
                "formats."
            )
        if errors:
            raise ValueError("\n".join(errors))

        return Llama(
            model_path=cast(str, self.model_path),
            chat_format=self.chat_format,
            lora_base=self.lora_base,
            n_ctx=self.n_ctx,
            n_gpu_layers=self.n_gpu_layers,
            use_mmap=self.use_mmap,
            vocab_only=self.vocab_only,
        )

    def run(
        self, messages: str | BaseMessage | list[BaseMessage], **kwargs
    ) -> LLMInterface:
        input_: list[BaseMessage] = []

        if isinstance(messages, str):
            input_ = [HumanMessage(content=messages)]
        elif isinstance(messages, BaseMessage):
            input_ = [messages]
        else:
            input_ = messages

        pred: "CCCR" = self.client_object.create_chat_completion(
            messages=[
                {"role": self._role_mapper[each.type], "content": each.content}
                for each in input_
            ],  # type: ignore
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
