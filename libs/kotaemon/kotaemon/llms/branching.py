from typing import List, Optional

from kotaemon.base import Document, Runnable

from .linear import GatedLinearPipeline


class SimpleBranchingPipeline:
    def __init__(self, branches: List[Runnable] | None = None) -> None:
        self.branches: List[Runnable] = branches or []

    def add_branch(self, component: Runnable):
        self.branches.append(component)

    def run(self, **prompt_kwargs):
        return [branch(**prompt_kwargs) for branch in self.branches]


class GatedBranchingPipeline(SimpleBranchingPipeline):
    def run(self, *, condition_text: Optional[str] = None, **prompt_kwargs):
        if condition_text is None:
            raise ValueError("`condition_text` must be provided.")
        for branch in self.branches:
            output = branch(condition_text=condition_text, **prompt_kwargs)
            if output:
                return output
        return Document(None)
