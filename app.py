import os

from ktem.main import App
from theflow.settings import settings as flowsettings

KH_APP_DATA_DIR = getattr(flowsettings, "KH_MARKDOWN_OUTPUT_DIR", ".")
GRADIO_TEMP_DIR = os.getenv(
    "GRADIO_TEMP_DIR", os.path.join(KH_APP_DATA_DIR, "gradio_tmp")
)

app = App()
demo = app.make()
demo.queue().launch(
    favicon_path=app._favicon,
    inbrowser=True,
    allowed_paths=[
        "libs/ktem/ktem/assets",
        GRADIO_TEMP_DIR,
    ],
)
