import langchain_core.messages
from ktem.llms.manager import llms
from ktem.reasoning.prompt_optimization.rewrite_question import (
    DEFAULT_REWRITE_PROMPT,
    RewriteQuestionPipeline,
)
from langchain.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    SemanticSimilarityExampleSelector,
)
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from theflow.settings import settings as flowsettings

from kotaemon.base import AIMessage, Document, HumanMessage, Node, SystemMessage
from kotaemon.llms import ChatLLM


class FewshotRewriteQuestionPipeline(RewriteQuestionPipeline):
    """Rewrite user question

    Args:
        llm: the language model to rewrite question
        rewrite_template: the prompt template for llm to paraphrase a text input
        lang: the language of the answer. Currently support English and Japanese
    """

    llm: ChatLLM = Node(default_callback=lambda _: llms.get_default())
    rewrite_template: str = DEFAULT_REWRITE_PROMPT
    lang: str = "English"
    final_prompt: ChatPromptTemplate

    def create_example_selector(
        self, examples, k: int = getattr(flowsettings, "N_PROMPT_OPT_EXAMPLES", 0)
    ):
        if not examples:
            return None

        embeddings = OpenAIEmbeddings(
            openai_api_key=getattr(flowsettings, "KH_EMBEDDINGS")["openai"]["spec"][
                "api_key"
            ],
            openai_api_type="openai",
            openai_api_base=getattr(flowsettings, "KH_EMBEDDINGS")["openai"]["spec"][
                "base_url"
            ],
            openai_api_version=getattr(flowsettings, "KH_EMBEDDINGS")["openai"]["spec"][
                "api_version"
            ],
        )
        vectorstore = Chroma(
            "rephrase_question",
            embeddings,
            persist_directory=str(getattr(flowsettings, "KH_APP_DATA_DIR")),
        )
        example_selector = SemanticSimilarityExampleSelector(
            vectorstore=vectorstore,
            k=k,
        )

        return example_selector

    def create_prompt(self, examples, example_selector):
        example_prompt = ChatPromptTemplate.from_messages(
            [
                ("human", self.rewrite_template.replace("{lang}", self.lang)),
                ("ai", "{rewritten_question}"),
            ]
        )

        if example_selector is not None:
            few_shot_prompt = FewShotChatMessagePromptTemplate(
                example_prompt=example_prompt,
                input_variables=["question"],
                example_selector=example_selector,
            )
        elif examples:
            few_shot_prompt = FewShotChatMessagePromptTemplate(
                example_prompt=example_prompt,
                examples=examples,
            )

        final_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are a helpful assistant"),
                few_shot_prompt,
                ("human", self.rewrite_template.replace("{lang}", self.lang)),
            ]
        )

        return final_prompt

    @classmethod
    def get_pipeline(cls, examples):
        pipeline = cls()
        example_selector = pipeline.create_example_selector(examples)
        prompt = pipeline.create_prompt(examples, example_selector)
        pipeline.final_prompt = prompt

        return pipeline

    def run(self, question: str) -> Document:  # type: ignore
        messages = self.final_prompt.format_messages(question=question)
        new_messages = []
        for message in messages:
            if isinstance(message, langchain_core.messages.human.HumanMessage):
                new_messages.append(HumanMessage(content=message.content))
            elif isinstance(message, langchain_core.messages.system.SystemMessage):
                new_messages.append(SystemMessage(content=message.content))
            elif isinstance(message, langchain_core.messages.ai.AIMessage):
                new_messages.append(AIMessage(content=message.content))

        result = self.llm(new_messages)
        return result
