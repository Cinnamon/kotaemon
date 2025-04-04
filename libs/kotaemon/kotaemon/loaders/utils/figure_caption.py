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

from kotaemon.loaders.utils.llava import generate_llava

def generate_single_figure_caption(vlm_endpoint: str, figure: str) -> str:
    output = ""

    """Summarize a single figure using llava"""
    if figure:
        try:
            output = generate_llava(
                endpoint=vlm_endpoint,
                prompt="Provide a short 2 sentence summary of this image.",
                images=figure,
            )
            if "sorry" in output.lower():
                output = ""
        except Exception as e:
            print(f"Error generating caption: {e}")

    return output