import os

import gradio as gr
from authlib.integrations.starlette_client import OAuth, OAuthError
from decouple import config
from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse
from ktem.assets import KotaemonTheme
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from theflow.settings import settings as flowsettings

KH_APP_DATA_DIR = getattr(flowsettings, "KH_APP_DATA_DIR", ".")
GRADIO_TEMP_DIR = os.getenv("GRADIO_TEMP_DIR", None)
# override GRADIO_TEMP_DIR if it's not set
if GRADIO_TEMP_DIR is None:
    GRADIO_TEMP_DIR = os.path.join(KH_APP_DATA_DIR, "gradio_tmp")
    os.environ["GRADIO_TEMP_DIR"] = GRADIO_TEMP_DIR


GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = config("GOOGLE_CLIENT_SECRET", default="")
SECRET_KEY = config("SECRET_KEY", default="default-secret-key")


def add_session_middleware(app):
    config_data = {
        "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
        "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
    }
    starlette_config = Config(environ=config_data)
    oauth = OAuth(starlette_config)
    oauth.register(
        name="google",
        server_metadata_url=(
            "https://accounts.google.com/" ".well-known/openid-configuration"
        ),
        client_kwargs={"scope": "openid email profile"},
    )

    app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
    return oauth


from ktem.main import App  # noqa

gradio_app = App()
main_demo = gradio_app.make()

app = FastAPI()
oauth = add_session_middleware(app)


# Dependency to get the current user
def get_user(request: Request):
    user = request.session.get("user")
    if user:
        return user["name"]
    return None


@app.get("/")
def public(user: dict = Depends(get_user)):
    if user:
        return RedirectResponse(url="/app")
    else:
        return RedirectResponse(url="/login-app")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(gradio_app._favicon)


@app.route("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")


@app.route("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth")
    # If your app is running on https, you should ensure that the
    # `redirect_uri` is https, e.g. uncomment the following lines:
    #
    # from urllib.parse import urlparse, urlunparse
    # redirect_uri = urlunparse(urlparse(str(redirect_uri))._replace(scheme='https'))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.route("/auth")
async def auth(request: Request):
    try:
        access_token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        return RedirectResponse(url="/")
    request.session["user"] = dict(access_token)["userinfo"]
    return RedirectResponse(url="/")


with gr.Blocks(
    theme=KotaemonTheme(),
    css=gradio_app._css,
) as login_demo:
    with gr.Row(elem_id="login-row"):
        gr.Markdown("<h1 style='text-align:center;'>Welcome to Kotaemon</h1>")
        gr.Button(
            "Login with Google",
            link="/login",
            variant="primary",
            elem_id="google-login",
        )

app = gr.mount_gradio_app(app, login_demo, path="/login-app")
app = gr.mount_gradio_app(
    app,
    main_demo,
    path="/app",
    auth_dependency=get_user,
    allowed_paths=[
        "libs/ktem/ktem/assets",
        GRADIO_TEMP_DIR,
    ],
)
