from typing import Callable, Any

from theflow import Param

from kotaemon.base import BaseComponent, Document

from .template import PromptTemplate


class BasePromptComponent(BaseComponent):
    """
    Base class for prompt components.

    Args:
        template (PromptTemplate): The prompt template.
        **kwargs: Any additional keyword arguments that will be used to populate the
            given template.
    """

    class Config:
        middleware_switches = {"theflow.middleware.CachingMiddleware": False}
        allow_extra = True

    template: str | PromptTemplate

    @Param.auto(depends_on="template")
    def template__(self) -> PromptTemplate:
        return (
            self.template
            if isinstance(self.template, PromptTemplate)
            else PromptTemplate(self.template)
        )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__set(**kwargs)

    def __check_redundant_kwargs(self, **kwargs: Any) -> None:
        """
        Check for redundant keyword arguments.

        Parameters:
            **kwargs (dict): A dictionary of keyword arguments.

        Raises:
            ValueError: If any keys provided are not in the template.

        Returns:
            None
        """
        self.template__.check_redundant_kwargs(**kwargs)

    def __check_unset_placeholders(self) -> None:
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
        self.template__.check_missing_kwargs(**self.__dict__)

    def __validate_value_type(self, **kwargs: Any) -> None:
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
            if k.startswith("template"):
                continue
            if not isinstance(v, (str, int, Document, Callable)):  # type: ignore
                type_error.append((k, type(v)))

        if type_error:
            raise ValueError(
                "Type of values must be either int, str, Document, Callable, "
                f"found unsupported type for (key, type): {type_error}"
            )

    def __set(self, **kwargs: Any) -> None:
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

    def __prepare_value(self) -> dict[str, str]:
        """
        Generate a dictionary of keyword arguments based on the template's placeholders
            and the current instance's attributes.

        Returns:
            dict: A dictionary of keyword arguments.
        """

        def __prepare(key: str, value: Any) -> str:
            if isinstance(value, str):
                return value
            if isinstance(value, (int, Document)):
                return str(value)

            raise ValueError(
                f"Unsupported type {type(value)} for template value of key {key}"
            )

        kwargs = {}
        for k in self.template__.placeholders:
            v = getattr(self, k)

            # if get a callable, execute to get its output
            if isinstance(v, Callable):  # type: ignore[arg-type]
                v = v()

            if isinstance(v, list):
                v = str([__prepare(k, each) for each in v])
            elif isinstance(v, (str, int, Document)):
                v = __prepare(k, v)
            else:
                raise ValueError(
                    f"Unsupported type {type(v)} for template value of key `{k}`"
                )
            kwargs[k] = v

        return kwargs

    def set_value(self, **kwargs: Any) -> None:
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

    def run(self, **kwargs: Any) -> Document:
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

        text = self.template__.populate(**prepared_kwargs)
        return Document(text=text, metadata={"origin": "PromptComponent"})

    def flow(self) -> Document:
        return self.__call__()
