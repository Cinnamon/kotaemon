import pytest

from kotaemon.documents.base import Document
from kotaemon.post_processing.extractor import RegexExtractor
from kotaemon.prompt.base import BasePrompt
from kotaemon.prompt.template import PromptTemplate


def test_set_attributes():
    template = PromptTemplate("str = {s}, int = {i}, doc = {doc}, comp = {comp}")
    doc = Document(text="Helloo, Alice!")
    comp = RegexExtractor(
        pattern=r"\d+", output_map={"1": "One", "2": "Two", "3": "Three"}
    )
    comp.set_run(kwargs={"text": "This is a test. 1 2 3"}, temp=True)

    prompt = BasePrompt(template=template, s="Alice", i=30, doc=doc, comp=comp)
    assert prompt.s == "Alice"
    assert prompt.i == 30
    assert prompt.doc == doc
    assert prompt.comp == comp


def test_check_redundant_kwargs():
    template = PromptTemplate("Hello, {name}!")
    prompt = BasePrompt(template, name="Alice")
    with pytest.raises(ValueError):
        prompt._BasePrompt__check_redundant_kwargs(name="Alice", age=30)


def test_check_unset_placeholders():
    template = PromptTemplate("Hello, {name}! I'm {age} years old.")
    prompt = BasePrompt(template, name="Alice")
    with pytest.raises(ValueError):
        prompt._BasePrompt__check_unset_placeholders()


def test_validate_value_type():
    template = PromptTemplate("Hello, {name}!")
    prompt = BasePrompt(template)
    with pytest.raises(ValueError):
        prompt._BasePrompt__validate_value_type(name={})


def test_run():
    template = PromptTemplate("str = {s}, int = {i}, doc = {doc}, comp = {comp}")
    doc = Document(text="Helloo, Alice!")
    comp = RegexExtractor(
        pattern=r"\d+", output_map={"1": "One", "2": "Two", "3": "Three"}
    )
    comp.set_run(kwargs={"text": "This is a test. 1 2 3"}, temp=True)

    prompt = BasePrompt(template=template, s="Alice", i=30, doc=doc, comp=comp)

    result = prompt()

    assert (
        result
        == "str = Alice, int = 30, doc = Helloo, Alice!, comp = ['One', 'Two', 'Three']"
    )


def test_set_method():
    template = PromptTemplate("Hello, {name}!")
    prompt = BasePrompt(template)
    prompt.set(name="Alice")
    assert prompt.name == "Alice"
