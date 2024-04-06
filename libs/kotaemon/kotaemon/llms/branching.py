from typing import List, Optional

from kotaemon.base import BaseComponent, Document, Param

from .linear import GatedLinearPipeline


class SimpleBranchingPipeline(BaseComponent):
    """
    A simple branching pipeline for executing multiple branches.

    Attributes:
        branches (List[BaseComponent]): The list of branches to be executed.

    Example:
        ```python
        from kotaemon.llms import (
            LCAzureChatOpenAI,
            BasePromptComponent,
            GatedLinearPipeline,
        )
        from kotaemon.parsers import RegexExtractor

        def identity(x):
            return x

        pipeline = SimpleBranchingPipeline()
        llm = LCAzureChatOpenAI(
            openai_api_base="your openai api base",
            openai_api_key="your openai api key",
            openai_api_version="your openai api version",
            deployment_name="dummy-q2-gpt35",
            temperature=0,
            request_timeout=600,
        )

        for i in range(3):
            pipeline.add_branch(
                GatedLinearPipeline(
                    prompt=BasePromptComponent(template=f"what is {i} in Japanese ?"),
                    condition=RegexExtractor(pattern=f"{i}"),
                    llm=llm,
                    post_processor=identity,
                )
            )
        print(pipeline(condition_text="1"))
        print(pipeline(condition_text="2"))
        print(pipeline(condition_text="12"))
        ```
    """

    branches: List[BaseComponent] = Param(default_callback=lambda *_: [])

    def add_branch(self, component: BaseComponent):
        """
        Add a new branch to the pipeline.

        Args:
            component (BaseComponent): The branch component to be added.
        """
        self.branches.append(component)

    def run(self, **prompt_kwargs):
        """
        Execute the pipeline by running each branch and return the outputs as a list.

        Args:
            **prompt_kwargs: Keyword arguments for the branches.

        Returns:
            List: The outputs of each branch as a list.
        """
        output = []
        for i, branch in enumerate(self.branches):
            self._prepare_child(branch, name=f"branch-{i}")
            output.append(branch(**prompt_kwargs))

        return output


class GatedBranchingPipeline(SimpleBranchingPipeline):
    """
    A simple gated branching pipeline for executing multiple branches based on a
        condition.

    This class extends the SimpleBranchingPipeline class and adds the ability to execute
        the branches until a branch returns a non-empty output based on a condition.

    Attributes:
        branches (List[BaseComponent]): The list of branches to be executed.

    Example:
        ```python
        from kotaemon.llms import (
            LCAzureChatOpenAI,
            BasePromptComponent,
            GatedLinearPipeline,
        )
        from kotaemon.parsers import RegexExtractor

        def identity(x):
            return x

        pipeline = GatedBranchingPipeline()
        llm = LCAzureChatOpenAI(
            openai_api_base="your openai api base",
            openai_api_key="your openai api key",
            openai_api_version="your openai api version",
            deployment_name="dummy-q2-gpt35",
            temperature=0,
            request_timeout=600,
        )

        for i in range(3):
            pipeline.add_branch(
                GatedLinearPipeline(
                    prompt=BasePromptComponent(template=f"what is {i} in Japanese ?"),
                    condition=RegexExtractor(pattern=f"{i}"),
                    llm=llm,
                    post_processor=identity,
                )
            )
        print(pipeline(condition_text="1"))
        print(pipeline(condition_text="2"))
        ```
    """

    def run(self, *, condition_text: Optional[str] = None, **prompt_kwargs):
        """
        Execute the pipeline by running each branch and return the output of the first
            branch that returns a non-empty output based on the provided condition.

        Args:
            condition_text (str): The condition text to evaluate for each branch.
                Default to None.
            **prompt_kwargs: Keyword arguments for the branches.

        Returns:
            Union[OutputType, None]: The output of the first branch that satisfies the
            condition, or None if no branch satisfies the condition.

        Raises:
            ValueError: If condition_text is None
        """
        if condition_text is None:
            raise ValueError("`condition_text` must be provided.")

        for i, branch in enumerate(self.branches):
            self._prepare_child(branch, name=f"branch-{i}")
            output = branch(condition_text=condition_text, **prompt_kwargs)
            if output:
                return output

        return Document(None)


if __name__ == "__main__":
    import dotenv

    from kotaemon.llms import BasePromptComponent, LCAzureChatOpenAI
    from kotaemon.parsers import RegexExtractor

    def identity(x):
        return x

    secrets = dotenv.dotenv_values(".env")

    pipeline = GatedBranchingPipeline()
    llm = LCAzureChatOpenAI(
        openai_api_base=secrets.get("OPENAI_API_BASE", ""),
        openai_api_key=secrets.get("OPENAI_API_KEY", ""),
        openai_api_version=secrets.get("OPENAI_API_VERSION", ""),
        deployment_name="dummy-q2-gpt35",
        temperature=0,
        request_timeout=600,
    )

    for i in range(3):
        pipeline.add_branch(
            GatedLinearPipeline(
                prompt=BasePromptComponent(template=f"what is {i} in Japanese ?"),
                condition=RegexExtractor(pattern=f"{i}"),
                llm=llm,
                post_processor=identity,
            )
        )
    pipeline(condition_text="1")
