from ktem.llms.manager import llms

from kotaemon.base import BaseComponent
from kotaemon.base.schema import HumanMessage, SystemMessage


class LLMScenarioPipeline(BaseComponent):
    def run(self, query: str, tag_info: str):
        return self.invoke(query, tag_info)

    def get_prompt(self, query: str, tag_info: str):
        messages = [
            SystemMessage(
                content=(
                    "You are a world class algorithm to convert "
                    "user query to structured search query with the meta-tags "
                    "schema below."
                )
            ),
            HumanMessage(content=(f"Tag schema:{tag_info}")),
            HumanMessage(content=f"User query:\n{query}"),
            HumanMessage(
                content=(
                    "Build tag value(s) based on the above context "
                    "to search in the DB."
                )
            ),
            HumanMessage(
                content=(
                    "Output tag name and value in the format: "
                    "(markdown)\n"
                    "| tag name | tag value |\n"
                    "Only output markdown table without explanation."
                )
            ),
        ]
        return messages

    def parse_structure_output(output: str):
        # temporary method LLM output to query value
        output_lines = [line for line in output.split("\n") if "|" in line]
        if output_lines:
            line = output_lines[0]
            search_tag_name, search_tag_value = [
                it.strip() for it in line.split("|") if it.strip()
            ][:2]
            print("Searching for", search_tag_name, search_tag_value)
        else:
            search_tag_name, search_tag_value = None, None

        return {search_tag_name: search_tag_value}

    def invoke(self, query: str, tag_info: str):
        default_llm = llms.get(llms.get_default_name())  # type: ignore
        messages = self.get_prompt(query, tag_info)
        kwargs = {
            "max_tokens": 100,
        }
        try:
            llm_output = default_llm(messages, **kwargs).text
        except Exception as e:
            print(e)
            return None

        return llm_output
