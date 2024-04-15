# flake8: noqa

from kotaemon.llms import PromptTemplate

zero_shot_react_prompt = PromptTemplate(
    template="""Answer the following questions as best you can. Give answer in {lang}. You have access to the following tools:
{tool_description}
Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do

Action: the action to take, should be one of [{tool_names}]

Action Input: the input to the action, should be different from the action input of the same action in previous steps.

Observation: the result of the action

... (this Thought/Action/Action Input/Observation can repeat N times)
#Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin! After each Action Input.

Question: {instruction}
Thought:{agent_scratchpad}
    """
)
