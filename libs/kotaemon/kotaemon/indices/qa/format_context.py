import html
from functools import partial

import tiktoken

from kotaemon.base import BaseComponent, Document, RetrievedDocument
from kotaemon.indices.splitters import TokenSplitter

EVIDENCE_MODE_TEXT = 0
EVIDENCE_MODE_TABLE = 1
EVIDENCE_MODE_CHATBOT = 2
EVIDENCE_MODE_FIGURE = 3


class PrepareEvidencePipeline(BaseComponent):
    """Prepare the evidence text from the list of retrieved documents

    This step usually happens after `DocumentRetrievalPipeline`.

    Args:
        trim_func: a callback function or a BaseComponent, that splits a large
            chunk of text into smaller ones. The first one will be retained.
    """

    max_context_length: int = 32000
    trim_func: TokenSplitter | None = None

    def run(self, docs: list[RetrievedDocument]) -> Document:
        evidence = ""
        images = []
        table_found = 0
        evidence_modes = []

        evidence_trim_func = (
            self.trim_func
            if self.trim_func
            else TokenSplitter(
                chunk_size=self.max_context_length,
                chunk_overlap=0,
                separator=" ",
                tokenizer=partial(
                    tiktoken.encoding_for_model("gpt-3.5-turbo").encode,
                    allowed_special=set(),
                    disallowed_special="all",
                ),
            )
        )

        for _, retrieved_item in enumerate(docs):
            retrieved_content = ""
            page = retrieved_item.metadata.get("page_label", None)
            source = filename = retrieved_item.metadata.get("file_name", "-")
            if page:
                source += f" (Page {page})"
            if retrieved_item.metadata.get("type", "") == "table":
                evidence_modes.append(EVIDENCE_MODE_TABLE)
                if table_found < 5:
                    retrieved_content = retrieved_item.metadata.get(
                        "table_origin", retrieved_item.text
                    )
                    if retrieved_content not in evidence:
                        table_found += 1
                        evidence += (
                            f"<br><b>Table from {source}</b>\n"
                            + retrieved_content
                            + "\n<br>"
                        )
            elif retrieved_item.metadata.get("type", "") == "chatbot":
                evidence_modes.append(EVIDENCE_MODE_CHATBOT)
                retrieved_content = retrieved_item.metadata["window"]
                evidence += (
                    f"<br><b>Chatbot scenario from {filename} (Row {page})</b>\n"
                    + retrieved_content
                    + "\n<br>"
                )
            elif retrieved_item.metadata.get("type", "") == "image":
                evidence_modes.append(EVIDENCE_MODE_FIGURE)
                retrieved_content = retrieved_item.metadata.get("image_origin", "")
                retrieved_caption = html.escape(retrieved_item.get_content())
                evidence += (
                    f"<br><b>Figure from {source}</b>\n"
                    + "<img width='85%' src='<src>' "
                    + f"alt='{retrieved_caption}'/>"
                    + "\n<br>"
                )
                images.append(retrieved_content)
            else:
                if "window" in retrieved_item.metadata:
                    retrieved_content = retrieved_item.metadata["window"]
                else:
                    retrieved_content = retrieved_item.text
                retrieved_content = retrieved_content.replace("\n", " ")
                if retrieved_content not in evidence:
                    evidence += (
                        f"<br><b>Content from {source}: </b> "
                        + retrieved_content
                        + " \n<br>"
                    )

        # resolve evidence mode
        evidence_mode = EVIDENCE_MODE_TEXT
        if EVIDENCE_MODE_FIGURE in evidence_modes:
            evidence_mode = EVIDENCE_MODE_FIGURE
        elif EVIDENCE_MODE_TABLE in evidence_modes:
            evidence_mode = EVIDENCE_MODE_TABLE

        # trim context by trim_len
        print("len (original)", len(evidence))
        if evidence:
            texts = evidence_trim_func([Document(text=evidence)])
            evidence = texts[0].text
            print("len (trimmed)", len(evidence))

        return Document(content=(evidence_mode, evidence, images))
