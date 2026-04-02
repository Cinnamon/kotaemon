from kotaemon.agents.codeact.agent import CodeActAgent
from kotaemon.agents.tools import BaseTool
from kotaemon.llms import BaseLLM, PromptTemplate
from kotaemon.agents.typedefs import AgentOutput, AgentStatus, EventFinalResponse
from pydantic import ConfigDict

class MockLLM(BaseLLM):
    """A mock LLM that produces static sequences of outputs for testing CodeActAgent."""
    
    model_config = ConfigDict(extra="allow")
    responses: list[str] = []
    _call_idx: int = 0

    def invoke(self, messages, *args, **kwargs):
        from kotaemon.base import Document
        
        if self._call_idx < len(self.responses):
            text = self.responses[self._call_idx]
            self._call_idx += 1
            return Document(text=text)
        return Document(text="No more responses")


class EchoTool(BaseTool):
    name: str = "echo_tool"
    description: str = "Echoes the query back."

    def _run_tool(self, query):
        return f"ECHO::{query}"


def test_codeact_agent_execution_loop():
    """
    Test that CodeActAgent properly parses python blocks, executes them,
    and breaks correctly when final_answer() is called.
    """
    # Define a sequence of responses from the "LLM"
    # Turn 1: Write some code, wait for observation
    # Turn 2: Receive observation, calculate final answer
    responses = [
        # Turn 1
        "I need to calculate 21 * 2 first.\n"
        "```python\n"
        "x = 21 * 2\n"
        "print('Result is', x)\n"
        "```\n"
        "I'll wait for the interpreter output.",
        
        # Turn 2
        "```python\n"
        "final_answer(x)\n"
        "```"
    ]
    
    llm = MockLLM(responses=responses)
    agent = CodeActAgent(llm=llm, timeout=10)
    
    result = agent.run("What is 21 times 2?")
    
    assert isinstance(result, AgentOutput)
    assert result.status == AgentStatus.FINISHED
    assert result.text == "42"
    assert len(result.intermediate_steps) == 2
    
    # Verify the observation was recorded correctly
    turn1_observation = result.intermediate_steps[0][1]
    assert "Result is 42" in turn1_observation

def test_codeact_agent_planning_loop():
    """
    Test that CodeActAgent properly constructs an initial plan when planning=True
    """
    responses = [
        # Turn 1: Planning Step LLM Response
        "## 1. Facts survey\nWe need to compute 10 * 5\n## 2. Plan\n1. Multiply 10 by 5\n2. Return result.<end_plan>",
        
        # Turn 2: Execution Step LLM Response
        "```python\n"
        "final_answer(10 * 5)\n"
        "```"
    ]
    
    llm = MockLLM(responses=responses)
    agent = CodeActAgent(llm=llm, timeout=10, planning=True)
    
    result = agent.run("What is 10 times 5?")
    
    assert isinstance(result, AgentOutput)
    assert result.status == AgentStatus.FINISHED
    assert result.text == "50"
    
    # Verify the observation was recorded correctly
    # intermediate_steps[0] should be the explicit plan
    assert len(result.intermediate_steps) == 2
    assert result.intermediate_steps[0][0] == "Initial Plan Formulation"
    assert "We need to compute 10 * 5" in result.intermediate_steps[0][1]


def test_codeact_agent_max_iteration_status_stopped():
    responses = [
        "```python\n"
        "print('still thinking')\n"
        "```"
    ]

    llm = MockLLM(responses=responses)
    agent = CodeActAgent(llm=llm, timeout=10, max_iterations=1)

    result = agent.run("Keep working but don't call final_answer.")

    assert isinstance(result, AgentOutput)
    assert result.status == AgentStatus.STOPPED
    assert "Max iterations reached" in result.text


def test_codeact_agent_prompt_supports_lang_placeholder():
    llm = MockLLM(
        responses=[
            "```python\n"
            "final_answer('ok')\n"
            "```"
        ]
    )
    agent = CodeActAgent(llm=llm, timeout=10)
    agent.prompt_template = PromptTemplate(
        "Question: {instruction}\nLanguage: {lang}\n{agent_scratchpad}"
    )

    result = agent.run("Say ok.")

    assert result.status == AgentStatus.FINISHED
    assert result.text == "ok"

    stream_agent = CodeActAgent(
        llm=MockLLM(
            responses=[
                "```python\n"
                "final_answer('ok')\n"
                "```"
            ]
        ),
        timeout=10,
    )
    stream_agent.prompt_template = PromptTemplate(
        "Question: {instruction}\nLanguage: {lang}\n{agent_scratchpad}"
    )
    events = list(stream_agent.stream("Say ok.", max_iterations=1))
    final_event = [e for e in events if isinstance(e, EventFinalResponse)][-1]
    assert final_event.status == AgentStatus.FINISHED
    assert final_event.agent_type == stream_agent.agent_type


def test_codeact_agent_tool_call_from_python_block():
    responses = [
        "I will call the external tool first.\n"
        "```python\n"
        "echo_tool(query='hello')\n"
        "```\n",
        "```python\n"
        "final_answer('done')\n"
        "```",
    ]
    agent = CodeActAgent(llm=MockLLM(responses=responses), timeout=10)
    agent.plugins = [EchoTool()]

    result = agent.run("Test tool call")

    assert result.status == AgentStatus.FINISHED
    assert result.text == "done"
    assert "Tool[echo_tool] output" in result.intermediate_steps[0][1]
    assert "ECHO::hello" in result.intermediate_steps[0][1]


def test_codeact_agent_normalizes_dict_final_answer():
    responses = [
        "```python\n"
        "final_answer({'answer': 'AAPL looks overbought'})\n"
        "```"
    ]
    agent = CodeActAgent(llm=MockLLM(responses=responses), timeout=10)

    result = agent.run("Analyze AAPL.")

    assert result.status == AgentStatus.FINISHED
    assert result.text == "AAPL looks overbought"
