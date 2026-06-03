from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Iterator, Optional, cast

from kotaemon.base import BaseMessage, HumanMessage, LLMInterface

from .base import ChatLLM

if TYPE_CHECKING:
    from llama_cpp import CreateChatCompletionResponse as CCCR
    from llama_cpp import Llama


@dataclass(kw_only=True)
class LlamaCppChat(ChatLLM):
    """Wrapper around the llama-cpp-python Llama model."""

    model_path: Optional[str] = field(
        default=None, metadata={"description": "Path to the model file"}
    )
    repo_id: Optional[str] = field(
        default=None, metadata={"description": "HuggingFace repo id"}
    )
    filename: Optional[str] = field(
        default=None, metadata={"description": "Model filename in repo"}
    )
    chat_format: str = field(
        metadata={"description": "Chat format (llama_cpp.llama_chat_format)"}
    )
    lora_base: Optional[str] = field(
        default=None, metadata={"description": "Path to Lora model"}
    )
    n_ctx: Optional[int] = field(
        default=512, metadata={"description": "Text context size"}
    )
    n_gpu_layers: Optional[int] = field(
        default=0, metadata={"description": "GPU layers (-1 = all)"}
    )
    use_mmap: Optional[bool] = field(default=True, metadata={"description": ""})
    vocab_only: Optional[bool] = field(
        default=False, metadata={"description": "Vocabulary only (debug)"}
    )

    _role_mapper: dict[str, str] = field(
        default_factory=lambda: {
            "human": "user",
            "system": "system",
            "ai": "assistant",
        },
        repr=False,
    )

    @cached_property
    def client_object(self) -> "Llama":
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
                "- `model_path` or `repo_id` and `filename` are required"
            )
        if not self.chat_format:
            errors.append("- `chat_format` is required")
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
        if isinstance(messages, str):
            input_ = [HumanMessage(content=messages)]
        elif isinstance(messages, BaseMessage):
            input_ = [messages]
        else:
            input_ = messages

        return [
            {"role": self._role_mapper[each.type], "content": each.content}
            for each in input_
        ]

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
