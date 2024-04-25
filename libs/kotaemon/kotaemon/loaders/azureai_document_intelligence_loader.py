from pathlib import Path
from typing import Optional

from kotaemon.base import Document, Param

from .base import BaseReader


class AzureAIDocumentIntelligenceLoader(BaseReader):
    """Utilize Azure AI Document Intelligence to parse document

    As of April 24, the supported file formats are: pdf, jpeg/jpg, png, bmp, tiff,
    heif, docx, xlsx, pptx and html.
    """

    _dependencies = ["azure-ai-documentintelligence"]

    endpoint: str = Param("Endpoint of Azure AI Document Intelligence")
    credential: str = Param("Credential of Azure AI Document Intelligence")
    model: str = Param(
        "prebuilt-layout",
        help=(
            "Model to use for document analysis. Default is prebuilt-layout. "
            "As of April 24, you can view the supported models [here]"
            "(https://learn.microsoft.com/en-us/azure/ai-services/"
            "document-intelligence/concept-model-overview?view=doc-intel-4.0.0"
            "#model-analysis-features)"
        ),
    )

    @Param.auto(depends_on=["endpoint", "credential"])
    def client_(self):
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
        except ImportError:
            raise ImportError("Please install azure-ai-documentintelligence")

        return DocumentIntelligenceClient(
            self.endpoint, AzureKeyCredential(self.credential)
        )

    def run(
        self, file_path: str | Path, extra_info: Optional[dict] = None, **kwargs
    ) -> list[Document]:
        return self.load_data(Path(file_path), extra_info=extra_info, **kwargs)

    def load_data(
        self, file_path: Path, extra_info: Optional[dict] = None, **kwargs
    ) -> list[Document]:
        metadata = extra_info or {}
        with open(file_path, "rb") as fi:
            poller = self.client_.begin_analyze_document(
                self.model,
                analyze_request=fi,
                content_type="application/octet-stream",
                output_content_format="markdown",
            )
            result = poller.result()

        return [Document(content=result.content, metadata=metadata)]
