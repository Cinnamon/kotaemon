from functools import cached_property, lru_cache
from typing import Any, Callable, Generic, TypeVar

DepT = TypeVar("DepT")


class Dependency(Generic[DepT]):
    def __init__(
        self,
        Caller: type[DepT] | Callable[..., DepT],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.Caller = Caller
        self.args = args
        self.kwargs = kwargs

    def instantiate(self) -> DepT:
        args = (arg.obj if isinstance(arg, Dependency) else arg for arg in self.args)
        kwargs = {
            key: val.obj if isinstance(val, Dependency) else val
            for key, val in self.kwargs.items()
        }

        return self.Caller(*args, **kwargs)

    @property
    def obj(self) -> DepT:
        return self.instantiate()

    def get(self) -> DepT:
        return self.instantiate()


class SingletonDependency(Dependency[DepT], Generic[DepT]):
    @cached_property
    def obj(self) -> DepT:
        return super().obj

    @lru_cache
    def get(self) -> DepT:
        return self.instantiate()


class Registry(Generic[DepT]):
    def __init__(
        self,
        mapping: dict[str, Dependency[DepT]] | None = None,
    ) -> None:
        self._registry: dict[str, Dependency[DepT]] = {}
        self._registry.update(mapping or {})

    @property
    def registry(self) -> dict[str, Dependency[DepT]]:
        return self._registry

    def get(self, key: str) -> Dependency[DepT]:
        return self.registry[key]
