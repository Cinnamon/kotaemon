from typing import Optional

from ktem.db.cruds import EmbeddingCRUD
from ktem.db.engine import engine
from ktem.db.models import EmbeddingTable

from kotaemon.embeddings.base import BaseEmbeddings
from kotaemon.embeddings.factory import (
    MP_VENDOR_CLS,
    EmbeddingFactory,
    EmbeddingVendor,
)


class EmbeddingManager:
    """Represent a pool of embedding models."""

    def __init__(self):
        self._models: dict[str, BaseEmbeddings] = {}
        self._info: dict[str, EmbeddingTable] = {}
        self._default: str = ""

        self.load()

    def load(self) -> None:
        """Load the model pool from database."""
        self._models, self._info, self._default = {}, {}, ""

        with EmbeddingCRUD(engine) as crud:
            for item in crud.list_all():
                self._models[item.name] = EmbeddingFactory.get_cls(
                    item.vendor
                )(**item.spec)
                self._info[item.name] = item
                if item.default:
                    self._default = item.name

    def __getitem__(self, key: str) -> BaseEmbeddings:
        """Get model by name."""
        if key == "default":
            key = self._default
        return self._models[key]

    def __contains__(self, key: str) -> bool:
        """Check if model exists."""
        return key in self._models

    def get(
        self, key: str, default: Optional[BaseEmbeddings] = None
    ) -> Optional[BaseEmbeddings]:
        """Get model by name with a fallback default."""
        return self._models.get(key, default)

    def settings(self) -> dict:
        """Return Gradio dropdown settings for the pool."""
        return {
            "label": "Embedding",
            "choices": list(self._models.keys()),
            "value": self.get_default_name(),
        }

    def options(self) -> dict[str, BaseEmbeddings]:
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

    def get_random(self) -> BaseEmbeddings:
        """Return a random model instance."""
        return self._models[self.get_random_name()]

    def get_default(self) -> BaseEmbeddings:
        """Return the default model instance."""
        return self._models[self.get_default_name()]

    def info(self) -> dict[str, EmbeddingTable]:
        """Return all model metadata keyed by name."""
        return self._info

    def add(
        self,
        name: str,
        vendor: EmbeddingVendor,
        spec: dict,
        default: bool,
    ) -> None:
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
            with EmbeddingCRUD(engine) as crud:
                crud.create(
                    name=name, vendor=vendor, spec=spec, default=default
                )
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(
                f"Failed to add embedding model '{name}': {e}"
            ) from e
        self.load()

    def delete(self, name: str) -> None:
        """Remove a model from the pool.

        Args:
            name: name of the model to remove.

        Raises:
            ValueError: if the model does not exist.
        """
        with EmbeddingCRUD(engine) as crud:
            crud.delete(name)
        self.load()

    def update(
        self,
        name: str,
        vendor: EmbeddingVendor,
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
        if not name:
            raise ValueError("Name must not be empty")

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
            with EmbeddingCRUD(engine) as crud:
                crud.update(
                    name, vendor=vendor, spec=spec, default=default
                )
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(
                f"Failed to update embedding model '{name}': {e}"
            ) from e
        self.load()

    def vendors(self) -> dict[EmbeddingVendor, type[BaseEmbeddings]]:
        """Return all registered vendor classes keyed by EmbeddingVendor."""
        return {v: MP_VENDOR_CLS[v] for v in self._vendors}


embedding_models_manager = EmbeddingManager()
