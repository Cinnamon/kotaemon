from typing import Any, Callable, Dict, Optional, Tuple, Type, Union

from langchain.agents import Tool as LCTool
from pydantic import BaseModel

from kotaemon.base import BaseComponent


class ToolException(Exception):
    """An optional exception that tool throws when execution error occurs.

    When this exception is thrown, the agent will not stop working,
    but will handle the exception according to the handle_tool_error
    variable of the tool, and the processing result will be returned
    to the agent as observation, and printed in red on the console.
    """


class BaseTool(BaseComponent):
    name: str
    """The unique name of the tool that clearly communicates its purpose."""
    description: str
    """Description used to tell the model how/when/why to use the tool.
    You can provide few-shot examples as a part of the description. This will be
    input to the prompt of LLM.
    """
    args_schema: Optional[Type[BaseModel]] = None
    """Pydantic model class to validate and parse the tool's input arguments."""
    verbose: bool = False
    """Whether to log the tool's progress."""
    handle_tool_error: Optional[
        Union[bool, str, Callable[[ToolException], str]]
    ] = False
    """Handle the content of the ToolException thrown."""

    def _parse_input(
        self,
        tool_input: Union[str, Dict],
    ) -> Union[str, Dict[str, Any]]:
        """Convert tool input to pydantic model."""
        args_schema = self.args_schema
        if isinstance(tool_input, str):
            if args_schema is not None:
                key_ = next(iter(args_schema.model_fields.keys()))
                args_schema.validate({key_: tool_input})
            return tool_input
        else:
            if args_schema is not None:
                result = args_schema.parse_obj(tool_input)
                return {k: v for k, v in result.dict().items() if k in tool_input}
        return tool_input

    def _run_tool(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Call tool."""
        raise NotImplementedError(f"_run_tool is not implemented for {self.name}")

    def _to_args_and_kwargs(self, tool_input: Union[str, Dict]) -> Tuple[Tuple, Dict]:
        # For backwards compatibility, if run_input is a string,
        # pass as a positional argument.
        if isinstance(tool_input, str):
            return (tool_input,), {}
        else:
            return (), tool_input

    def _handle_tool_error(self, e: ToolException) -> Any:
        """Handle the content of the ToolException thrown."""
        observation = None
        if not self.handle_tool_error:
            raise e
        elif isinstance(self.handle_tool_error, bool):
            if e.args:
                observation = e.args[0]
            else:
                observation = "Tool execution error"
        elif isinstance(self.handle_tool_error, str):
            observation = self.handle_tool_error
        elif callable(self.handle_tool_error):
            observation = self.handle_tool_error(e)
        else:
            raise ValueError(
                f"Got unexpected type of `handle_tool_error`. Expected bool, str "
                f"or callable. Received: {self.handle_tool_error}"
            )
        return observation

    def to_langchain_format(self) -> LCTool:
        """Convert this tool to Langchain format to use with its agent"""
        return LCTool(name=self.name, description=self.description, func=self.run)

    def run(
        self,
        tool_input: Union[str, Dict],
        verbose: Optional[bool] = None,
        **kwargs: Any,
    ) -> Any:
        """Run the tool."""
        parsed_input = self._parse_input(tool_input)
        # TODO (verbose_): Add logging
        try:
            tool_args, tool_kwargs = self._to_args_and_kwargs(parsed_input)
            call_kwargs = {**kwargs, **tool_kwargs}
            observation = self._run_tool(*tool_args, **call_kwargs)
        except ToolException as e:
            observation = self._handle_tool_error(e)
            return observation
        else:
            return observation

    @classmethod
    def from_langchain_format(cls, langchain_tool: LCTool) -> "BaseTool":
        """Wrapper for Langchain Tool"""
        new_tool = BaseTool(
            name=langchain_tool.name, description=langchain_tool.description
        )
        new_tool._run_tool = langchain_tool._run  # type: ignore
        return new_tool


class ComponentTool(BaseTool):
    """Wrapper around other BaseComponent to use it as a tool

    Args:
        component: BaseComponent-based component to wrap
        postprocessor: Optional postprocessor for the component output
    """

    component: BaseComponent
    postprocessor: Optional[Callable] = None

    def _run_tool(self, *args: Any, **kwargs: Any) -> Any:
        output = self.component(*args, **kwargs)
        if self.postprocessor:
            output = self.postprocessor(output)

        return output
