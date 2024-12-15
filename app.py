import os
from threading import Thread
from fastapi import FastAPI
from theflow.settings import settings as flowsettings
from ktem.main import App  # noqa
import uvicorn

# Gradio の設定
KH_APP_DATA_DIR = getattr(flowsettings, "KH_APP_DATA_DIR", ".")
GRADIO_TEMP_DIR = os.getenv("GRADIO_TEMP_DIR", None)

# GRADIO_TEMP_DIR が設定されていない場合にデフォルトパスを使用
if GRADIO_TEMP_DIR is None:
    GRADIO_TEMP_DIR = os.path.join(KH_APP_DATA_DIR, "gradio_tmp")
    os.environ["GRADIO_TEMP_DIR"] = GRADIO_TEMP_DIR

# FastAPI アプリケーション（ヘルスチェック用）
health_app = FastAPI()

@health_app.get("/health")
async def health():
    """ヘルスチェックエンドポイント"""
    return {"status": "ok"}

def run_health_check():
    """FastAPI サーバーを別スレッドで起動"""
    uvicorn.run(health_app, host="0.0.0.0", port=8000, log_level="info")

# FastAPI サーバーを別スレッドで起動
Thread(target=run_health_check, daemon=True).start()

# Gradio アプリケーションの起動
app = App()
demo = app.make()
demo.queue().launch(
    server_name="0.0.0.0",
    favicon_path=app._favicon,
    inbrowser=True,
    allowed_paths=[
        "libs/ktem/ktem/assets",
        GRADIO_TEMP_DIR,
    ],
)
