import re
from typing import Set


class PromptTemplate:
    """
    Base class for prompt templates.
    """

    @staticmethod
    def extract_placeholders(template: str) -> Set[str]:
        """
        Extracts placeholders from a template string.

        Args:
            template (str): The template string to extract placeholders from.

        Returns:
            set[str]: A set of placeholder names found in the template string.
        """
        placeholder_regex = r"{([a-zA-Z_][a-zA-Z0-9_]*)}"

        placeholders = set()
        for item in re.findall(placeholder_regex, template):
            if item.isidentifier():
                placeholders.add(item)

        return placeholders

    def __init__(self, template: str):
        self.placeholders = self.extract_placeholders(template)
        self.template = template

    def populate(self, **kwargs):
        """
        Populate the template with the given keyword arguments.

        Args:
            **kwargs: The keyword arguments to populate the template.
                      Each keyword corresponds to a placeholder in the template.

        Returns:
            str: The populated template.

        Raises:
            ValueError: If an unknown placeholder is provided.

        """
        prompt = self.template
        for placeholder, value in kwargs.items():
            if placeholder not in self.placeholders:
                raise ValueError(f"Unknown placeholder: {placeholder}")
            prompt = prompt.replace(f"{{{placeholder}}}", value)

        return prompt

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
