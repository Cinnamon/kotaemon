Utilities detail can be referred in the sub-pages of this section.

## Prompt engineering UI

![chat-ui](https://github.com/Cinnamon/kotaemon/assets/35283585/ac8f9aac-d853-4571-a48b-d866a99eaf3e)

**_Important:_** despite the name prompt engineering UI, this tool allows DMs to test any kind of parameters that are exposed by AIRs. Prompt is one kind of param. There can be other type of params that DMs can tweak (e.g. top_k, temperature...).

**_Note:_** For hands-on examination of how to use prompt engineering UI, refer `./examples/promptui` and `./examples/example2/`

In client projects, AI developers typically build the pipeline. However, for LLM projects requiring Japanese and domain expertise in prompt creation, non-technical team members (DM, BizDev, and QALs) can be more effective. To facilitate this, "xxx" offers a user-friendly prompt engineering UI that AI developers integrate into their pipelines. This enables non-technical members to adjust prompts and parameters, run experiments, and export results for optimization.

As of Sept 2023, there are 2 kinds of prompt engineering UI:

- Simple pipeline: run one-way from start to finish.
- Chat pipeline: interactive back-and-forth.

### Simple pipeline

For simple pipeline, the supported client project workflow looks as follow:

1. [AIR] Build pipeline
2. [AIR] Export pipeline to config: `$ kh promptui export <module.path.piplineclass> --output <path/to/config/file.yml>`
3. [AIR] Customize the config
4. [AIR] Spin up prompt engineering UI: `$ kh promptui run <path/to/config/file.yml>`
5. [DM] Change params, run inference
6. [DM] Export to Excel
7. [DM] Select the set of params that achieve the best output

The prompt engineering UI prominently involves from step 2 to step 7 (step 1 is normal AI tasks in project, while step 7 happens exclusively in Excel file).

#### Step 2 - Export pipeline to config

Command:

```
$ kh promptui export <module.path.piplineclass> --output <path/to/config/file.yml>
```

where:

- `<module.path.pipelineclass>` is a dot-separated path to the pipeline. For example, if your pipeline can be accessed with `from projectA.pipelines import AnsweringPipeline`, then this value is `projectA.pipelines.AnswerPipeline`.
- `<path/to/config/file.yml>` is the target file path that the config will be exported to. If the config file already exists, and contains information of other pipelines, the config of current pipeline will additionally be added. If it contains information of the current pipeline (in the past), the old information will be replaced.

By default, all params in a pipeline (including nested params) will be export to the configuration file. For params that you do not wish to expose to the UI, you can directly remove them from the config YAML file. You can also annotate those param with `ignore_ui=True`, and they will be ignored in the config generation process. Example:

```python
class Pipeline(BaseComponent):
    param1: str = Param(default="hello")
    param2: str = Param(default="goodbye", ignore_ui=True)
```

Declared as above, and `param1` will show up in the config YAML file, while `param2` will not.

#### Step 3 - Customize the config

AIR can further edit the config file in this step to get the most suitable UI (step 4) with their tasks. The exported config will have this overall schema:

```
<module.path.pipelineclass1>:
  params:
    ... (Detail param information to initiate a pipeline. This corresponds to the pipeline init parameters.)
  inputs:
    ... (Detail the input of the pipeline e.g. a text prompt, an FNOL... This corresponds to the params of `run(...)` method.)
  outputs:
    ... (Detail the output of the pipeline e.g. prediction, accuracy... This is the output information we wish to see in the UI.)
  logs:
    ... (Detail what information should show up in the log.)
```

##### Input and params

The inputs section have the overall schema as follow:

```
inputs:
  <input-variable-name-1>:
    component: <supported-UI-component>
    params: # this section is optional)
      value: <default-value>
  <input-variable-name-2>:
    ... # similar to above
params:
  <param-variable-name-1>:
    ... # similar to those in the inputs
```

The list of supported prompt UI and their corresponding gradio UI components:

```
COMPONENTS_CLASS = {
    "text": gr.components.Textbox,
    "checkbox": gr.components.CheckboxGroup,
    "dropdown": gr.components.Dropdown,
    "file": gr.components.File,
    "image": gr.components.Image,
    "number": gr.components.Number,
    "radio": gr.components.Radio,
    "slider": gr.components.Slider,
}
```

##### Outputs

The outputs are a list of variables that we wish to show in the UI. Since in Python, the function output doesn't have variable name, so output declaration is a little bit different than input and param declaration:

```
outputs:
  - component: <supported-UI-component>
    step: <name-of-pipeline-step>
    item: <jsonpath way to retrieve the info>
  - ... # similar to above
```

where:

- component: the same text string and corresponding Gradio UI as in inputs & params
- step: the pipeline step that we wish to look fetch and show output on the UI
- item: the jsonpath mechanism to get the targeted variable from the step above

##### Logs

The logs show a list of sheetname and how to retrieve the desired information.

```
logs:
  <logname>:
    inputs:
      - name: <column name>
        step: <the pipeline step that we would wish to see the input>
        variable: <the variable in the step>
      - ...
    outputs:
      - name: <column name>
        step: <the pipeline step that we would wish to see the output>
        item: <how to retrieve the output of that step>
```

#### Step 4 + 5 - Spin up prompt engineering UI + Perform prompt engineering

Command:

```
$ kh promptui run <path/to/config/file.yml>
```

This will generate an UI as follow:

![Screenshot from 2023-09-20 12-20-31](https://github.com/Cinnamon/kotaemon/assets/35283585/9ac1b95a-b667-42e7-b318-98a1b805d6df)

where:

- The tabs at the top of the UI corresponds to the pipeline to do prompt engineering.
- The inputs and params tabs allow users to edit (these corresponds to the inputs and params in the config file).
- The outputs panel holds the UI elements to show the outputs defined in config file.
- The Run button: will execute pipeline with the supplied inputs and params, and render result in the outputs panel.
- The Export button: will export the logs of all the run to an Excel files users to inspect for best set of params.

#### Step 6 - Export to Excel

Upon clicking export, the users can download Excel file.

### Chat pipeline

Chat pipeline workflow is different from simple pipeline workflow. In simple pipeline, each Run creates a set of output, input and params for users to compare. In chat pipeline, each Run is not a one-off run, but a long interactive session. Hence, the workflow is as follow:

1. Set the desired parameters.
2. Click "New chat" to start a chat session with the supplied parameters. This set of parameters will persist until the end of the chat session. During an ongoing chat session, changing the parameters will not take any effect.
3. Chat and interact with the chat bot on the right panel. You can add any additional input (if any), and they will be supplied to the chatbot.
4. During chat, the log of the chat will show up in the "Output" tabs. This is empty by default, so if you want to show the log here, tell the AI developers to configure the UI settings.
5. When finishing chat, select your preference in the radio box. Click "End chat". This will save the chat log and the preference to disk.
6. To compare the result of different run, click "Export" to get an Excel spreadsheet summary of different run.
