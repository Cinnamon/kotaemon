from hashlib import md5
from typing import Any


class naivehash:
    """Hash a Python object

    Args:
        hash_func: hash function to use. Default is md5
    """

    def __init__(self, hash_func=None):
        """Initialize the hash object"""
        self.hash_func = hash_func() if hash_func is not None else md5()

    def update(self, obj: Any):
        """Hash a Python object

        Args:
            obj: Python object to be hashed

        Returns:
            hash of the object
        """
        type_ = f"{chr(0)}{type(obj)}{chr(0)}"
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            self.hash_func.update(f"|{type_}|{obj}".encode())
        elif isinstance(obj, (tuple, list)):
            self.update(f"|{type_}|")
            for idx, item in enumerate(obj):
                self.update(f"|{type_}{idx}|")
                self.update(item)
        elif isinstance(obj, set):
            self.update(f"|{type_}|")
            for idx, item in enumerate(sorted(obj)):
                self.update(f"|{type_}{idx}|")
                self.update(item)
        elif isinstance(obj, dict):
            self.update(f"|{type_}|")
            for idx, key in enumerate(sorted(obj)):
                self.update(f"|{type_}{idx}|")
                self.update(key)
                self.update(obj[key])
        else:
            path = ""
            path += str(obj.__module__) if hasattr(obj, "__module__") else ""
            path += str(obj.__name__) if hasattr(obj, "__name__") else ""
            self.update(f"|{type_}|{path}|")

            for idx, attr in enumerate(sorted(dir(obj))):
                if attr.startswith("_"):
                    continue
                self.update(f"|{type_}{idx}|")
                self.update(attr)
                # avoid self.update(getattr(obj, attr)) to avoid infinite recursion
                self.update(str(getattr(obj, attr)))

    def __call__(self, obj: Any) -> str:
        """Return the hash digest"""
        self.update(obj)
        return self.hash_func.hexdigest()
