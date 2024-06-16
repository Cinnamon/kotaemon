"""Pandas Excel reader.

Pandas parser for .xlsx files.

"""
from pathlib import Path
from typing import Any, List, Optional, Union

from llama_index.core.readers.base import BaseReader

from kotaemon.base import Document


class PandasExcelReader(BaseReader):
    r"""Pandas-based CSV parser.

    Parses CSVs using the separator detection from Pandas `read_csv` function.
    If special parameters are required, use the `pandas_config` dict.

    Args:

        pandas_config (dict): Options for the `pandas.read_excel` function call.
            Refer to https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html
            for more information. Set to empty dict by default,
            this means defaults will be used.

    """

    def __init__(
        self,
        *args: Any,
        pandas_config: Optional[dict] = None,
        row_joiner: str = "\n",
        col_joiner: str = " ",
        **kwargs: Any,
    ) -> None:
        """Init params."""
        super().__init__(*args, **kwargs)
        self._pandas_config = pandas_config or {}
        self._row_joiner = row_joiner if row_joiner else "\n"
        self._col_joiner = col_joiner if col_joiner else " "

    def load_data(
        self,
        file: Path,
        include_sheetname: bool = False,
        sheet_name: Optional[Union[str, int, list]] = None,
        extra_info: Optional[dict] = None,
        **kwargs,
    ) -> List[Document]:
        """Parse file and extract values from a specific column.

        Args:
            file (Path): The path to the Excel file to read.
            include_sheetname (bool): Whether to include the sheet name in the output.
            sheet_name (Union[str, int, None]): The specific sheet to read from,
                default is None which reads all sheets.

        Returns:
            List[Document]: A list of`Document objects containing the
                values from the specified column in the Excel file.
        """
        import itertools

        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "install pandas using `pip3 install pandas` to use this loader"
            )

        if sheet_name is not None:
            sheet_name = (
                [sheet_name] if not isinstance(sheet_name, list) else sheet_name
            )

        dfs = pd.read_excel(file, sheet_name=sheet_name, **self._pandas_config)
        sheet_names = dfs.keys()
        df_sheets = []

        for key in sheet_names:
            sheet = []
            if include_sheetname:
                sheet.append([key])
            dfs[key] = dfs[key].dropna(axis=0, how="all")
            dfs[key] = dfs[key].dropna(axis=0, how="all")
            dfs[key].fillna("", inplace=True)
            sheet.extend(dfs[key].values.astype(str).tolist())
            df_sheets.append(sheet)

        text_list = list(
            itertools.chain.from_iterable(df_sheets)
        )  # flatten list of lists

        output = [
            Document(
                text=self._row_joiner.join(
                    self._col_joiner.join(sublist) for sublist in text_list
                ),
                metadata=extra_info or {},
            )
        ]

        return output


class ExcelReader(BaseReader):
    r"""Spreadsheet exporter respecting multiple worksheets

    Parses CSVs using the separator detection from Pandas `read_csv` function.
    If special parameters are required, use the `pandas_config` dict.

    Args:

        pandas_config (dict): Options for the `pandas.read_excel` function call.
            Refer to https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html
            for more information. Set to empty dict by default,
            this means defaults will be used.

    """

    def __init__(
        self,
        *args: Any,
        pandas_config: Optional[dict] = None,
        row_joiner: str = "\n",
        col_joiner: str = " ",
        **kwargs: Any,
    ) -> None:
        """Init params."""
        super().__init__(*args, **kwargs)
        self._pandas_config = pandas_config or {}
        self._row_joiner = row_joiner if row_joiner else "\n"
        self._col_joiner = col_joiner if col_joiner else " "

    def load_data(
        self,
        file: Path,
        include_sheetname: bool = True,
        sheet_name: Optional[Union[str, int, list]] = None,
        extra_info: Optional[dict] = None,
        **kwargs,
    ) -> List[Document]:
        """Parse file and extract values from a specific column.

        Args:
            file (Path): The path to the Excel file to read.
            include_sheetname (bool): Whether to include the sheet name in the output.
            sheet_name (Union[str, int, None]): The specific sheet to read from,
                default is None which reads all sheets.

        Returns:
            List[Document]: A list of`Document objects containing the
                values from the specified column in the Excel file.
        """

        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "install pandas using `pip3 install pandas` to use this loader"
            )

        if sheet_name is not None:
            sheet_name = (
                [sheet_name] if not isinstance(sheet_name, list) else sheet_name
            )

        # clean up input
        file = Path(file)
        extra_info = extra_info or {}

        dfs = pd.read_excel(file, sheet_name=sheet_name, **self._pandas_config)
        sheet_names = dfs.keys()
        output = []

        for idx, key in enumerate(sheet_names):
            dfs[key] = dfs[key].dropna(axis=0, how="all")
            dfs[key] = dfs[key].dropna(axis=0, how="all")
            dfs[key] = dfs[key].astype("object")
            dfs[key].fillna("", inplace=True)

            rows = dfs[key].values.astype(str).tolist()
            content = self._row_joiner.join(
                self._col_joiner.join(row).strip() for row in rows
            ).strip()
            if include_sheetname:
                content = f"(Sheet {key} of file {file.name})\n{content}"
            metadata = {"page_label": idx + 1, "sheet_name": key, **extra_info}
            output.append(Document(text=content, metadata=metadata))

        return output
