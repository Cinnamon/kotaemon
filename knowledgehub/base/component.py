from abc import abstractmethod

from theflow.base import Function


class BaseComponent(Function):
    """A component is a class that can be used to compose a pipeline

    Benefits of component:
        - Auto caching, logging
        - Allow deployment

    For each component, the spirit is:
        - Tolerate multiple input types, e.g. str, Document, List[str], List[Document]
        - Enforce single output type. Hence, the output type of a component should be
        as generic as possible.
    """

    inflow = None

    def flow(self):
        if self.inflow is None:
            raise ValueError("No inflow provided.")

        if not isinstance(self.inflow, BaseComponent):
            raise ValueError(
                f"inflow must be a BaseComponent, found {type(self.inflow)}"
            )

        return self.__call__(self.inflow.flow())

    @abstractmethod
    def run(self, *args, **kwargs):
        # enforce output type to be compatible with Document
        """Run the component."""
        ...
