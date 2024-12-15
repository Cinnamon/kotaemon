from copy import deepcopy
from functools import cached_property
from typing import Any

from decouple import config
from llama_index.core.readers.base import BaseReader
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


class ExtensionManager:
    """Pool of loaders for extensions"""

    def __init__(self, factory: ReaderFactory | None = None):
        self.factory = factory or ReaderFactory()
        self._supported, self._default_index = self._init_supported()

    def get_current_loader(self) -> dict[str, BaseReader]:
        return deepcopy(
            {
                k: self.get_selected_loader_by_extension(k)[0]
                for k, _ in self._supported.items()
            }
        )

    def _init_supported(self) -> tuple[dict[str, list[BaseReader]], dict[str, str]]:
        supported: dict[str, list[BaseReader]] = {
            ".xlsx": [self.factory.pandas_excel],
            ".docx": [self.factory.unstructured],
            ".pptx": [self.factory.unstructured],
            ".xls": [self.factory.unstructured],
            ".doc": [self.factory.unstructured],
            ".html": [self.factory.html],
            ".mhtml": [self.factory.mhtml],
            ".png": [
                self.factory.unstructured,
                self.factory.gocr,
                self.factory.docling,
            ],
            ".jpeg": [
                self.factory.unstructured,
                self.factory.gocr,
                self.factory.docling,
            ],
            ".jpg": [
                self.factory.unstructured,
                self.factory.gocr,
                self.factory.docling,
            ],
            ".tiff": [self.factory.unstructured, self.factory.docling],
            ".tif": [self.factory.unstructured, self.factory.docling],
            ".pdf": [
                self.factory.pdf_thumbnail,
                self.factory.adobe,
                self.factory.azuredi,
                self.factory.docling,
            ],
            ".txt": [self.factory.txt],
            ".md": [self.factory.txt],
        }

        default_index = {
            k: ExtensionManager.get_loader_name(vs[0]) for k, vs in supported.items()
        }

        return supported, default_index

    def load(self, settings: dict, prefix="extension"):
        for key, value in settings.items():
            if not key.startswith(prefix):
                continue
            extension = key.replace("extension.", "")
            if extension in self._supported:
                # Update the default index
                # Only if it's in supported list
                supported_loader_names = self.get_loaders_by_extension(extension)[1]
                if value in supported_loader_names:
                    self._default_index[extension] = value
                else:
                    print(
                        f"[{extension}]Can not find loader: {value} from list of "
                        f"supported extensions: {supported_loader_names}"
                    )

    @staticmethod
    def get_loader_name(loader: BaseReader) -> str:
        return loader.__class__.__name__

    def get_supported_extensions(self):
        return list(self._supported.keys())

    def get_loaders_by_extension(
        self, extension: str
    ) -> tuple[list[BaseReader], list[str]]:
        loaders = self._supported[extension]
        loaders_name = [self.get_loader_name(loader) for loader in loaders]
        return loaders, loaders_name

    def get_selected_loader_by_extension(
        self, extension: str
    ) -> tuple[BaseReader, str]:
        supported_loaders: list[BaseReader] = self._supported[extension]

        for loader in supported_loaders:
            loader_name = self.get_loader_name(loader)

            if loader_name == self._default_index[extension]:
                return loader, loader_name

        raise Exception(f"can not find the selected loader for extension: {extension}")

    def generate_gradio_settings(self) -> dict[str, Any]:
        """Generates the settings dictionary for use in Gradio."""
        settings = {}

        for extension, loaders in self._supported.items():
            current_loader: str = self._default_index[extension]
            loaders_choices: list[str] = [
                self.get_loader_name(loader) for loader in loaders
            ]

            settings[extension] = {
                "name": f"Loader {extension}",
                "value": current_loader,
                "choices": loaders_choices,
                "component": "dropdown",  # You can customize this to "radio" if needed
            }

        return settings


extension_manager = ExtensionManager()
