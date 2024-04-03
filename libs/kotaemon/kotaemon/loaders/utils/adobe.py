# need pip install pdfservices-sdk==2.3.0

import base64
import json
import logging
import os
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Union

import pandas as pd
from decouple import config

from kotaemon.loaders.utils.gpt4v import generate_gpt4v


def request_adobe_service(file_path: str, output_path: str = "") -> str:
    """Main function to call the adobe service, and unzip the results.
    Args:
        file_path (str): path to the pdf file
        output_path (str): path to store the results

    Returns:
        output_path (str): path to the results

    """
    try:
        from adobe.pdfservices.operation.auth.credentials import Credentials
        from adobe.pdfservices.operation.exception.exceptions import (
            SdkException,
            ServiceApiException,
            ServiceUsageException,
        )
        from adobe.pdfservices.operation.execution_context import ExecutionContext
        from adobe.pdfservices.operation.io.file_ref import FileRef
        from adobe.pdfservices.operation.pdfops.extract_pdf_operation import (
            ExtractPDFOperation,
        )
        from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_element_type import (  # noqa: E501
            ExtractElementType,
        )
        from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_pdf_options import (  # noqa: E501
            ExtractPDFOptions,
        )
        from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_renditions_element_type import (  # noqa: E501
            ExtractRenditionsElementType,
        )
    except ImportError:
        raise ImportError(
            "pdfservices-sdk is not installed. "
            "Please install it by running `pip install pdfservices-sdk"
            "@git+https://github.com/niallcm/pdfservices-python-sdk.git"
            "@bump-and-unfreeze-requirements`"
        )

    if not output_path:
        output_path = tempfile.mkdtemp()

    try:
        # Initial setup, create credentials instance.
        credentials = (
            Credentials.service_principal_credentials_builder()
            .with_client_id(config("PDF_SERVICES_CLIENT_ID", default=""))
            .with_client_secret(config("PDF_SERVICES_CLIENT_SECRET", default=""))
            .build()
        )

        # Create an ExecutionContext using credentials
        # and create a new operation instance.
        execution_context = ExecutionContext.create(credentials)
        extract_pdf_operation = ExtractPDFOperation.create_new()

        # Set operation input from a source file.
        source = FileRef.create_from_local_file(file_path)
        extract_pdf_operation.set_input(source)

        # Build ExtractPDF options and set them into the operation
        extract_pdf_options: ExtractPDFOptions = (
            ExtractPDFOptions.builder()
            .with_elements_to_extract(
                [ExtractElementType.TEXT, ExtractElementType.TABLES]
            )
            .with_elements_to_extract_renditions(
                [
                    ExtractRenditionsElementType.TABLES,
                    ExtractRenditionsElementType.FIGURES,
                ]
            )
            .build()
        )
        extract_pdf_operation.set_options(extract_pdf_options)

        # Execute the operation.
        result: FileRef = extract_pdf_operation.execute(execution_context)

        # Save the result to the specified location.
        zip_file_path = os.path.join(
            output_path, "ExtractTextTableWithFigureTableRendition.zip"
        )
        result.save_as(zip_file_path)
        # Open the ZIP file
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            # Extract all contents to the destination folder
            zip_ref.extractall(output_path)
    except (ServiceApiException, ServiceUsageException, SdkException):
        logging.exception("Exception encountered while executing operation")

    return output_path


def make_markdown_table(table_as_list: List[str]) -> str:
    """
    Convert table from python list representation to markdown format.
    The input list consists of rows of tables, the first row is the header.

    Args:
        table_as_list: list of table rows
            Example: [["Name", "Age", "Height"],
                    ["Jake", 20, 5'10],
                    ["Mary", 21, 5'7]]
    Returns:
        markdown representation of the table
    """
    markdown = "\n" + str("| ")

    for e in table_as_list[0]:
        to_add = " " + str(e) + str(" |")
        markdown += to_add
    markdown += "\n"

    markdown += "| "
    for i in range(len(table_as_list[0])):
        markdown += str("--- | ")
    markdown += "\n"

    for entry in table_as_list[1:]:
        markdown += str("| ")
        for e in entry:
            to_add = str(e) + str(" | ")
            markdown += to_add
        markdown += "\n"

    return markdown + "\n"


def load_json(input_path: Union[str | Path]) -> dict:
    """Load json file"""
    with open(input_path, "r") as fi:
        data = json.load(fi)

    return data


def load_excel(input_path: Union[str | Path]) -> str:
    """Load excel file and convert to markdown"""

    df = pd.read_excel(input_path).fillna("")
    # Convert dataframe to a list of rows
    row_list = [df.columns.values.tolist()] + df.values.tolist()

    for item_id, item in enumerate(row_list[0]):
        if "Unnamed" in item:
            row_list[0][item_id] = ""

    for row in row_list:
        for item_id, item in enumerate(row):
            row[item_id] = str(item).replace("_x000D_", " ").replace("\n", " ").strip()

    markdown_str = make_markdown_table(row_list)
    return markdown_str


def encode_image_base64(image_path: Union[str | Path]) -> Union[bytes, str]:
    """Convert image to base64"""

    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def parse_table_paths(file_paths: List[Path]) -> str:
    """Read the table stored in an excel file given the file path"""

    content = ""
    for path in file_paths:
        if path.suffix == ".xlsx":
            content = load_excel(path)
            break
    return content


def parse_figure_paths(file_paths: List[Path]) -> Union[bytes, str]:
    """Read and convert an image to base64 given the image path"""

    content = ""
    for path in file_paths:
        if path.suffix == ".png":
            base64_image = encode_image_base64(path)
            content = f"data:image/png;base64,{base64_image}"  # type: ignore
            break
    return content


def generate_single_figure_caption(vlm_endpoint: str, figure: str) -> str:
    """Summarize a single figure using GPT-4V"""
    if figure:
        output = generate_gpt4v(
            endpoint=vlm_endpoint,
            prompt="Provide a short 2 sentence summary of this image?",
            images=figure,
        )
        if "sorry" in output.lower():
            output = ""
    else:
        output = ""
    return output


def generate_figure_captions(
    vlm_endpoint: str, figures: List, max_figures_to_process: int
) -> List:
    """Summarize several figures using GPT-4V.
    Args:
        vlm_endpoint (str): endpoint to the vision language model service
        figures (List): list of base64 images
        max_figures_to_process (int): the maximum number of figures will be summarized,
        the rest are ignored.

    Returns:
        results (List[str]): list of all figure captions and empty strings for
        ignored figures.
    """
    to_gen_figures = figures[:max_figures_to_process]
    other_figures = figures[max_figures_to_process:]

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                lambda: generate_single_figure_caption(vlm_endpoint, figure)
            )
            for figure in to_gen_figures
        ]

    results = [future.result() for future in futures]
    return results + [""] * len(other_figures)
