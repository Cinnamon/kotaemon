from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize(
    "module_name,class_name",
    [("react", "ReactAgentPipeline"), ("rewoo", "RewooAgentPipeline")],
)
def test_repeated_pipeline_load_preserves_enabled_tools(
    module_name, class_name, mocker
):
    import importlib

    module = importlib.import_module(f"ktem.reasoning.{module_name}")
    pipeline_class = getattr(module, class_name)
    config = {
        "command": "npx",
        "args": ["-y", "mcp-remote", "https://example.com/mcp"],
        "enabled_tools": ["search"],
    }
    original = deepcopy(config)
    manager = Mock()
    manager.get.return_value = {"config": config}
    mocker.patch.object(module, "mcp_manager", manager)
    selected_tool = object()
    create_tools = mocker.patch.object(
        module, "create_tools_from_config", return_value=[selected_tool]
    )
    mocker.patch.object(module, "llms")
    pipeline = SimpleNamespace(
        agent=SimpleNamespace(prompt_template={}), rewrite_pipeline=SimpleNamespace()
    )
    mocker.patch.object(module, class_name, return_value=pipeline)
    prefix = f"reasoning.options.{pipeline_class.get_info()['id']}"
    settings = {
        f"{prefix}.{key}": value
        for key, value in {
            "llm": "",
            "planner_llm": "",
            "solver_llm": "",
            "max_iterations": 2,
            "qa_prompt": "test",
            "planner_prompt": "test",
            "solver_prompt": "test",
            "highlight_citation": False,
            "tools": ["[MCP] example"],
        }.items()
    }
    settings["reasoning.lang"] = "en"

    for _ in range(2):
        result = pipeline_class.get_pipeline(settings, {})
        assert result.agent.plugins == [selected_tool]
        assert create_tools.call_args.args[1] == ["search"]
        assert config == original
