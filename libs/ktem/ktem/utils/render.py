import markdown


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
        return markdown.markdown(text, extensions=["markdown.extensions.tables"])

    @staticmethod
    def highlight(text: str) -> str:
        """Highlight text"""
        return f"<mark>{text}</mark>"
