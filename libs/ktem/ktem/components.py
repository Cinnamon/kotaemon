"""Common components, some kind of config"""

import logging
from functools import cache
from typing import Any, Optional

from ktem.settings_config import app_settings as settings

from kotaemon.storages import BaseDocumentStore, BaseVectorStore
from kotaemon.storages.docstores.factory import DocStoreFactory
from kotaemon.storages.vectorstores.factory import VectorStoreFactory

logger = logging.getLogger(__name__)


# filestorage_path = Path(settings.KH_FILESTORAGE_PATH)
# filestorage_path.mkdir(parents=True, exist_ok=True)


@cache
def get_docstore(collection_name: str | None = None) -> BaseDocumentStore:
    """Instantiate and return the configured docstore for *collection_name*."""
    overriding_envvars = {}
    if collection_name:
        overriding_envvars["DOCSTORE_COLLECTION_NAME"] = collection_name

    return DocStoreFactory.get_cls(settings.KH_DOCSTORE_VENDOR).from_env(
        overriding_envvars=overriding_envvars
    )


@cache
def get_vectorstore(collection_name: str | None = None) -> BaseVectorStore:
    """Instantiate and return the configured vectorstore for *collection_name*."""
    overriding_envvars = {}
    if collection_name:
        overriding_envvars["VECTORSTORE_COLLECTION_NAME"] = collection_name
    return VectorStoreFactory.get_cls(settings.KH_VECTORSTORE_VENDOR).from_env(
        overriding_envvars=overriding_envvars
    )


class ModelPool:
    """Represent a pool of models"""

    def __init__(self, category: str, conf: dict):
        self._category = category
        self._conf = conf

        self._models: dict[str, Any] = {}
        self._accuracy: list[str] = []
        self._cost: list[str] = []
        self._default: list[str] = []

        for name, model in conf.items():
            # TODO: replace with vendor-factory pattern once ModelPool
            # is used with non-empty conf (mirrors LLM/embedding managers).
            if model.get("default", False):
                self._default.append(name)

        self._accuracy = list(
            sorted(conf, key=lambda x: conf[x].get("accuracy", float("-inf")))
        )
        self._cost = list(sorted(conf, key=lambda x: conf[x].get("cost", float("inf"))))

    def __getitem__(self, key: str) -> Any:
        """Get model by name"""
        return self._models[key]

    def __setitem__(self, key: str, value: Any):
        """Set model by name"""
        self._models[key] = value

    def __delitem__(self, key: str):
        """Delete model by name"""
        del self._models[key]

    def __contains__(self, key: str) -> bool:
        """Check if model exists"""
        return key in self._models

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """Get model by name with default value"""
        return self._models.get(key, default)

    def settings(self) -> dict:
        """Present model pools option for gradio"""
        return {
            "label": self._category,
            "choices": list(self._models.keys()),
            "value": self.get_default_name(),
        }

    def options(self) -> dict:
        """Present a dict of models"""
        return self._models

    def get_random_name(self) -> str:
        """Get the name of random model

        Returns:
            str: random model name in the pool
        """
        import random

        if not self._conf:
            raise ValueError("No models in pool")

        return random.choice(list(self._conf.keys()))

    def get_default_name(self) -> str:
        """Get the name of default model

        In case there is no default model, choose random model from pool. In
        case there are multiple default models, choose random from them.

        Returns:
            str: model name
        """
        if not self._conf:
            raise ValueError("No models in pool")

        if self._default:
            import random

            return random.choice(self._default)

        return self.get_random_name()

    def get_random(self) -> Any:
        """Get random model"""
        return self._models[self.get_random_name()]

    def get_default(self) -> Any:
        """Get default model."""
        return self._models[self.get_default_name()]

    def get_highest_accuracy_name(self) -> str:
        """Get the name of model with highest accuracy

        Returns:
            str: model name
        """
        if not self._conf:
            raise ValueError("No models in pool")
        return self._accuracy[-1]

    def get_highest_accuracy(self) -> Any:
        """Get model with highest accuracy."""
        if not self._conf:
            raise ValueError("No models in pool")

        return self._models[self._accuracy[-1]]

    def get_lowest_cost_name(self) -> str:
        """Get the name of model with lowest cost

        Returns:
            str: model name
        """
        if not self._conf:
            raise ValueError("No models in pool")
        return self._cost[0]

    def get_lowest_cost(self) -> Any:
        """Get model with lowest cost."""
        if not self._conf:
            raise ValueError("No models in pool")

        return self._models[self._cost[0]]


reasonings: dict = {}
tools = ModelPool("Tools", {})
