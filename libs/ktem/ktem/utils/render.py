import os.path

import markdown

from kotaemon.base import RetrievedDocument


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
    def create_popup_modal_element() -> str:
        return """
        <!-- The Modal -->
        <div id="pdf-modal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <span class="close">&times;</span>
                </div>
                <div class="modal-body">
                    <pdfjs-viewer-element id="pdf-viewer" viewer-path="/file={PDFJS_PREBUILT_DIR}" locale="en">
                    </pdfjs-viewer-element>
                </div>
            </div>
        </div>
        """

    @staticmethod
    def update_preview(html_content: str, doc: RetrievedDocument) -> str:
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

        return f"""
        <a href="#" class="pdf-link" data-src="/file={pdf_path}" data-page="{page_idx}" data-search="{text}">
            [Preview]
        </a>
        {html_content}
        """

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
