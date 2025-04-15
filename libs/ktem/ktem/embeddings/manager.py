from typing import Optional, Type

from sqlalchemy import select
from sqlalchemy.orm import Session
from theflow.settings import settings as flowsettings
from theflow.utils.modules import deserialize

from kotaemon.embeddings.base import BaseEmbeddings

from .db import EmbeddingTable, engine


class EmbeddingManager:
    """Represent a pool of models"""

    def __init__(self):
        self._models: dict[str, BaseEmbeddings] = {}
        self._info: dict[str, dict] = {}
        self._default: str = ""
        self._vendors: list[Type] = []

        # populate the pool if empty
        if hasattr(flowsettings, "KH_EMBEDDINGS"):
            with Session(engine) as sess:
                count = sess.query(EmbeddingTable).count()
            if not count:
                for name, model in flowsettings.KH_EMBEDDINGS.items():
                    self.add(
                        name=name,
                        spec=model["spec"],
                        default=model.get("default", False),
                    )

        self.load()
        self.load_vendors()

    def load(self):
        """Load the model pool from database"""
        self._models, self._info, self._default = {}, {}, ""
        with Session(engine) as sess:
            stmt = select(EmbeddingTable)
            items = sess.execute(stmt)

            for (item,) in items:
                self._models[item.name] = deserialize(item.spec, safe=False)
                self._info[item.name] = {
                    "name": item.name,
                    "spec": item.spec,
                    "default": item.default,
                }
                if item.default:
                    self._default = item.name
                    self._models["default"] = self._models[item.name]

    def load_vendors(self):
        from kotaemon.embeddings import (
            AzureOpenAIEmbeddings,
            FastEmbedEmbeddings,
            LCCohereEmbeddings,
            LCGoogleEmbeddings,
            LCHuggingFaceEmbeddings,
            LCMistralEmbeddings,
            OpenAIEmbeddings,
            TeiEndpointEmbeddings,
            VoyageAIEmbeddings,
        )

        self._vendors = [
            AzureOpenAIEmbeddings,
            OpenAIEmbeddings,
            FastEmbedEmbeddings,
            LCCohereEmbeddings,
            LCHuggingFaceEmbeddings,
            LCGoogleEmbeddings,
            LCMistralEmbeddings,
            TeiEndpointEmbeddings,
            VoyageAIEmbeddings,
        ]

    def __getitem__(self, key: str) -> BaseEmbeddings:
        """Get model by name"""
        return self._models[key]

    def __contains__(self, key: str) -> bool:
        """Check if model exists"""
        return key in self._models

    def get(
        self, key: str, default: Optional[BaseEmbeddings] = None
    ) -> Optional[BaseEmbeddings]:
        """Get model by name with default value"""
        return self._models.get(key, default)

    def settings(self) -> dict:
        """Present model pools option for gradio"""
        return {
            "label": "Embedding",
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

        if not self._models:
            raise ValueError("No models in pool")

        return random.choice(list(self._models.keys()))

    def get_default_name(self) -> str:
        """Get the name of default model

        In case there is no default model, choose random model from pool. In
        case there are multiple default models, choose random from them.

        Returns:
            str: model name
        """
        if not self._models:
            raise ValueError("No models in pool")

        if not self._default:
            return self.get_random_name()

        return self._default

    def get_random(self) -> BaseEmbeddings:
        """Get random model"""
        return self._models[self.get_random_name()]

    def get_default(self) -> BaseEmbeddings:
        """Get default model

        In case there is no default model, choose random model from pool. In
        case there are multiple default models, choose random from them.

        Returns:
            BaseEmbeddings: model
        """
        return self._models[self.get_default_name()]

    def info(self) -> dict:
        """List all models"""
        return self._info

    def add(self, name: str, spec: dict, default: bool):
        """Add a new model to the pool"""
        if not name:
            raise ValueError("Name must not be empty")

        try:
            with Session(engine) as sess:
                if default:
                    # turn all models to non-default
                    sess.query(EmbeddingTable).update({"default": False})
                    sess.commit()

                item = EmbeddingTable(name=name, spec=spec, default=default)
                sess.add(item)
                sess.commit()
        except Exception as e:
            raise ValueError(f"Failed to add model {name}: {e}")

        self.load()

    def delete(self, name: str):
        """Delete a model from the pool"""
        try:
            with Session(engine) as sess:
                item = sess.query(EmbeddingTable).filter_by(name=name).first()
                sess.delete(item)
                sess.commit()
        except Exception as e:
            raise ValueError(f"Failed to delete model {name}: {e}")

        self.load()

    def update(self, name: str, spec: dict, default: bool):
        """Update a model in the pool"""
        if not name:
            raise ValueError("Name must not be empty")

        try:
            with Session(engine) as sess:

                if default:
                    # turn all models to non-default
                    sess.query(EmbeddingTable).update({"default": False})
                    sess.commit()

                item = sess.query(EmbeddingTable).filter_by(name=name).first()
                if not item:
                    raise ValueError(f"Model {name} not found")
                item.spec = spec
                item.default = default
                sess.commit()
        except Exception as e:
            raise ValueError(f"Failed to update model {name}: {e}")

        self.load()

    def vendors(self) -> dict:
        """Return list of vendors"""
        return {vendor.__qualname__: vendor for vendor in self._vendors}


embedding_models_manager = EmbeddingManager()
