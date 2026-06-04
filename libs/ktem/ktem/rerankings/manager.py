from typing import Optional

from ktem.settings_config import app_settings as flowsettings

from ktem.db.cruds import RerankingCRUD
from ktem.db.engine import engine
from ktem.db.models import RerankingTable

from kotaemon.rerankings.base import BaseReranking
from kotaemon.rerankings.factory import (
    MP_VENDOR_CLS,
    RerankingFactory,
    RerankingVendor,
)


class RerankingManager:
    """Represent a pool of reranking models."""

    def __init__(self):
        self._models: dict[str, BaseReranking] = {}
        self._info: dict[str, RerankingTable] = {}
        self._default: str = ""

        self.load()

    def load(self) -> None:
        """Load the model pool from database."""
        self._models, self._info, self._default = {}, {}, ""

        with RerankingCRUD(engine) as crud:
            for item in crud.list_all():
                self._models[item.name] = RerankingFactory.get_cls(
                    item.vendor
                )(**item.spec)
                self._info[item.name] = item
                if item.default:
                    self._default = item.name

    def __getitem__(self, key: str) -> BaseReranking:
        """Get model by name."""
        if key == "default":
            key = self._default
        return self._models[key]

    def __contains__(self, key: str) -> bool:
        """Check if model exists."""
        return key in self._models

    def get(
        self, key: str, default: Optional[BaseReranking] = None
    ) -> Optional[BaseReranking]:
        """Get model by name with a fallback default."""
        return self._models.get(key, default)

    def settings(self) -> dict:
        """Return Gradio dropdown settings for the pool."""
        return {
            "label": "Reranking",
            "choices": list(self._models.keys()),
            "value": self.get_default_name(),
        }

    def options(self) -> dict[str, BaseReranking]:
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

    def get_random(self) -> BaseReranking:
        """Return a random model instance."""
        return self._models[self.get_random_name()]

    def get_default(self) -> BaseReranking:
        """Return the default model instance."""
        return self._models[self.get_default_name()]

    def info(self) -> dict[str, RerankingTable]:
        """Return all model metadata keyed by name."""
        return self._info

    def add(
        self,
        name: str,
        vendor: RerankingVendor,
        spec: dict,
        default: bool,
    ) -> None:
        """Add a new model to the pool."""
        try:
            with RerankingCRUD(engine) as crud:
                crud.create(
                    name=name, vendor=vendor, spec=spec, default=default
                )
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(
                f"Failed to add reranking model '{name}': {e}"
            ) from e
        self.load()

    def delete(self, name: str) -> None:
        """Remove a model from the pool."""
        with RerankingCRUD(engine) as crud:
            crud.delete(name)
        self.load()

    def update(
        self,
        name: str,
        vendor: RerankingVendor,
        spec: dict,
        default: bool,
        new_name: str = "",
    ) -> None:
        """Update a model, optionally renaming it."""
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
            with RerankingCRUD(engine) as crud:
                crud.update(
                    name, vendor=vendor, spec=spec, default=default
                )
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(
                f"Failed to update reranking model '{name}': {e}"
            ) from e
        self.load()

    def vendors(self) -> dict[RerankingVendor, type[BaseReranking]]:
        """Return all registered vendor classes keyed by RerankingVendor."""
        return {v: MP_VENDOR_CLS[v] for v in RerankingFactory.supported_vendors()}


reranking_models_manager = RerankingManager()
