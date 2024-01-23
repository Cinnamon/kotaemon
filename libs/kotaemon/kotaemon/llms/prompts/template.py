import warnings
from string import Formatter


class PromptTemplate:
    """
    Base class for prompt templates.
    """

    def __init__(self, template: str, ignore_invalid=True):
        template = template
        formatter = Formatter()
        parsed_template = list(formatter.parse(template))

        placeholders = set()
        for _, key, _, _ in parsed_template:
            if key is None:
                continue
            if not key.isidentifier():
                if ignore_invalid:
                    warnings.warn(f"Ignore invalid placeholder: {key}.", UserWarning)
                else:
                    raise ValueError(
                        "Placeholder name must be a valid Python identifier, found:"
                        f" {key}."
                    )
            placeholders.add(key)

        self.template = template
        self.placeholders = placeholders
        self.__formatter = formatter
        self.__parsed_template = parsed_template

    def check_missing_kwargs(self, **kwargs):
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
        missing_keys = self.placeholders.difference(kwargs.keys())
        if missing_keys:
            raise ValueError(f"Missing keys in template: {','.join(missing_keys)}")

    def check_redundant_kwargs(self, **kwargs):
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
        provided_keys = set(kwargs.keys())
        redundant_keys = provided_keys - self.placeholders

        if redundant_keys:
            warnings.warn(
                f"Keys provided but not in template: {','.join(redundant_keys)}",
                UserWarning,
            )

    def populate(self, **kwargs) -> str:
        """
        Strictly populate the template with the given keyword arguments.

        Args:
            **kwargs: The keyword arguments to populate the template.
                      Each keyword corresponds to a placeholder in the template.

        Returns:
            The populated template.

        Raises:
            ValueError: If an unknown placeholder is provided.
        """
        self.check_missing_kwargs(**kwargs)

        return self.partial_populate(**kwargs)

    def partial_populate(self, **kwargs):
        """
        Partially populate the template with the given keyword arguments.

        Args:
            **kwargs: The keyword arguments to populate the template.
                      Each keyword corresponds to a placeholder in the template.

        Returns:
            str: The populated template.
        """
        self.check_redundant_kwargs(**kwargs)

        prompt = []
        for literal_text, field_name, format_spec, conversion in self.__parsed_template:
            prompt.append(literal_text)

            if field_name is None:
                continue

            if field_name not in kwargs:
                if conversion:
                    value = f"{{{field_name}}}!{conversion}:{format_spec}"
                else:
                    value = f"{{{field_name}:{format_spec}}}"
            else:
                value = kwargs[field_name]
                if conversion is not None:
                    value = self.__formatter.convert_field(value, conversion)
                if format_spec is not None:
                    value = self.__formatter.format_field(value, format_spec)

            prompt.append(value)

        return "".join(prompt)

    def __add__(self, other):
        """
        Create a new PromptTemplate object by concatenating the template of the current
            object with the template of another PromptTemplate object.

        Parameters:
            other (PromptTemplate): Another PromptTemplate object.

        Returns:
            PromptTemplate: A new PromptTemplate object with the concatenated templates.
        """
        return PromptTemplate(self.template + "\n" + other.template)
