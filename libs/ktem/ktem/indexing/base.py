from kotaemon.base import BaseComponent


class BaseIndex(BaseComponent):
    def get_user_settings(self) -> dict:
        """Get the user settings for indexing

        Returns:
            dict: user settings in the dictionary format of
                `ktem.settings.SettingItem`
        """
        return {}

    @classmethod
    def get_pipeline(cls, setting: dict) -> "BaseIndex":
        raise NotImplementedError
