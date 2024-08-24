import os

from ktem.main import App

GRADIO_TEMP_DIR = os.getenv("GRADIO_TEMP_DIR", "./gradio_tmp")

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
