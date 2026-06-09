from typing import Optional, Type

from ktem.collections.registry import get_index_cls
from ktem.db.cruds import IndexCRUD
from ktem.db.engine import engine
from ktem.settings_config import app_settings as settings

from .base import BaseCollection


class CollectionManager:
    """Manage the application indices

    The index manager is responsible for:
        - Managing the range of possible indices and their extensions
        - Each actual index built by user

    Attributes:
        - indices: list of indices built by user
    """

    def __init__(self, app):
        self._app = app
        self._collections = []
        self._index_types: dict[str, Type[BaseCollection]] = {}

    @property
    def index_types(self) -> dict:
        """List the index_type of the index"""
        return self._index_types

    def build_index(self, name: str, config: dict, index_type: str):
        """Build the index

        Building the index simply means recording the index information into the
        database and returning the index object.

        Args:
            name (str): the name of the index
            config (dict): the config of the index
            index_type (str): the type of the index
            id (int, optional): the id of the index. If None, the id will be
                generated automatically. Defaults to None.

        Returns:
            BaseCollection: the index object
        """

        with IndexCRUD(engine) as crud:
            entry = crud.create(name=name, index_type=index_type, config=config)

            if entry.id is None:
                raise ValueError(f'Cannot create index "{name}": missing id')
            index_id = entry.id
            try:
                index_cls = get_index_cls(index_type)
                index = index_cls(app=self._app, id=index_id, name=name, config=config)
                index.on_create()
                crud.update(index_id, config=index.config)
            except Exception as e:
                crud.delete(index_id)
                raise ValueError(f'Cannot create index "{name}": {e}') from e

        return index

    def update_index(self, id: int, name: str, config: dict):
        """Update the index information

        Args:
            id: the id of the index
            name: the new name of the index
            config: the new config of the index
        """
        with IndexCRUD(engine) as crud:
            crud.update(id, name=name, config=config)

        for index in self._collections:
            if index.id == id:
                index.name = name
                index.config = config
                break

    def start_index(self, id: int, name: str, config: dict, index_type: str):
        """Start the index

        Args:
            id (int): the id of the index
            name (str): the name of the index
            config (dict): the config of the index
            index_type (str): the type of the index
        """
        index_cls = get_index_cls(index_type)
        index = index_cls(app=self._app, id=id, name=name, config=config)
        index.on_start()

        self._collections.append(index)
        return index

    def delete_index(self, id: int):
        """Delete the index from the database"""
        index: Optional[BaseCollection] = None
        for _ in self._collections:
            if _.id == id:
                index = _
                break

        if index is None:
            raise ValueError(
                "Index does not exist. If you have already removed the index, "
                "please restart to reflect the changes."
            )

        try:
            try:
                index.on_delete()
            except Exception as e:
                print(f"Error while deleting index {index.name}: {e}")

            with IndexCRUD(engine) as crud:
                crud.delete(id)

            new_indices = [_ for _ in self._collections if _.id != id]
            self._collections = new_indices
        except Exception as e:
            raise ValueError(f"Cannot delete index {index.name}: {e}") from e

    def load_index_types(self):
        """Load the supported index types"""
        self._index_types = {}

        from .file.index import FileIndex

        for index in [FileIndex]:
            self._index_types[f"{index.__module__}.{index.__qualname__}"] = index

        for index_str in settings.KH_INDEX_TYPES:
            cls = get_index_cls(index_str)
            self._index_types[f"{cls.__module__}.{cls.__qualname__}"] = cls

    def exists(self, id: Optional[int] = None, name: Optional[str] = None) -> bool:
        """Check if the index exists

        Args:
            id (int): the id of the index

        Returns:
            bool: True if the index exists, False otherwise
        """
        with IndexCRUD(engine) as crud:
            if id:
                return crud.get(id) is not None
            if name:
                return crud.get_by_name(name) is not None

        return False

    def on_application_startup(self):
        """This method is called by the base application when the application starts

        Load the index from database
        """
        self.load_index_types()

        for index in settings.KH_INDICES:
            if not self.exists(name=index["name"]):
                self.build_index(**index)

        with IndexCRUD(engine) as crud:
            index_defs = crud.list_all()
            for index_def in index_defs:
                if index_def.id is None:
                    continue
                self.start_index(
                    id=index_def.id,
                    name=index_def.name,
                    config=index_def.config,
                    index_type=index_def.index_type,
                )

    @property
    def collections(self):
        return self._collections[:1]

    def info(self):
        return {index.id: index for index in self._collections}
