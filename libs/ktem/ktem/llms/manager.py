from typing import Optional, Type, overload

from sqlalchemy import select
from sqlalchemy.orm import Session
from theflow.settings import settings as flowsettings
from theflow.utils.modules import deserialize, import_dotted_string

from kotaemon.llms import ChatLLM

from .db import LLMTable, engine


class LLMManager:
    """Represent a pool of models"""

    def __init__(self):
        self._models: dict[str, ChatLLM] = {}
        self._info: dict[str, dict] = {}
        self._default: str = ""
        self._vendors: list[Type] = []

        if hasattr(flowsettings, "KH_LLMS"):
            for name, model in flowsettings.KH_LLMS.items():
                with Session(engine) as session:
                    stmt = select(LLMTable).where(LLMTable.name == name)
                    result = session.execute(stmt)
                    if not result.first():
                        item = LLMTable(
                            name=name,
                            spec=model["spec"],
                            default=model.get("default", False),
                        )
                        session.add(item)
                        session.commit()

        self.load()
        self.load_vendors()

    def load(self):
        """Load the model pool from database"""
        self._models, self._info, self._default = {}, {}, ""
        with Session(engine) as session:
            stmt = select(LLMTable)
            items = session.execute(stmt)

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
        from kotaemon.llms import (
            AzureChatOpenAI,
            ChatOpenAI,
            LCAnthropicChat,
            LCGeminiChat,
            LlamaCppChat,
        )

        self._vendors = [
            ChatOpenAI,
            AzureChatOpenAI,
            LCAnthropicChat,
            LCGeminiChat,
            LlamaCppChat,
        ]

        for extra_vendor in getattr(flowsettings, "KH_LLM_EXTRA_VENDORS", []):
            self._vendors.append(import_dotted_string(extra_vendor, safe=False))

    def __getitem__(self, key: str) -> ChatLLM:
        """Get model by name"""
        return self._models[key]

    def __contains__(self, key: str) -> bool:
        """Check if model exists"""
        return key in self._models

    @overload
    def get(self, key: str, default: None) -> Optional[ChatLLM]:
        ...

    @overload
    def get(self, key: str, default: ChatLLM) -> ChatLLM:
        ...

    def get(self, key: str, default: Optional[ChatLLM] = None) -> Optional[ChatLLM]:
        """Get model by name with default value"""
        return self._models.get(key, default)

    def settings(self) -> dict:
        """Present model pools option for gradio"""
        return {
            "label": "LLM",
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

    def get_random(self) -> ChatLLM:
        """Get random model"""
        return self._models[self.get_random_name()]

    def get_default(self) -> ChatLLM:
        """Get default model

        In case there is no default model, choose random model from pool. In
        case there are multiple default models, choose random from them.

        Returns:
            ChatLLM: model
        """
        return self._models[self.get_default_name()]

    def info(self) -> dict:
        """List all models"""
        return self._info

    def add(self, name: str, spec: dict, default: bool):
        """Add a new model to the pool"""
        name = name.strip()
        if not name:
            raise ValueError("Name must not be empty")

        try:
            with Session(engine) as session:

                if default:
                    # turn all models to non-default
                    session.query(LLMTable).update({"default": False})
                    session.commit()

                item = LLMTable(name=name, spec=spec, default=default)
                session.add(item)
                session.commit()
        except Exception as e:
            raise ValueError(f"Failed to add model {name}: {e}")

        self.load()

    def delete(self, name: str):
        """Delete a model from the pool"""
        try:
            with Session(engine) as session:
                item = session.query(LLMTable).filter_by(name=name).first()
                session.delete(item)
                session.commit()
        except Exception as e:
            raise ValueError(f"Failed to delete model {name}: {e}")

        self.load()

    def update(self, name: str, spec: dict, default: bool):
        """Update a model in the pool"""
        if not name:
            raise ValueError("Name must not be empty")

        try:
            with Session(engine) as session:

                if default:
                    # turn all models to non-default
                    session.query(LLMTable).update({"default": False})
                    session.commit()

                item = session.query(LLMTable).filter_by(name=name).first()
                if not item:
                    raise ValueError(f"Model {name} not found")
                item.spec = spec
                item.default = default
                session.commit()
        except Exception as e:
            raise ValueError(f"Failed to update model {name}: {e}")

        self.load()

    def vendors(self) -> dict:
        """Return list of vendors"""
        return {vendor.__qualname__: vendor for vendor in self._vendors}


llms = LLMManager()
