from typing import Type

from ktem.db.models import engine
from sqlmodel import Session, select
from theflow.settings import settings
from theflow.utils.modules import import_dotted_string

from .base import BaseIndex
from .models import Index


class IndexManager:
    """Manage the application indices

    The index manager is responsible for:
        - Managing the range of possible indices and their extensions
        - Each actual index built by user

    Attributes:
        - indices: list of indices built by user
    """

    def __init__(self, app):
        self._app = app
        self._indices = []
        self._index_types = {}

    def add_index_type(self, cls: Type[BaseIndex]):
        """Register index type to the system"""
        self._index_types[cls.__name__] = cls

    def list_index_types(self) -> dict:
        """List the index_type of the index"""
        return self._index_types

    def build_index(self, name: str, config: dict, index_type: str, id=None):
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
            BaseIndex: the index object
        """
        with Session(engine) as session:
            index_entry = Index(id=id, name=name, config=config, index_type=index_type)
            session.add(index_entry)
            session.commit()
            session.refresh(index_entry)

        index_cls = import_dotted_string(index_type, safe=False)
        index = index_cls(app=self._app, id=id, name=name, config=config)
        index.on_create()

        return index

    def start_index(self, id: int, name: str, config: dict, index_type: str):
        """Start the index

        Args:
            id (int): the id of the index
            name (str): the name of the index
            config (dict): the config of the index
            index_type (str): the type of the index
        """
        index_cls = import_dotted_string(index_type, safe=False)
        index = index_cls(app=self._app, id=id, name=name, config=config)
        index.on_start()

        self._indices.append(index)
        return index

    def exists(self, id: int) -> bool:
        """Check if the index exists

        Args:
            id (int): the id of the index

        Returns:
            bool: True if the index exists, False otherwise
        """
        with Session(engine) as session:
            index = session.get(Index, id)
            return index is not None

    def on_application_startup(self):
        """This method is called by the base application when the application starts

        Load the index from database
        """
        for index in settings.KH_INDEX_TYPES:
            index_cls = import_dotted_string(index, safe=False)
            self.add_index_type(index_cls)

        for index in settings.KH_INDICES:
            if not self.exists(index["id"]):
                self.build_index(**index)

        with Session(engine) as session:
            index_defs = session.exec(select(Index))
            for index_def in index_defs:
                self.start_index(**index_def.dict())

    @property
    def indices(self):
        return self._indices
