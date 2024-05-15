# Add new indexing and reasoning pipeline to the application

@trducng

At high level, to add new indexing and reasoning pipeline:

1. You define your indexing or reasoning pipeline as a class from
   `BaseComponent`.
2. You declare that class in the setting files `flowsettings.py`.

Then when `python app.py`, the application will dynamically load those
pipelines.

The below sections talk in more detail about how the pipelines should be
constructed.

## Define a pipeline as a class

In essence, a pipeline will subclass from `kotaemon.base.BaseComponent`.
Each pipeline has 2 main parts:

- All declared arguments and sub-pipelines.
- The logic inside the pipeline.

An example pipeline:

```python
from kotaemon.base import BaseComponent


class SoSimple(BaseComponent):
    arg1: int
    arg2: str

    def run(self, arg3: str):
        return self.arg1 * self.arg2 + arg3
```

This pipeline is simple for demonstration purpose, but we can imagine pipelines
with much more arguments, that can take other pipelines as arguments, and have
more complicated logic in the `run` method.

**_An indexing or reasoning pipeline is just a class subclass from
`BaseComponent` like above._**

For more detail on this topic, please refer to [Creating a
Component](/create-a-component/)

## Run signatures

**Note**: this section is tentative at the moment. We will finalize `def run`
function signature by latest early April.

The indexing pipeline:

```python
    def run(
        self,
        file_paths: str | Path | list[str | Path],
        reindex: bool = False,
        **kwargs,
    ):
        """Index files to intermediate representation (e.g. vector, database...)

        Args:
            file_paths: the list of paths to files
            reindex: if True, files in `file_paths` that already exists in database
                should be reindex.
        """
```

The reasoning pipeline:

```python
    def run(self, question: str, history: list, **kwargs) -> Document:
        """Answer the question

        Args:
            question: the user input
            history: the chat history [(user_msg1, bot_msg1), (user_msg2, bot_msg2)...]

        Returns:
            kotaemon.base.Document: the final answer
        """
```

## Register your pipeline to ktem

To register your pipelines to ktem, you declare it in the `flowsettings.py`
file. This file locates at the current working directory where you start the
ktem. In most use cases, it is this
[one](https://github.com/Cinnamon/kotaemon/blob/main/libs/ktem/flowsettings.py).

```python
KH_REASONING = ["<python.module.path.to.the.reasoning.class>"]

KH_INDEX = "<python.module.path.to.the.indexing.class>"
```

You can register multiple reasoning pipelines to ktem by populating the
`KH_REASONING` list. The user can select which reasoning pipeline to use
in their Settings page.

For now, there's only one supported index option for `KH_INDEX`.

Make sure that your class is discoverable by Python.

## Allow users to customize your pipeline in the app settings

To allow the users to configure your pipeline, you need to declare what you
allow the users to configure as a dictionary. `ktem` will include them into the
application settings.

In your pipeline class, add a classmethod `get_user_settings` that returns a
setting dictionary, add a classmethod `get_info` that returns an info
dictionary. Example:

```python
class SoSimple(BaseComponent):

    ... # as above

    @classmethod
    def get_user_settings(cls) -> dict:
        """The settings to the user"""
        return {
            "setting_1": {
                "name": "Human-friendly name",
                "value": "Default value",
                "choices": [("Human-friendly Choice 1", "choice1-id"), ("HFC 2", "choice2-id")], # optional
                "component": "Which Gradio UI component to render, can be: text, number, checkbox, dropdown, radio, checkboxgroup"
            },
            "setting_2": {
                # follow the same rule as above
            }
        }

    @classmethod
    def get_info(cls) -> dict:
        """Pipeline information for bookkeeping purpose"""
        return {
            "id": "a unique id to differentiate this pipeline from other pipeline",
            "name": "Human-friendly name of the pipeline",
            "description": "Can be a short description of this pipeline"
        }
```

Once adding these methods to your pipeline class, `ktem` will automatically
extract and add them to the settings.

## Construct to pipeline object

Once `ktem` runs your pipeline, it will call your classmethod `get_pipeline`
with the full user settings and expect to obtain the pipeline object. Within
this `get_pipeline` method, you implement all the necessary logics to initiate
the pipeline object. Example:

```python
class SoSimple(BaseComponent):
    ... # as above

    @classmethod
    def get_pipeline(self, setting):
        obj = cls(arg1=setting["reasoning.id.setting1"])
        return obj
```

## Reasoning: Stream output to UI

For fast user experience, you can stream the output directly to UI. This way,
user can start observing the output as soon as the LLM model generates the 1st
token, rather than having to wait the pipeline finishes to read the whole message.

To stream the output, you need to;

1. Turn the `run` function to async.
2. Pass in the output to a special queue with `self.report_output`.

```python

    async def run(self, question: str, history: list, **kwargs) -> Document:
        for char in "This is a long messages":
            self.report_output({"output": text.text})
```

The argument to `self.report_output` is a dictionary, that contains either or
all of these 2 keys: "output", "evidence". The "output" string will be streamed
to the chat message, and the "evidence" string will be streamed to the
information panel.

## Access application LLMs, Embeddings

You can access users' collections of LLMs and embedding models with:

```python
from ktem.embeddings.manager import embeddings
from ktem.llms.manager import llms


llm = llms.get_default()
embedding_model = embeddings.get_default()
```

You can also allow the users to specifically select which llms or embedding
models they want to use through the settings.

```python
    @classmethod
    def get_user_settings(cls) -> dict:
        from ktem.llms.manager import llms

        return {
            "citation_llm": {
                "name": "LLM for citation",
                "value": llms.get_default(),
                "component: "dropdown",
                "choices": list(llms.options().keys()),
            },
            ...
        }
```

## Optional: Access application data

You can access the user's application database, vector store as follow:

```python
# get the database that contains the source files
from ktem.db.models import Source, Index, Conversation, User

# get the vector store
```
