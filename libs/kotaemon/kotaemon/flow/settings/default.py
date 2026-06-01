"""Default setting for important variables"""
from pathlib import Path

from theflow.utils.paths import default_theflow_path, temp_path

CONTEXT = {
    "__type__": "theflow.context.Context",
}

CACHE = {
    "__type__": "theflow.cache.FileCache",
    "path": str(Path(temp_path(), "cache")),
}

STORAGE = {
    "__type__": "theflow.storage.LocalStorage",
    "prefix": str(default_theflow_path()),
}

MIDDLEWARE = {
    "default": [
        "theflow.middleware.TrackProgressMiddleware",
        "theflow.middleware.CachingMiddleware",
        "theflow.middleware.SkipComponentMiddleware",
    ]
}


BASE_BACKEND = {
    "__type__": "theflow.backends.Backend",
}
