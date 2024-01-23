from kotaemon.base import Document


def get_plugin_response_content(output) -> str:
    """
    Wrapper for AgentOutput content return
    """
    if isinstance(output, Document):
        return output.text
    else:
        return str(output)


def calculate_cost(model_name: str, prompt_token: int, completion_token: int) -> float:
    """
    Calculate the cost of a prompt and completion.

    Returns:
        float: Cost of the provided model name with provided token information
    """
    # TODO: to be implemented
    return 0.0
