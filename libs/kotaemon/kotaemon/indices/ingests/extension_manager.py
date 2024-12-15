from copy import deepcopy

from decouple import config
from llama_index.core.readers.base import BaseReader
from theflow.settings import settings as flowsettings

from kotaemon.loaders import (
    AdobeReader,
    AzureAIDocumentIntelligenceLoader,
    DirectoryReader,
    HtmlReader,
    MathpixPDFReader,
    MhtmlReader,
    OCRReader,
    PandasExcelReader,
    PDFThumbnailReader,
    TxtReader,
    UnstructuredReader,
    ImageReader,
    GOCR2ImageReader
)


unstructured = UnstructuredReader()
adobe_reader = AdobeReader()
azure_reader = AzureAIDocumentIntelligenceLoader(
    endpoint=str(config("AZURE_DI_ENDPOINT", default="")),
    credential=str(config("AZURE_DI_CREDENTIAL", default="")),
    cache_dir=getattr(flowsettings, "KH_MARKDOWN_OUTPUT_DIR", None),
)
adobe_reader.vlm_endpoint = azure_reader.vlm_endpoint = getattr(
    flowsettings, "KH_VLM_ENDPOINT", ""
)

KH_DEFAULT_FILE_EXTRACTORS: dict[str, BaseReader] = {
    ".xlsx": PandasExcelReader(),
    ".docx": unstructured,
    ".pptx": unstructured,
    ".xls": unstructured,
    ".doc": unstructured,
    ".html": HtmlReader(),
    ".mhtml": MhtmlReader(),
    ".png": ImageReader(),
    ".jpeg": ImageReader(),
    ".jpg": ImageReader(),
    ".tiff": unstructured,
    ".tif": unstructured,
    ".pdf": PDFThumbnailReader(),
    ".txt": TxtReader(),
    ".md": TxtReader(),
}


class ExtensionManager:
    """Pool of loaders for extensions"""
    def __init__(self):
        self._supported, self._default_index = self._init_supported()

    def get_current_loader(self) -> dict[str, BaseReader]:
        return deepcopy({k: self.get_selected_loader_by_extension(k)[0] for k, _ in self._supported.items()})

    @staticmethod
    def _init_supported() -> tuple[dict[str, list[BaseReader]], dict[str, str]]:
        supported: dict[str, list[BaseReader]] = {
            ".xlsx": [PandasExcelReader()],
            ".docx": [unstructured],
            ".pptx": [unstructured],
            ".xls": [unstructured],
            ".doc": [unstructured],
            ".html": [HtmlReader()],
            ".mhtml": [MhtmlReader()],
            ".png": [GOCR2ImageReader(), unstructured],
            ".jpeg": [GOCR2ImageReader(), unstructured],
            ".jpg": [GOCR2ImageReader(), unstructured],
            ".tiff": [unstructured],
            ".tif": [unstructured],
            ".pdf": [PDFThumbnailReader()],
            ".txt": [TxtReader()],
            ".md": [TxtReader()],
        }

        default_index = {
            k: ExtensionManager.get_loader_name(vs[0])
            for k, vs
            in supported.items()
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
                    print(f"[{extension}]Can not find loader: {value} from list of "
                          f"supported extensions: {supported_loader_names}")

    @staticmethod
    def get_loader_name(loader: BaseReader) -> str:
        return loader.__class__.__name__

    def get_supported_extensions(self):
        return list(self._supported.keys())

    def get_loaders_by_extension(self, extension: str) -> tuple[list[BaseReader], list[str]]:
        loaders = self._supported[extension]
        loaders_name = [self.get_loader_name(loader) for loader in loaders]
        return loaders, loaders_name

    def get_selected_loader_by_extension(self, extension: str) -> tuple[BaseReader, str]:
        supported_loaders: list[BaseReader] = self._supported[extension]

        for loader in supported_loaders:
            loader_name = self.get_loader_name(loader)

            if loader_name == self._default_index[extension]:
                return loader, loader_name

        raise Exception(f"can not find the selected loader for extension: {extension}")

    def generate_gradio_settings(self) -> dict[str, dict]:
        """Generates the settings dictionary for use in Gradio."""
        settings = {}

        for extension, loaders in self._supported.items():
            current_loader: str = self._default_index[extension]
            loaders_choices: list[str] = [self.get_loader_name(loader) for loader in loaders]

            settings[extension] = {
                "name": f"Loader {extension}",
                "value": current_loader,
                "choices": loaders_choices,
                "component": "dropdown",  # You can customize this to "radio" if needed
            }

        return settings


extension_manager = ExtensionManager()


if __name__ == "__main__":
    print(extension_manager.get_loaders_by_extension(".xlsx"))
