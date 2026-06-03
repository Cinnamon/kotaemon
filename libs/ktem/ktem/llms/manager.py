from typing import Optional

from ktem.db.cruds import LLMCRUD
from ktem.db.engine import engine
from ktem.db.models import LLMTable

from kotaemon.llms import ChatLLM
from kotaemon.llms.chats.factory import LLMFactory, LLMVendor


class LLMManager:
    """Represent a pool of language models."""

    def __init__(self):
        self._models: dict[str, ChatLLM] = {}
        self._info: dict[str, LLMTable] = {}
        self._default: str = ""

        self.load()

    def load(self) -> None:
        """Load the model pool from database."""
        self._models, self._info, self._default = {}, {}, ""

        with LLMCRUD(engine) as crud:
            for item in crud.list_all():
                llm_cls = LLMFactory.get_cls(LLMVendor(item.vendor))
                self._models[item.name] = llm_cls(**item.spec)
                self._info[item.name] = item
                if item.default:
                    self._default = item.name

    def __getitem__(self, key: str) -> ChatLLM:
        """Get model by name."""
        if key == "default":
            key = self._default
        return self._models[key]

    def __contains__(self, key: str) -> bool:
        """Check if model exists."""
        return key in self._models

    def get(
        self, key: str, default: Optional[ChatLLM] = None
    ) -> Optional[ChatLLM]:
        """Get model by name with a fallback default."""
        return self._models.get(key, default)

    def settings(self) -> dict:
        """Return Gradio dropdown settings for the pool."""
        return {
            "label": "LLM",
            "choices": list(self._models.keys()),
            "value": self.get_default_name(),
        }

    def options(self) -> dict[str, ChatLLM]:
        """Return all models keyed by name."""
        return self._models

    def get_random_name(self) -> str:
        """Return a random model name from the pool."""
        import random

        if not self._models:
            raise ValueError("No models in pool")
        return random.choice(list(self._models.keys()))

    def get_default_name(self) -> str:
        """Return the default model name, or a random one if unset."""
        if not self._models:
            raise ValueError("No models in pool")
        return self._default or self.get_random_name()

    def get_default(self) -> ChatLLM:
        """Return the default model instance."""
        return self._models[self.get_default_name()]

    def info(self) -> dict[str, LLMTable]:
        """Return all model metadata keyed by name."""
        return self._info

    def add(self, name: str, vendor: LLMVendor, spec: dict, default: bool) -> None:
        """Add a new model to the pool.

        Args:
            name: unique model name.
            vendor: vendor class identifier for factory lookup.
            spec: constructor parameters for the vendor class.
            default: make this model the pool default.

        Raises:
            ValueError: on validation or database errors.
        """
        try:
            with LLMCRUD(engine) as crud:
                crud.create(
                    name=name, 
                    vendor=vendor, 
                    spec=spec, 
                    default=default,
                )
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(
                f"Failed to add LLM '{name}': {e}"
            ) from e
        self.load()

    def delete(self, name: str) -> None:
        """Remove a model from the pool.

        Args:
            name: name of the model to remove.

        Raises:
            ValueError: if the model does not exist.
        """
        with LLMCRUD(engine) as crud:
            crud.delete(name)
        self.load()

    def update(
        self,
        name: str,
        vendor: LLMVendor,
        spec: dict,
        default: bool,
        new_name: str = "",
    ) -> None:
        """Update a model, optionally renaming it.

        Args:
            name: current model name.
            vendor: vendor class identifier for factory lookup.
            spec: constructor parameters for the vendor class.
            default: new default flag.
            new_name: rename the model when non-empty.

        Raises:
            ValueError: on validation or database errors.
        """
        if new_name and new_name != name:
            if new_name in self._info:
                raise ValueError(
                    f"Model '{new_name}' already exists."
                    " Use a unique name."
                )
            self.delete(name)
            self.add(new_name, vendor=vendor, spec=spec, default=default)
            return

        try:
            with LLMCRUD(engine) as crud:
                crud.update(
                    name, vendor=vendor, spec=spec, default=default
                )
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(
                f"Failed to update LLM '{name}': {e}"
            ) from e
        self.load()


llms = LLMManager()
