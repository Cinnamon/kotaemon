import logging
import re
from textwrap import dedent

from ktem.llms.manager import llms

from kotaemon.base import BaseComponent, Document, HumanMessage, Node, SystemMessage
from kotaemon.llms import ChatLLM, PromptTemplate

logger = logging.getLogger(__name__)


MINDMAP_HTML_EXPORT_TEMPLATE = dedent(
    """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Mindmap</title>
    <style>
      svg.markmap {
        width: 100%;
        height: 100vh;
      }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" />
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@0.16"></script>
  </head>
  <body>
    {markmap_div}
  </body>
</html>
"""
)


class CreateMindmapPipeline(BaseComponent):
    """Create a mindmap from the question and context"""

    llm: ChatLLM = Node(default_callback=lambda _: llms.get_default())
    lang: str = "English"

    SYSTEM_PROMPT = """
From now on you will behave as "MapGPT" and, for every text the user will submit, you are going to create a PlantUML mind map file for the inputted text to best describe main ideas. Format it as a code. You don't have to provide a general example for the mind map format before the user inputs the text.
    """  # noqa: E501
    MINDMAP_PROMPT_TEMPLATE = """
Question:
{question}

Context:
{context}

Generate a sample PlantUML mindmap based on the provided question and context above. Only includes context relevant to the question to produce the mindmap.
The mind map MUST be in {lang}.

For mathematical formulas in the mindmap, follow these rules STRICTLY:
1. Use $...$ for inline math formulas (e.g., $E=mc^2$, $n_{{max}}$, $x^2$)
2. For complex formulas with fractions, subscripts, or superscripts, keep them simple and avoid special characters like #, <, >, &, quotes
3. Escape special characters: use \# for #, \< for <, \> for >, \& for &
4. Avoid using double backslashes (\\) - use single backslash for LaTeX commands
5. Keep formulas as short as possible - consider simplifying complex expressions
6. Examples of GOOD formulas:
   - $w^*$ (simple superscript)
   - $n_{{max}}$ (simple subscript)
   - $||w||^2$ (norm notation)
   - $X^T$ (transpose)
   - $\alpha^2$ (Greek letters)
7. Examples of BAD formulas that may cause rendering errors:
   - Complex fractions like $\frac{{a}}{{b}}$ - simplify if possible
   - Multiple nested operations - break into simpler parts
   - Special symbols not supported by PlantUML

Use the template like this:

@startmindmap
* Title
** Item A
*** Item B
**** Item C
*** Item D
@endmindmap
    """  # noqa: E501
    prompt_template: str = MINDMAP_PROMPT_TEMPLATE

    @classmethod
    def convert_uml_to_markdown(cls, text: str) -> str:
        start_phrase = "@startmindmap"
        end_phrase = "@endmindmap"

        try:
            text = text.split(start_phrase)[-1]
            text = text.split(end_phrase)[0]
            text = text.strip().replace("*", "#")
            
            # Fix common PlantUML math rendering issues
            # Remove problematic characters that cause red errors
            
            # Find all math expressions between $...$
            math_expressions = re.findall(r'\$[^$]+\$', text)
            for math_expr in math_expressions:
                # Remove or escape problematic characters within math expressions
                fixed_expr = math_expr
                # Remove # symbols that can cause issues
                fixed_expr = fixed_expr.replace('#', '')
                # Simplify complex fractions if possible
                # Keep the fix localized to the math expression
                text = text.replace(math_expr, fixed_expr)
                
        except IndexError:
            text = ""

        return text

    def run(self, question: str, context: str) -> Document:  # type: ignore
        prompt_template = PromptTemplate(self.prompt_template)
        prompt = prompt_template.populate(
            question=question,
            context=context,
            lang=self.lang,
        )

        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        uml_text = self.llm(messages).text
        markdown_text = self.convert_uml_to_markdown(uml_text)

        return Document(
            text=markdown_text,
        )
