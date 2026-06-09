from typing import Any, Protocol


class Runnable(Protocol):
    """Minimal execution contract for pipelines/components."""

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Run component logic."""


class Serializable(Protocol):
    """Contract for objects that can be stored as runtime specs."""

    def to_spec(self) -> dict[str, Any]:
        """Return a JSON-serializable runtime spec."""
