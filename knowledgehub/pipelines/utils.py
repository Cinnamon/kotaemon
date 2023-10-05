import hashlib
from typing import List


def filename_to_hash(filename: str) -> str:
    """
    Convert filename to hash to be used as collection name for storage
    """
    result = hashlib.md5(filename.encode())
    return result.hexdigest()


def file_names_to_collection_name(file_name_list: List[str]) -> str:
    """
    Convert list of filenames to collection name
    """
    return filename_to_hash(" ".join(file_name_list))
