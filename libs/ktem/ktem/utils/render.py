import os

import markdown
from fast_langdetect import detect

from kotaemon.base import RetrievedDocument

BASE_PATH = os.environ.get("GR_FILE_ROOT_PATH", "")


def is_close(val1, val2, tolerance=1e-9):
    return abs(val1 - val2) <= tolerance


def replace_mardown_header(text: str) -> str:
    textlines = text.splitlines()
    newlines = []
    for line in textlines:
        if line.startswith("#"):
            line = "<strong>" + line.replace("#", "") + "</strong>"
        if line.startswith("=="):
            line = ""
        newlines.append(line)

    return "\n".join(newlines)


def get_header(doc: RetrievedDocument) -> str:
    """Get the header for the document"""
    header = ""
    if "page_label" in doc.metadata:
        header += f" [Page {doc.metadata['page_label']}]"

    header += f" {doc.metadata.get('file_name', '<evidence>')}"
    return header.strip()


class Render:
    """Default text rendering into HTML for the UI"""

    @staticmethod
    def collapsible(header, content, open: bool = False) -> str:
        """Render an HTML friendly collapsible section"""
        o = " open" if open else ""
        return (
            f"<details class='evidence' {o}><summary>"
            f"{header}</summary>{content}"
            "</details><br>"
        )

    @staticmethod
    def table(text: str) -> str:
        """Render table from markdown format into HTML"""
        text = replace_mardown_header(text)
        return markdown.markdown(
            text,
            extensions=[
                "markdown.extensions.tables",
                "markdown.extensions.fenced_code",
            ],
        )

    @staticmethod
    def table_preserve_linebreaks(text: str) -> str:
        """Render table from markdown format into HTML"""
        return markdown.markdown(
            text,
            extensions=[
                "markdown.extensions.tables",
                "markdown.extensions.fenced_code",
            ],
        ).replace("\n", "<br>")

    @staticmethod
    def preview(
        html_content: str,
        doc: RetrievedDocument,
        highlight_text: str | None = None,
    ) -> str:
        text = doc.content
        pdf_path = doc.metadata.get("file_path", "")

        if not os.path.isfile(pdf_path):
            print(f"pdf-path: {pdf_path} does not exist")
            return html_content

        is_pdf = doc.metadata.get("file_type", "") == "application/pdf"
        page_idx = int(doc.metadata.get("page_label", 1))

        if not is_pdf:
            print("Document is not pdf")
            return html_content

        if page_idx < 0:
            print("Fail to extract page number")
            return html_content

        if not highlight_text:
            try:
                lang = detect(text.replace("\n", " "))["lang"]
                if lang not in ["ja", "cn"]:
                    highlight_words = [
                        t[:-1] if t.endswith("-") else t for t in text.split("\n")
                    ]
                    highlight_text = highlight_words[0]
                    phrase = "true"
                else:
                    phrase = "false"

                highlight_text = (
                    text.replace("\n", "").replace('"', "").replace("'", "")
                )
            except Exception as e:
                print(e)
                highlight_text = text
        else:
            phrase = "true"

        return f"""
        {html_content}
        <a href="#" class="pdf-link" data-src="{BASE_PATH}/file={pdf_path}" data-page="{page_idx}" data-search="{highlight_text}" data-phrase="{phrase}">
            [Preview]
        </a>
        """  # noqa

    @staticmethod
    def highlight(text: str, elem_id: str | None = None) -> str:
        """Highlight text"""
        id_text = f" id='mark-{elem_id}'" if elem_id else ""
        return f"<mark{id_text}>{text}</mark>"

    @staticmethod
    def image(url: str, text: str = "") -> str:
        """Render an image"""
        img = f'<img src="{url}"><br>'
        if text:
            caption = f"<p>{text}</p>"
            return f"<figure>{img}{caption}</figure><br>"
        return img

    @staticmethod
    def collapsible_with_header(
        doc: RetrievedDocument,
        open_collapsible: bool = False,
    ) -> str:
        header = f"<i>{get_header(doc)}</i>"
        if doc.metadata.get("type", "") == "image":
            doc_content = Render.image(url=doc.metadata["image_origin"], text=doc.text)
        elif doc.metadata.get("type", "") == "table_raw":
            doc_content = Render.table_preserve_linebreaks(doc.text)
        else:
            doc_content = Render.table(doc.text)

        return Render.collapsible(
            header=Render.preview(header, doc),
            content=doc_content,
            open=open_collapsible,
        )

    @staticmethod
    def collapsible_with_header_score(
        doc: RetrievedDocument,
        override_text: str | None = None,
        highlight_text: str | None = None,
        open_collapsible: bool = False,
    ) -> str:
        """Format the retrieval score and the document"""
        # score from doc_store (Elasticsearch)
        if is_close(doc.score, -1.0):
            vectorstore_score = ""
            text_search_str = " (full-text search)<br>"
        else:
            vectorstore_score = str(round(doc.score, 2))
            text_search_str = "<br>"

        llm_reranking_score = (
            round(doc.metadata["llm_trulens_score"], 2)
            if doc.metadata.get("llm_trulens_score") is not None
            else 0.0
        )
        reranking_score = (
            round(doc.metadata["reranking_score"], 2)
            if doc.metadata.get("reranking_score") is not None
            else 0.0
        )
        item_type_prefix = doc.metadata.get("type", "")
        item_type_prefix = item_type_prefix.capitalize()
        if item_type_prefix:
            item_type_prefix += " from "

        if "raw" in item_type_prefix:
            item_type_prefix = ""

        if llm_reranking_score > 0:
            relevant_score = llm_reranking_score
        elif reranking_score > 0:
            relevant_score = reranking_score
        else:
            relevant_score = 0.0

        rendered_score = Render.collapsible(
            header=f"<b>&emsp;Relevance score</b>: {relevant_score:.1f}",
            content="<b>&emsp;&emsp;Vectorstore score:</b>"
            f" {vectorstore_score}"
            f"{text_search_str}"
            "<b>&emsp;&emsp;LLM relevant score:</b>"
            f" {llm_reranking_score}<br>"
            "<b>&emsp;&emsp;Reranking score:</b>"
            f" {reranking_score}<br>",
        )

        text = doc.text if not override_text else override_text
        if doc.metadata.get("type", "") == "image":
            rendered_doc_content = Render.image(
                url=doc.metadata["image_origin"],
                text=text,
            )
        elif doc.metadata.get("type", "") == "table_raw":
            rendered_doc_content = Render.table_preserve_linebreaks(doc.text)
        else:
            rendered_doc_content = Render.table(text)

        rendered_header = Render.preview(
            f"<i>{item_type_prefix}{get_header(doc)}</i>",
            doc,
            highlight_text=highlight_text,
        )
        rendered_doc_content = (
            f"<div class='evidence-content'>{rendered_doc_content}</div>"
        )

        return Render.collapsible(
            header=rendered_header,
            content=rendered_doc_content,
            open=open_collapsible,
        )
