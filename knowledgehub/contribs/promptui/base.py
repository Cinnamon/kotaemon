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


def get_component(component_def: dict) -> gr.components.Component:
    """Get the component based on component definition"""
    component_cls = None

    if "component" in component_def:
        component = component_def["component"]
        if component not in SUPPORTED_COMPONENTS:
            raise ValueError(
                f"Unsupported UI component: {component}. "
                f"Must be one of {SUPPORTED_COMPONENTS}"
            )

        component_cls = COMPONENTS_CLASS[component]
    else:
        raise ValueError(
            f"Cannot decide the component from {component_def}. "
            "Please specify `component` with 1 of the following "
            f"values: {SUPPORTED_COMPONENTS}"
        )

    return component_cls(**component_def.get("params", {}))
