from abc import abstractmethod

from theflow.base import Compose


class BaseComponent(Compose):
    """Base class for component

    A component is a class that can be used to compose a pipeline. To use the
    component, you should implement the following methods:

    - run_raw: run on raw input
    - run_batch_raw: run on batch of raw input
    - run_document: run on document
    - run_batch_document: run on batch of documents
    - is_document: check if input is document
    - is_batch: check if input is batch
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
    def run_raw(self, *args, **kwargs):
        ...

    @abstractmethod
    def run_batch_raw(self, *args, **kwargs):
        ...

    @abstractmethod
    def run_document(self, *args, **kwargs):
        ...

    @abstractmethod
    def run_batch_document(self, *args, **kwargs):
        ...

    @abstractmethod
    def is_document(self, *args, **kwargs) -> bool:
        ...

    @abstractmethod
    def is_batch(self, *args, **kwargs) -> bool:
        ...

    def run(self, *args, **kwargs):
        """Run the component."""

        is_document = self.is_document(*args, **kwargs)
        is_batch = self.is_batch(*args, **kwargs)

        if is_document and is_batch:
            return self.run_batch_document(*args, **kwargs)
        elif is_document and not is_batch:
            return self.run_document(*args, **kwargs)
        elif not is_document and is_batch:
            return self.run_batch_raw(*args, **kwargs)
        else:
            return self.run_raw(*args, **kwargs)
