# User settings

`ktem` allows developers to extend the index and the reasoning pipeline. In
many cases, these components can have settings that should be modified by
users at run-time, (e.g. `topk`, `chunksize`...). These are the user settings.

`ktem` allows developers to declare such user settings in their code. Once
declared, `ktem` will render them in a Settings page.

There are 2 places that `ktem` looks for declared user settings. You can
refer to the respective pages.

- In the index.
- In the reasoning pipeline.

## Syntax of a settings

A collection of settings is a dictionary of type `dict[str, dict]`, where the
key is a setting id, and the value is the description of the setting.

```python
settings = {
    "topk": {
        "name": "Top-k chunks",
        "value": 10,
        "component": "number",
    },
    "lang": {
        "name": "Languages",
        "value": "en",
        "component": "dropdown",
        "choices": [("en", "English"), ("cn", "Chinese")],
    }
}
```

Each setting description must have:

- name: the human-understandable name of the settings.
- value: the default value of the settings.
- component: the UI component to render such setting on the UI. Available:

  - "text": single-value
  - "number": single-value
  - "checkbox": single-value
  - "dropdown": choices
  - "radio": choices
  - "checkboxgroup": choices

- choices: the list of choices, if the component type allows.

## Settings page structure
