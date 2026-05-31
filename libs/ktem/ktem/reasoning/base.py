from typing import Any

from kotaemon.base import BaseComponent


class BaseReasoning(BaseComponent):
    """The reasoning pipeline that handles each of the user chat messages

    This reasoning pipeline has access to:
        - the retrievers
        - the user settings
        - the message
        - the conversation id
        - the message history
    """

    @classmethod
    def get_info(cls) -> dict[str, str]:
        """Get the pipeline information for the app to organize and display

        Returns:
            a dictionary that contains the following keys:
                - "id": the unique id of the pipeline
                - "name": the human-friendly name of the pipeline
                - "description": the overview short description of the pipeline, for
                user to grasp what does the pipeline do
        """
        raise NotImplementedError

    @classmethod
    def get_user_settings(cls) -> dict[str, dict[str, Any]]:
        """Get the default user settings for this pipeline"""
        return {}

    @classmethod
    def get_pipeline(
        cls,
        user_settings: dict[str, Any],
        state: dict[str, Any],
        retrievers: list[BaseComponent] | None = None,
    ) -> "BaseReasoning":
        """Get the reasoning pipeline for the app to execute

        Args:
            user_setting: user settings
            state: conversation state
            retrievers (list): List of retrievers
        """
        return cls()

    def run(
        self, message: str, conv_id: str, history: list[tuple[str, str]], **kwargs: Any
    ) -> Any:
        """Execute the reasoning pipeline"""
        raise NotImplementedError
