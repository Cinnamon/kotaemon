import pytest

from kotaemon.prompt.template import PromptTemplate


def test_prompt_template_creation():
    # Test case 1: Ensure the PromptTemplate object is created correctly
    template_string = "This is a template"
    template = PromptTemplate(template_string)
    assert template.template == template_string

    template_string = "Hello, {name}! Today is {day}."
    template = PromptTemplate(template_string)
    assert template.template == template_string
    assert template.placeholders == {"name", "day"}


def test_prompt_template_addition():
    # Test case 2: Ensure the __add__ method concatenates the templates correctly
    template1 = PromptTemplate("Hello, ")
    template2 = PromptTemplate("world!")
    result = template1 + template2
    assert result.template == "Hello, \nworld!"

    template1 = PromptTemplate("Hello, {name}!")
    template2 = PromptTemplate("Today is {day}.")
    result = template1 + template2
    assert result.template == "Hello, {name}!\nToday is {day}."


def test_prompt_template_extract_placeholders():
    # Test case 3: Ensure the extract_placeholders method extracts placeholders
    # correctly
    template_string = "Hello, {name}! Today is {day}."
    result = PromptTemplate.extract_placeholders(template_string)
    assert result == {"name", "day"}


def test_prompt_template_populate():
    # Test case 4: Ensure the populate method populates the template correctly
    template_string = "Hello, {name}! Today is {day}."
    template = PromptTemplate(template_string)
    result = template.populate(name="John", day="Monday")
    assert result == "Hello, John! Today is Monday."


def test_prompt_template_unknown_placeholder():
    # Test case 5: Ensure the populate method raises an exception for unknown
    # placeholders
    template_string = "Hello, {name}! Today is {day}."
    template = PromptTemplate(template_string)
    with pytest.raises(ValueError):
        template.populate(name="John", month="January")
