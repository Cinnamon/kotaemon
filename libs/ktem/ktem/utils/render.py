import os.path

import markdown
from fast_langdetect import detect

from kotaemon.base import RetrievedDocument


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
        return f"<details{o}><summary>{header}</summary>{content}</details><br>"

    @staticmethod
    def table(text: str) -> str:
        """Render table from markdown format into HTML"""
        text = replace_mardown_header(text)
        return markdown.markdown(text, extensions=["markdown.extensions.tables"])

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
                print("lang", lang)
                if lang not in ["ja", "cn"]:
                    highlight_words = [
                        t[:-1] if t.endswith("-") else t for t in text.split("\n")
                    ]
                    highlight_text = highlight_words[0]
                    phrase = "true"
                else:
                    highlight_text = text.replace("\n", "")
                    phrase = "false"

                print("highlight_text", highlight_text, phrase)
            except Exception as e:
                print(e)
                highlight_text = text
        else:
            phrase = "true"

        return f"""
        {html_content}
        <a href="#" class="pdf-link" data-src="/file={pdf_path}" data-page="{page_idx}" data-search="{highlight_text}" data-phrase="{phrase}">
            [Preview]
        </a>
        """  # noqa

    @staticmethod
    def highlight(text: str) -> str:
        """Highlight text"""
        return f"<mark>{text}</mark>"

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
        cohere_reranking_score = (
            round(doc.metadata["cohere_reranking_score"], 2)
            if doc.metadata.get("cohere_reranking_score") is not None
            else 0.0
        )
        item_type_prefix = doc.metadata.get("type", "")
        item_type_prefix = item_type_prefix.capitalize()
        if item_type_prefix:
            item_type_prefix += " from "

        rendered_score = Render.collapsible(
            header=f"<b>&emsp;Relevance score</b>: {llm_reranking_score}",
            content="<b>&emsp;&emsp;Vectorstore score:</b>"
            f" {vectorstore_score}"
            f"{text_search_str}"
            "<b>&emsp;&emsp;LLM relevant score:</b>"
            f" {llm_reranking_score}<br>"
            "<b>&emsp;&emsp;Reranking score:</b>"
            f" {cohere_reranking_score}<br>",
        )

        text = doc.text if not override_text else override_text
        if doc.metadata.get("type", "") == "image":
            rendered_doc_content = Render.image(
                url=doc.metadata["image_origin"],
                text=text,
            )
        else:
            rendered_doc_content = Render.table(text)

        rendered_header = Render.preview(
            f"<i>{item_type_prefix}{get_header(doc)}</i>"
            f" [score: {llm_reranking_score}]",
            doc,
            highlight_text=highlight_text,
        )

        return Render.collapsible(
            header=rendered_header,
            content=rendered_score + rendered_doc_content,
            open=open_collapsible,
        )
