from typing import Any, Generator as GeneratorType, Iterator


class Generator:
    """A generator that stores return value from another generator"""

    def __init__(self, gen: GeneratorType[Any, Any, Any]) -> None:
        self.gen = gen

    def __iter__(self) -> Iterator[Any]:
        self.value = yield from self.gen
        return self.value
