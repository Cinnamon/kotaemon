import gradio as gr

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
SUPPORTED_COMPONENTS = set(COMPONENTS_CLASS.keys())
DEFAULT_COMPONENT_BY_TYPES = {
    "str": "text",
    "bool": "checkbox",
    "int": "number",
    "float": "number",
    "list": "dropdown",
}
