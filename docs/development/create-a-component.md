# Creating a component

A fundamental concept in kotaemon is "component".

Anything that isn't data or data structure is a "component". A component can be
thought of as a step within a pipeline. It takes in some input, processes it,
and returns an output, just the same as a Python function! The output will then
become an input for the next component in a pipeline. In fact, a pipeline is just
a component. More appropriately, a nested component: a component that makes use of one or more other components in
the processing step. So in reality, there isn't a difference between a pipeline
and a component! Because of that, in kotaemon, we will consider them the
same as "component".

To define a component, you will:

1. Create a class that subclasses from `kotaemon.base.BaseComponent`
2. Declare init params with type annotation
3. Declare nodes (nodes are just other components!) with type annotation
4. Implement the processing logic in `run`.

The syntax of a component is as follow:

```python
from kotaemon.base import BaseComponent
from kotaemon.llms import LCAzureChatOpenAI
from kotaemon.parsers import RegexExtractor


class FancyPipeline(BaseComponent):
    param1: str = "This is param1"
    param2: int = 10
    param3: float

    node1: BaseComponent    # this is a node because of BaseComponent type annotation
    node2: LCAzureChatOpenAI  # this is also a node because LCAzureChatOpenAI subclasses BaseComponent
    node3: RegexExtractor   # this is also a node bceause RegexExtractor subclasses BaseComponent

    def run(self, some_text: str):
        prompt = (self.param1 + some_text) * int(self.param2 + self.param3)
        llm_pred = self.node2(prompt).text
        matches = self.node3(llm_pred)
        return matches
```

Then this component can be used as follow:

```python
llm = LCAzureChatOpenAI(endpoint="some-endpont")
extractor = RegexExtractor(pattern=["yes", "Yes"])

component = FancyPipeline(
    param1="Hello"
    param3=1.5
    node1=llm,
    node2=llm,
    node3=extractor
)
component("goodbye")
```

This way, we can define each operation as a reusable component, and use them to
compose larger reusable components!

## Benefits of component

By defining a component as above, we formally encapsulate all the necessary
information inside a single class. This introduces several benefits:

1. Allow tools like promptui to inspect the inner working of a component in
   order to automatically generate the promptui.
2. Allow visualizing a pipeline for debugging purpose.
