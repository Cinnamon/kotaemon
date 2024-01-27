from kotaemon.base import BaseComponent


class BaseRetriever(BaseComponent):
    pass


class BaseIndexing(BaseComponent):
    """The pipeline to index information into the data store"""

    def get_user_settings(self) -> dict:
        """Get the user settings for indexing

        Returns:
            dict: user settings in the dictionary format of
                `ktem.settings.SettingItem`
        """
        return {}

    @classmethod
    def get_pipeline(cls, settings: dict) -> "BaseIndexing":
        raise NotImplementedError

    def get_retrievers(self, settings: dict, **kwargs) -> list[BaseRetriever]:
        raise NotImplementedError
