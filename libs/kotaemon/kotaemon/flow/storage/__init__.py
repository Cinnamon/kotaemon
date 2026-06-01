from ..settings import settings
from ..utils.modules import deserialize
from .local import LocalStorage

# make this lazy (created during first request)
storage = deserialize(settings.STORAGE, safe=False)

__all__ = ["LocalStorage", "storage"]
