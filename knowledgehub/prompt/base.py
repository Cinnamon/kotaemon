from typing import Union

from kotaemon.base import BaseComponent
from kotaemon.documents.base import Document
from kotaemon.prompt.template import PromptTemplate


class BasePrompt(BaseComponent):
    """
    Base class for prompt components.

    Args:
        template (PromptTemplate): The prompt template.
        **kwargs: Any additional keyword arguments that will be used to populate the
            given template.
    """

    def __check_redundant_kwargs(self, **kwargs):
        """
        Check for redundant keyword arguments.

        Parameters:
            **kwargs (dict): A dictionary of keyword arguments.

        Raises:
            ValueError: If any keys provided are not in the template.

        Returns:
            None
        """
        provided_keys = set(kwargs.keys())
        expected_keys = self.template.placeholders

        redundant_keys = provided_keys - expected_keys
        if redundant_keys:
            raise ValueError(f"\nKeys provided but not in template: {redundant_keys}")

    def __check_unset_placeholders(self):
        """
        Check if all the placeholders in the template are set.

        This function checks if all the expected placeholders in the template are set as
            attributes of the object. If any placeholders are missing, a `ValueError`
            is raised with the names of the missing keys.

        Parameters:
            None

        Returns:
            None
        """
        expected_keys = self.template.placeholders

        missing_keys = []
        for key in expected_keys:
            if key not in self.__dict__:
                missing_keys.append(key)

        if missing_keys:
            raise ValueError(f"\nMissing keys in template: {missing_keys}")

    def __validate_value_type(self, **kwargs):
        """
        Validates the value types of the given keyword arguments.

        Parameters:
            **kwargs (dict): A dictionary of keyword arguments to be validated.

        Raises:
            ValueError: If any of the values in the kwargs dictionary have an
                unsupported type.

        Returns:
            None
        """
        type_error = []
        for k, v in kwargs.items():
            if not isinstance(v, (str, int, Document, BaseComponent)):
                if isinstance(v, int):
                    kwargs[k] = str(v)
                type_error.append((k, type(v)))

        if type_error:
            raise ValueError(
                "Type of values must be either int, str, Document, BaseComponent, "
                f"found unsupported type for (key, type): {type_error}"
            )

    def __set(self, **kwargs):
        """
        Set the values of the attributes in the object based on the provided keyword
            arguments.

        Args:
            kwargs (dict): A dictionary with the attribute names as keys and the new
                values as values.

        Returns:
            None
        """
        self.__check_redundant_kwargs(**kwargs)
        self.__validate_value_type(**kwargs)

        self.__dict__.update(kwargs)

    def __prepare_value(self):
        """
        Generate a dictionary of keyword arguments based on the template's placeholders
            and the current instance's attributes.

        Returns:
            dict: A dictionary of keyword arguments.
        """
        kwargs = {}
        for k in self.template.placeholders:
            v = getattr(self, k)
            if isinstance(v, (int, Document)):
                v = str(v)
            elif isinstance(v, BaseComponent):
                v = str(v())
            kwargs[k] = v

        return kwargs

    def __init__(self, template: Union[str, PromptTemplate], **kwargs):
        super().__init__()
        self.template = (
            template
            if isinstance(template, PromptTemplate)
            else PromptTemplate(template)
        )

        self.__set(**kwargs)

    def set(self, **kwargs):
        """
        Similar to `__set` but for external use.

        Set the values of the attributes in the object based on the provided keyword
            arguments.

        Args:
            kwargs (dict): A dictionary with the attribute names as keys and the new
                values as values.

        Returns:
            None
        """
        self.__set(**kwargs)

    def run(self, **kwargs):
        """
        Run the function with the given keyword arguments.

        Args:
            **kwargs: The keyword arguments to pass to the function.

        Returns:
            The result of calling the `populate` method of the `template` object
            with the given keyword arguments.
        """
        self.__set(**kwargs)
        self.__check_unset_placeholders()
        prepared_kwargs = self.__prepare_value()

        return self.template.populate(**prepared_kwargs)

    def run_raw(self, *args, **kwargs):
        pass

    def run_batch_raw(self, *args, **kwargs):
        pass

    def run_document(self, *args, **kwargs):
        pass

    def run_batch_document(self, *args, **kwargs):
        pass

    def is_document(self, *args, **kwargs):
        pass

    def is_batch(self, *args, **kwargs):
        pass
