"""Common components, some kind of config"""

import logging
from functools import cache
from pathlib import Path
from typing import Optional

from theflow.settings import settings
from theflow.utils.modules import deserialize

from kotaemon.base import BaseComponent
from kotaemon.storages import BaseDocumentStore, BaseVectorStore

logger = logging.getLogger(__name__)


filestorage_path = Path(settings.KH_FILESTORAGE_PATH)
filestorage_path.mkdir(parents=True, exist_ok=True)


@cache
def get_docstore(collection_name: str = "default") -> BaseDocumentStore:
    from copy import deepcopy

    ds_conf = deepcopy(settings.KH_DOCSTORE)
    ds_conf["collection_name"] = collection_name
    return deserialize(ds_conf, safe=False)


@cache
def get_vectorstore(collection_name: str = "default") -> BaseVectorStore:
    from copy import deepcopy

    vs_conf = deepcopy(settings.KH_VECTORSTORE)
    vs_conf["collection_name"] = collection_name
    return deserialize(vs_conf, safe=False)


class ModelPool:
    """Represent a pool of models"""

    def __init__(self, category: str, conf: dict):
        self._category = category
        self._conf = conf

        self._models: dict[str, BaseComponent] = {}
        self._accuracy: list[str] = []
        self._cost: list[str] = []
        self._default: list[str] = []

        for name, model in conf.items():
            self._models[name] = deserialize(model["spec"], safe=False)
            if model.get("default", False):
                self._default.append(name)

        self._accuracy = list(
            sorted(conf, key=lambda x: conf[x].get("accuracy", float("-inf")))
        )
        self._cost = list(sorted(conf, key=lambda x: conf[x].get("cost", float("inf"))))

    def __getitem__(self, key: str) -> BaseComponent:
        """Get model by name"""
        return self._models[key]

    def __setitem__(self, key: str, value: BaseComponent):
        """Set model by name"""
        self._models[key] = value

    def __delitem__(self, key: str):
        """Delete model by name"""
        del self._models[key]

    def __contains__(self, key: str) -> bool:
        """Check if model exists"""
        return key in self._models

    def get(
        self, key: str, default: Optional[BaseComponent] = None
    ) -> Optional[BaseComponent]:
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

    def get_random(self) -> BaseComponent:
        """Get random model"""
        return self._models[self.get_random_name()]

    def get_default(self) -> BaseComponent:
        """Get default model

        In case there is no default model, choose random model from pool. In
        case there are multiple default models, choose random from them.

        Returns:
            BaseComponent: model
        """
        return self._models[self.get_default_name()]

    def get_highest_accuracy_name(self) -> str:
        """Get the name of model with highest accuracy

        Returns:
            str: model name
        """
        if not self._conf:
            raise ValueError("No models in pool")
        return self._accuracy[-1]

    def get_highest_accuracy(self) -> BaseComponent:
        """Get model with highest accuracy

        Returns:
            BaseComponent: model
        """
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

    def get_lowest_cost(self) -> BaseComponent:
        """Get model with lowest cost

        Returns:
            BaseComponent: model
        """
        if not self._conf:
            raise ValueError("No models in pool")

        return self._models[self._cost[0]]


reasonings: dict = {}
tools = ModelPool("Tools", {})
