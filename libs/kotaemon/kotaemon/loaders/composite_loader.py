from typing import Callable, List, Optional, Type

from llama_index.core.readers.base import BaseReader as LIBaseReader

from .base import BaseReader, LIReaderMixin


class DirectoryReader(LIReaderMixin, BaseReader):
    """Wrap around llama-index SimpleDirectoryReader

    Args:
        input_dir (str): Path to the directory.
        input_files (List): List of file paths to read
            (Optional; overrides input_dir, exclude)
        exclude (List): glob of python file paths to exclude (Optional)
        exclude_hidden (bool): Whether to exclude hidden files (dotfiles).
        encoding (str): Encoding of the files.
            Default is utf-8.
        errors (str): how encoding and decoding errors are to be handled,
              see https://docs.python.org/3/library/functions.html#open
        recursive (bool): Whether to recursively search in subdirectories.
            False by default.
        filename_as_id (bool): Whether to use the filename as the document id.
            False by default.
        required_exts (Optional[List[str]]): List of required extensions.
            Default is None.
        file_extractor (Optional[Dict[str, BaseReader]]): A mapping of file
            extension to a BaseReader class that specifies how to convert that file
            to text. If not specified, use default from DEFAULT_FILE_READER_CLS.
        num_files_limit (Optional[int]): Maximum number of files to read.
            Default is None.
        file_metadata (Optional[Callable[str, Dict]]): A function that takes
            in a filename and returns a Dict of metadata for the Document.
            Default is None.
    """

    input_dir: Optional[str] = None
    input_files: Optional[List] = None
    exclude: Optional[List] = None
    exclude_hidden: bool = True
    errors: str = "ignore"
    recursive: bool = False
    encoding: str = "utf-8"
    filename_as_id: bool = False
    required_exts: Optional[list[str]] = None
    file_extractor: Optional[dict[str, "LIBaseReader"]] = None
    num_files_limit: Optional[int] = None
    file_metadata: Optional[Callable[[str], dict]] = None

    def _get_wrapped_class(self) -> Type["LIBaseReader"]:
        from llama_index.core import SimpleDirectoryReader

        return SimpleDirectoryReader
