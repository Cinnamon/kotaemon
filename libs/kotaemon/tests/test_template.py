import pytest

from kotaemon.llms import PromptTemplate


def test_prompt_template_creation():
    # Ensure the PromptTemplate object is created correctly
    template_string = "This is a template"
    template = PromptTemplate(template_string)
    assert template.template == template_string

    template_string = "Hello, {name}! Today is {day}."
    template = PromptTemplate(template_string)
    assert template.template == template_string
    assert template.placeholders == {"name", "day"}


def test_prompt_template_creation_invalid_placeholder():
    # Ensure the PromptTemplate object handle invalid placeholder correctly
    template_string = "Hello, {name}! Today is {0day}."

    with pytest.raises(ValueError):
        PromptTemplate(template_string, ignore_invalid=False)

    with pytest.warns(
        UserWarning,
        match="Ignore invalid placeholder: 0day.",
    ):
        PromptTemplate(template_string, ignore_invalid=True)


def test_prompt_template_addition():
    # Ensure the __add__ method concatenates the templates correctly
    template1 = PromptTemplate("Hello, ")
    template2 = PromptTemplate("world!")
    result = template1 + template2
    assert result.template == "Hello, \nworld!"

    template1 = PromptTemplate("Hello, {name}!")
    template2 = PromptTemplate("Today is {day}.")
    result = template1 + template2
    assert result.template == "Hello, {name}!\nToday is {day}."


def test_prompt_template_extract_placeholders():
    # Ensure the PromptTemplate correctly extracts placeholders
    template_string = "Hello, {name}! Today is {day}."
    result = PromptTemplate(template_string).placeholders
    assert result == {"name", "day"}


def test_prompt_template_populate():
    # Ensure the populate method populates the template correctly
    template_string = "Hello, {name}! Today is {day}."
    template = PromptTemplate(template_string)
    result = template.populate(name="John", day="Monday")
    assert result == "Hello, John! Today is Monday."


def test_prompt_template_check_missing_kwargs():
    # Ensure the check_missing_kwargs and populate methods raise an exception for
    # missing placeholders
    template_string = "Hello, {name}! Today is {day}."
    template = PromptTemplate(template_string)
    kwargs = dict(name="John")

    with pytest.raises(ValueError):
        template.check_missing_kwargs(**kwargs)

    with pytest.raises(ValueError):
        template.populate(**kwargs)


def test_prompt_template_check_redundant_kwargs():
    # Ensure the check_redundant_kwargs, partial_populate and populate methods warn for
    # redundant placeholders
    template_string = "Hello, {name}! Today is {day}."
    template = PromptTemplate(template_string)
    kwargs = dict(name="John", day="Monday", age="30")

    with pytest.warns(UserWarning, match="Keys provided but not in template: age"):
        template.check_redundant_kwargs(**kwargs)

    with pytest.warns(UserWarning, match="Keys provided but not in template: age"):
        template.partial_populate(**kwargs)

    with pytest.warns(UserWarning, match="Keys provided but not in template: age"):
        template.populate(**kwargs)


def test_prompt_template_populate_complex_template():
    # Ensure the populate method produces the same results as the built-in str.format
    # function
    template_string = (
        "a = {a:.2f}, b = {b}, c = {c:.1%}, d = {d:#.0g}, ascii of {e} = {e!a:>2}"
    )
    template = PromptTemplate(template_string)
    kwargs = dict(a=1, b="two", c=3, d=4, e="á")
    populated = template.populate(**kwargs)
    expected = template_string.format(**kwargs)
    assert populated == expected


def test_prompt_template_partial_populate():
    # Ensure the partial_populate method populates correctly
    template_string = (
        "a = {a:.2f}, b = {b}, c = {c:.1%}, d = {d:#.0g}, ascii of {e} = {e!a:>2}"
    )
    template = PromptTemplate(template_string)
    kwargs = dict(a=1, b="two", d=4, e="á")
    populated = template.partial_populate(**kwargs)
    expected = "a = 1.00, b = two, c = {c:.1%}, d = 4., ascii of á = '\\xe1'"
    assert populated == expected
