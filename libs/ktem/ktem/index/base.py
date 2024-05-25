import abc
import logging
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ktem.app import BasePage

    from kotaemon.base import BaseComponent


logger = logging.getLogger(__name__)


class BaseIndex(abc.ABC):
    """The base class for the index

    The index is responsible for storing information in a searchable manner, and
    retrieving that information.

    An application can have multiple indices. For example:
        - An index of files locally in the computer
        - An index of chat messages on Discord, Slack, etc.
        - An index of files stored on Google Drie, Dropbox, etc.
        - ...

    User can create, delete, and manage the indices in this application. They
    can create an index, set it to track a local folder in their computer, and
    then the chatbot can search for files in that folder. The user can create
    another index to track their chat messages on Discords. And so on.

    This class defines the interface for the index. It concerns with:
        - Setting up the necessary software infrastructure for the index to work
        (e.g. database table, vector store collection, etc.).
        - Providing the UI for user interaction with the index, including settings.

    Methods:

        __init__: initiate any resource definition required for the index to work
            (e.g. database table, vector store collection, etc.).
        on_create: called only once, when the user creates the index.
        on_delete: called only once, when the user deletes the index.
        on_start: called when the index starts.
        get_selector_component_ui: return the UI component to select the entities in
            the Chat page. Called in the ChatUI page.
        get_index_page_ui: return the index page UI to manage the entities. Called in
            the main application UI page.
        get_user_settings: return default user settings. Called only when the app starts
        get_admin_settings: return the admin settings. Called only when the user
            creates the index (for the admin to customize it). The output will be
            stored in the Index's config.
        get_indexing_pipeline: return the indexing pipeline when the entities are
            populated into the index
        get_retriever_pipelines: return the retriever pipelines when the user chat
    """

    def __init__(self, app, id, name, config):
        self._app = app
        self.id = id
        self.name = name
        self.config = config  # admin settings

    def on_create(self):
        """Create the index for the first time"""

    def on_delete(self):
        """Trigger when the user delete the index"""

    def on_start(self):
        """Trigger when the index start

        Args:
            id (int): the id of the index
            name (str): the name of the index
            config (dict): the config of the index
        """

    def get_selector_component_ui(self) -> Optional["BasePage"]:
        """The UI component to select the entities in the Chat page"""
        return None

    def get_index_page_ui(self) -> Optional["BasePage"]:
        """The index page UI to manage the entities"""
        return None

    @classmethod
    def get_user_settings(cls) -> dict:
        """Return default user settings. These are the runtime settings.

        The settings will be populated in the user settings page. And will be used
        when initiating the indexing & retriever pipelines.

        Returns:
            dict: user settings in the dictionary format of
                `ktem.settings.SettingItem`
        """
        return {}

    @classmethod
    def get_admin_settings(cls) -> dict:
        """Return the default admin settings. These are the build-time settings.

        The settings will be populated in the admin settings page. And will be used
        when initiating the indexing & retriever pipelines.

        Returns:
            dict: user settings in the dictionary format of
                `ktem.settings.SettingItem`
        """
        return {}

    @abc.abstractmethod
    def get_indexing_pipeline(
        self, settings: dict, user_id: Optional[int]
    ) -> "BaseComponent":
        """Return the indexing pipeline that populates the entities into the index

        Args:
            settings: the user settings of the index
            user_id: the user id who is accessing the index
                TODO: instead of having a user_id, should have an app_state
                which might also contain the settings.

        Returns:
            BaseIndexing: the indexing pipeline
        """
        ...

    def get_retriever_pipelines(
        self, settings: dict, user_id: int, selected: Any = None
    ) -> list["BaseComponent"]:
        """Return the retriever pipelines to retrieve the entity from the index"""
        return []
