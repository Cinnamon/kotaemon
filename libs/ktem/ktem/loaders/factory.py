from functools import cached_property

from decouple import config
from theflow.settings import settings as flowsettings

from kotaemon.loaders import (
    AdobeReader,
    AzureAIDocumentIntelligenceLoader,
    DoclingReader,
    GOCR2ImageReader,
    HtmlReader,
    MathpixPDFReader,
    MhtmlReader,
    PandasExcelReader,
    PDFThumbnailReader,
    TxtReader,
    UnstructuredReader,
    WebReader,
)


class ReaderFactory:
    @cached_property
    def mathpix_pdf(self) -> MathpixPDFReader:
        return MathpixPDFReader()

    @cached_property
    def web(self) -> WebReader:
        return WebReader()

    @cached_property
    def unstructured(self) -> UnstructuredReader:
        return UnstructuredReader()

    @cached_property
    def adobe(self) -> AdobeReader:
        adobe_reader = AdobeReader()
        adobe_reader.vlm_endpoint = getattr(flowsettings, "KH_VLM_ENDPOINT", "")
        return adobe_reader

    @cached_property
    def azuredi(self) -> AzureAIDocumentIntelligenceLoader:
        azuredi_reader = AzureAIDocumentIntelligenceLoader(
            endpoint=str(config("AZURE_DI_ENDPOINT", default="")),
            credential=str(config("AZURE_DI_CREDENTIAL", default="")),
            cache_dir=getattr(flowsettings, "KH_MARKDOWN_OUTPUT_DIR", None),
        )
        azuredi_reader.vlm_endpoint = getattr(flowsettings, "KH_VLM_ENDPOINT", "")
        return azuredi_reader

    @cached_property
    def pandas_excel(self) -> PandasExcelReader:
        return PandasExcelReader()

    @cached_property
    def html(self) -> HtmlReader:
        return HtmlReader()

    @cached_property
    def mhtml(self) -> MhtmlReader:
        return MhtmlReader()

    @cached_property
    def gocr(self) -> GOCR2ImageReader:
        return GOCR2ImageReader()

    @cached_property
    def txt(self) -> TxtReader:
        return TxtReader()

    @cached_property
    def docling(self) -> DoclingReader:
        return DoclingReader()

    @cached_property
    def pdf_thumbnail(self) -> PDFThumbnailReader:
        return PDFThumbnailReader()
