from typing import Any, Callable, Optional, Union

from ..base import BaseComponent
from ..base.schema import Document, IO_Type
from .chats import ChatLLM
from .completions import LLM
from .prompts import BasePromptComponent


class SimpleLinearPipeline(BaseComponent):
    """
    A simple pipeline for running a function with a prompt, a language model, and an
        optional post-processor.

    Attributes:
        prompt (BasePromptComponent): The prompt component used to generate the initial
            input.
        llm (Union[ChatLLM, LLM]): The language model component used to generate the
            output.
        post_processor (Union[BaseComponent, Callable[[IO_Type], IO_Type]]): An optional
            post-processor component or function.

    Example Usage:
        ```python
        from kotaemon.llms import LCAzureChatOpenAI, BasePromptComponent

        def identity(x):
            return x

        llm = LCAzureChatOpenAI(
            openai_api_base="your openai api base",
            openai_api_key="your openai api key",
            openai_api_version="your openai api version",
            deployment_name="dummy-q2-gpt35",
            temperature=0,
            request_timeout=600,
        )

        pipeline = SimpleLinearPipeline(
            prompt=BasePromptComponent(template="what is {word} in Japanese ?"),
            llm=llm,
            post_processor=identity,
        )
        print(pipeline(word="lone"))
        ```
    """

    prompt: BasePromptComponent
    llm: Union[ChatLLM, LLM]
    post_processor: Union[BaseComponent, Callable[[IO_Type], IO_Type]]

    def run(
        self,
        *,
        llm_kwargs: Optional[dict] = {},
        post_processor_kwargs: Optional[dict] = {},
        **prompt_kwargs,
    ):
        """
        Run the function with the given arguments and return the final output as a
            Document object.

        Args:
            llm_kwargs (dict): Keyword arguments for the llm call.
            post_processor_kwargs (dict): Keyword arguments for the post_processor.
            **prompt_kwargs: Keyword arguments for populating the prompt.

        Returns:
            Document: The final output of the function as a Document object.
        """
        prompt = self.prompt(**prompt_kwargs)
        llm_output = self.llm(prompt.text, **llm_kwargs)
        if self.post_processor is not None:
            final_output = self.post_processor(llm_output, **post_processor_kwargs)[0]
        else:
            final_output = llm_output

        return Document(final_output)


class GatedLinearPipeline(SimpleLinearPipeline):
    """
    A pipeline that extends the SimpleLinearPipeline class and adds a condition
        attribute.

    Attributes:
        condition (Callable[[IO_Type], Any]): A callable function that represents the
            condition.

    Usage:
        ```{.py3 title="Example Usage"}
        from kotaemon.llms import LCAzureChatOpenAI, BasePromptComponent
        from kotaemon.parsers import RegexExtractor

        def identity(x):
            return x

        llm = LCAzureChatOpenAI(
            openai_api_base="your openai api base",
            openai_api_key="your openai api key",
            openai_api_version="your openai api version",
            deployment_name="dummy-q2-gpt35",
            temperature=0,
            request_timeout=600,
        )

        pipeline = GatedLinearPipeline(
            prompt=BasePromptComponent(template="what is {word} in Japanese ?"),
            condition=RegexExtractor(pattern="some pattern"),
            llm=llm,
            post_processor=identity,
        )
        print(pipeline(condition_text="some pattern", word="lone"))
        print(pipeline(condition_text="other pattern", word="lone"))
        ```
    """

    condition: Callable[[IO_Type], Any]

    def run(
        self,
        *,
        condition_text: Optional[str] = None,
        llm_kwargs: Optional[dict] = {},
        post_processor_kwargs: Optional[dict] = {},
        **prompt_kwargs,
    ) -> Document:
        """
        Run the pipeline with the given arguments and return the final output as a
            Document object.

        Args:
            condition_text (str): The condition text to evaluate. Default to None.
            llm_kwargs (dict): Additional keyword arguments for the language model call.
            post_processor_kwargs (dict): Additional keyword arguments for the
                post-processor.
            **prompt_kwargs: Keyword arguments for populating the prompt.

        Returns:
            Document: The final output of the pipeline as a Document object.

        Raises:
            ValueError: If condition_text is None
        """
        if condition_text is None:
            raise ValueError("`condition_text` must be provided")

        if self.condition(condition_text)[0]:
            return super().run(
                llm_kwargs=llm_kwargs,
                post_processor_kwargs=post_processor_kwargs,
                **prompt_kwargs,
            )

        return Document(None)
