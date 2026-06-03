import os

import gradiologin as grlogin
from decouple import config
from fastapi import FastAPI
from fastapi.responses import FileResponse
from theflow.settings import settings as flowsettings

KH_APP_DATA_DIR = getattr(flowsettings, "KH_APP_DATA_DIR", ".")
GRADIO_TEMP_DIR = os.getenv("GRADIO_TEMP_DIR", None)
AUTHENTICATION_METHOD = config("AUTHENTICATION_METHOD", "GOOGLE")

# override GRADIO_TEMP_DIR if it's not set
if GRADIO_TEMP_DIR is None:
    GRADIO_TEMP_DIR = os.path.join(KH_APP_DATA_DIR, "gradio_tmp")
    os.environ["GRADIO_TEMP_DIR"] = GRADIO_TEMP_DIR

# for authentication with Google
GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = config("GOOGLE_CLIENT_SECRET", default="")

# for authentication with Open ID by keycloak
KEYCLOAK_SERVER_URL = config("KEYCLOAK_SERVER_URL", default="")
KEYCLOAK_REALM = config("KEYCLOAK_REALM", default="")
KEYCLOAK_CLIENT_ID = config("KEYCLOAK_CLIENT_ID", default="")
KEYCLOAK_CLIENT_SECRET = config("KEYCLOAK_CLIENT_SECRET", default="")

from ktem.main import App  # noqa

gradio_app = App()
demo = gradio_app.make()

app = FastAPI()

if AUTHENTICATION_METHOD == "KEYCLOAK":
    # for authentication with Open ID by keycloak
    grlogin.register(
        name="keycloak",
        server_metadata_url=(
            f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/"
            ".well-known/openid-configuration"
        ),
        client_id=KEYCLOAK_CLIENT_ID,
        client_secret=KEYCLOAK_CLIENT_SECRET,
        client_kwargs={
            "scope": "openid email profile",
        },
    )

else:
    # for authentication with Google
    grlogin.register(
        name="google",
        server_metadata_url=(
            "https://accounts.google.com/.well-known/openid-configuration"
        ),
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        client_kwargs={
            "scope": "openid email profile",
        },
    )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(gradio_app._favicon)


grlogin.mount_gradio_app(
    app,
    demo,
    "/app",
    allowed_paths=[
        "libs/ktem/ktem/assets",
        GRADIO_TEMP_DIR,
    ],
)
