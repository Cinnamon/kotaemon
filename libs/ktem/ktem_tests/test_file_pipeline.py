import tiktoken

from ktem.index.file.pipelines import _default_token_func


def test_default_token_func_treats_special_tokens_as_text():
    text = "before <|endoftext|> after"
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

    assert _default_token_func(text) == encoding.encode(text, disallowed_special=())
