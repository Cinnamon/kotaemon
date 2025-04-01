from typing import Optional, Type

from sqlalchemy import select
from sqlalchemy.orm import Session
from theflow.settings import settings as flowsettings
from theflow.utils.modules import deserialize

from kotaemon.rerankings.base import BaseReranking

from .db import RerankingTable, engine


class RerankingManager:
    """Represent a pool of rerankings models"""

    def __init__(self):
        self._models: dict[str, BaseReranking] = {}
        self._info: dict[str, dict] = {}
        self._default: str = ""
        self._vendors: list[Type] = []

        # populate the pool if empty
        if hasattr(flowsettings, "KH_RERANKINGS"):
            with Session(engine) as sess:
                count = sess.query(RerankingTable).count()
            if not count:
                for name, model in flowsettings.KH_RERANKINGS.items():
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
            stmt = select(RerankingTable)
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

    def load_vendors(self):
        from kotaemon.rerankings import (
            CohereReranking,
            TeiFastReranking,
            VoyageAIReranking,
        )

        self._vendors = [TeiFastReranking, CohereReranking, VoyageAIReranking]

    def __getitem__(self, key: str) -> BaseReranking:
        """Get model by name"""
        return self._models[key]

    def __contains__(self, key: str) -> bool:
        """Check if model exists"""
        return key in self._models

    def get(
        self, key: str, default: Optional[BaseReranking] = None
    ) -> Optional[BaseReranking]:
        """Get model by name with default value"""
        return self._models.get(key, default)

    def settings(self) -> dict:
        """Present model pools option for gradio"""
        return {
            "label": "Reranking",
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
            raise ValueError("No models is pool")

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

    def get_random(self) -> BaseReranking:
        """Get random model"""
        return self._models[self.get_random_name()]

    def get_default(self) -> BaseReranking:
        """Get default model

        In case there is no default model, choose random model from pool. In
        case there are multiple default models, choose random from them.

        Returns:
            BaseReranking: model
        """
        return self._models[self.get_default_name()]

    def info(self) -> dict:
        """List all models"""
        return self._info

    def add(self, name: str, spec: dict, default: bool):
        if not name:
            raise ValueError("Name must not be empty")

        try:
            with Session(engine) as sess:
                if default:
                    # turn all models to non-default
                    sess.query(RerankingTable).update({"default": False})
                    sess.commit()

                item = RerankingTable(name=name, spec=spec, default=default)
                sess.add(item)
                sess.commit()
        except Exception as e:
            raise ValueError(f"Failed to add model {name}: {e}")

        self.load()

    def delete(self, name: str):
        """Delete a model from the pool"""
        try:
            with Session(engine) as sess:
                item = sess.query(RerankingTable).filter_by(name=name).first()
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
                    sess.query(RerankingTable).update({"default": False})
                    sess.commit()

                item = sess.query(RerankingTable).filter_by(name=name).first()
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


reranking_models_manager = RerankingManager()
