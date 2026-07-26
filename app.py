import os
from pathlib import Path

from theflow.settings import settings as flowsettings

_APP_DIR = Path(__file__).parent

KH_APP_DATA_DIR = getattr(flowsettings, "KH_APP_DATA_DIR", ".")
KH_GRADIO_SHARE = getattr(flowsettings, "KH_GRADIO_SHARE", False)
GRADIO_TEMP_DIR = os.getenv("GRADIO_TEMP_DIR")
# override GRADIO_TEMP_DIR if it's not set or is empty
if not GRADIO_TEMP_DIR:
    GRADIO_TEMP_DIR = os.path.join(KH_APP_DATA_DIR, "gradio_tmp")
    os.environ["GRADIO_TEMP_DIR"] = GRADIO_TEMP_DIR


from ktem.main import App  # noqa

app = App()
demo = app.make()
demo.queue().launch(
    favicon_path=app._favicon,
    inbrowser=os.getenv("KH_OPEN_BROWSER", "0") == "1",
    allowed_paths=[
        str(_APP_DIR / "libs/ktem/ktem/assets"),
        GRADIO_TEMP_DIR,
    ],
    share=KH_GRADIO_SHARE,
)
