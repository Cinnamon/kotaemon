import asyncio
import os
import tempfile
from copy import deepcopy
from typing import Optional

import gradio as gr
from ktem.components import llms, reasonings
from ktem.db.models import Conversation, Source, engine
from ktem.indexing.base import BaseIndex
from ktem.reasoning.simple import DocumentRetrievalPipeline
from sqlmodel import Session, select
from theflow.settings import settings as app_settings
from theflow.utils.modules import import_dotted_string


def create_pipeline(settings: dict, files: Optional[list] = None):
    """Create the pipeline from settings

    Args:
        settings: the settings of the app
        files: the list of file ids that will be served as context. If None, then
            consider using all files

    Returns:
        the pipeline objects
    """

    reasoning_mode = settings["reasoning.use"]
    reasoning_cls = reasonings[reasoning_mode]
    pipeline = reasoning_cls.get_pipeline(settings, files=files)

    if settings["reasoning.use"] in ["rewoo", "react"]:
        from kotaemon.agents import ReactAgent, RewooAgent

        llm = (
            llms["gpt4"]
            if settings["answer_simple_llm_model"] == "gpt-4"
            else llms["gpt35"]
        )
        tools = []
        tools_keys = (
            "answer_rewoo_tools"
            if settings["reasoning.use"] == "rewoo"
            else "answer_react_tools"
        )
        for tool in settings[tools_keys]:
            if tool == "llm":
                from kotaemon.agents import LLMTool

                tools.append(LLMTool(llm=llm))
            elif tool == "docsearch":
                from kotaemon.agents import ComponentTool

                filenames = ""
                if files:
                    with Session(engine) as session:
                        statement = select(Source).where(
                            Source.id.in_(files)  # type: ignore
                        )
                        results = session.exec(statement).all()
                        filenames = (
                            "The file names are: "
                            + "  ".join([result.name for result in results])
                            + ". "
                        )

                retrieval_pipeline = DocumentRetrievalPipeline()
                retrieval_pipeline.set_run(
                    {
                        ".top_k": int(settings["retrieval_number"]),
                        ".mmr": settings["retrieval_mmr"],
                        ".doc_ids": files,
                    },
                    temp=True,
                )
                tool = ComponentTool(
                    name="docsearch",
                    description=(
                        "A vector store that searches for similar and "
                        "related content "
                        f"in a document. {filenames}"
                        "The result is a huge chunk of text related "
                        "to your search but can also "
                        "contain irrelevant info."
                    ),
                    component=retrieval_pipeline,
                    postprocessor=lambda docs: "\n\n".join(
                        [doc.text.replace("\n", " ") for doc in docs]
                    ),
                )
                tools.append(tool)
            elif tool == "google":
                from kotaemon.agents import GoogleSearchTool

                tools.append(GoogleSearchTool())
            elif tool == "wikipedia":
                from kotaemon.agents import WikipediaTool

                tools.append(WikipediaTool())
            else:
                raise NotImplementedError(f"Unknown tool: {tool}")

        if settings["reasoning.use"] == "rewoo":
            pipeline = RewooAgent(
                planner_llm=llm,
                solver_llm=llm,
                plugins=tools,
            )
            pipeline.set_run({".use_citation": True})
        else:
            pipeline = ReactAgent(
                llm=llm,
                plugins=tools,
            )

    return pipeline


async def chat_fn(chat_input, chat_history, files, settings):
    """Chat function"""
    queue: asyncio.Queue[Optional[dict]] = asyncio.Queue()

    # construct the pipeline
    pipeline = create_pipeline(settings, files)
    pipeline.set_output_queue(queue)

    asyncio.create_task(pipeline(chat_input))
    text, refs = "", ""

    while True:
        try:
            response = queue.get_nowait()
        except Exception:
            await asyncio.sleep(0)
            continue

        if response is None:
            break

        if "output" in response:
            text += response["output"]
        if "evidence" in response:
            refs += response["evidence"]

        yield "", chat_history + [(chat_input, text)], refs


def is_liked(convo_id, liked: gr.LikeData):
    with Session(engine) as session:
        statement = select(Conversation).where(Conversation.id == convo_id)
        result = session.exec(statement).one()

        data_source = deepcopy(result.data_source)
        likes = data_source.get("likes", [])
        likes.append([liked.index, liked.value, liked.liked])
        data_source["likes"] = likes

        result.data_source = data_source
        session.add(result)
        session.commit()


def update_data_source(convo_id, selected_files, messages):
    """Update the data source"""
    if not convo_id:
        gr.Warning("No conversation selected")
        return

    with Session(engine) as session:
        statement = select(Conversation).where(Conversation.id == convo_id)
        result = session.exec(statement).one()

        data_source = result.data_source
        result.data_source = {
            "files": selected_files,
            "messages": messages,
            "likes": deepcopy(data_source.get("likes", [])),
        }
        session.add(result)
        session.commit()


def load_files():
    options = []
    with Session(engine) as session:
        statement = select(Source)
        results = session.exec(statement).all()
        for result in results:
            options.append((result.name, result.id))

    return options


def index_fn(files, reindex: bool, selected_files, settings):
    """Upload and index the files

    Args:
        files: the list of files to be uploaded
        reindex: whether to reindex the files
        selected_files: the list of files already selected
        settings: the settings of the app
    """
    gr.Info(f"Start indexing {len(files)} files...")

    # get the pipeline
    indexing_cls: BaseIndex = import_dotted_string(app_settings.KH_INDEX, safe=False)
    indexing_pipeline = indexing_cls.get_pipeline(settings)

    output_nodes, file_ids = indexing_pipeline(files, reindex=reindex)
    gr.Info(f"Finish indexing into {len(output_nodes)} chunks")

    # download the file
    text = "\n\n".join([each.text for each in output_nodes])
    handler, file_path = tempfile.mkstemp(suffix=".txt")
    with open(file_path, "w") as f:
        f.write(text)
    os.close(handler)

    if isinstance(selected_files, list):
        output = selected_files + file_ids
    else:
        output = file_ids

    file_list = load_files()

    return (
        gr.update(value=file_path, visible=True),
        gr.update(value=output, choices=file_list),
    )
