import os

import gradio as gr
from authlib.integrations.starlette_client import OAuth, OAuthError
from decouple import config
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from ktem.assets import KotaemonTheme
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from theflow.settings import settings as flowsettings

KH_DEMO_MODE = getattr(flowsettings, "KH_DEMO_MODE", False)
KH_APP_DATA_DIR = getattr(flowsettings, "KH_APP_DATA_DIR", ".")
GRADIO_TEMP_DIR = os.getenv("GRADIO_TEMP_DIR", None)
# override GRADIO_TEMP_DIR if it's not set
if GRADIO_TEMP_DIR is None:
    GRADIO_TEMP_DIR = os.path.join(KH_APP_DATA_DIR, "gradio_tmp")
    os.environ["GRADIO_TEMP_DIR"] = GRADIO_TEMP_DIR


GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = config("GOOGLE_CLIENT_SECRET", default="")
SECRET_KEY = config("SECRET_KEY", default="default-secret-key")

save_api_key_js = """
function(api_key) {
    setStorage('google_api_key', api_key);
    window.location.href = "/app";
}
"""

global_js = """
function () {
  // store info in local storage
  globalThis.setStorage = (key, value) => {
      localStorage.setItem(key, value)
  }
  globalThis.getStorage = (key, value) => {
    item = localStorage.getItem(key);
    return item ? item : value;
  }
  globalThis.removeFromStorage = (key) => {
      localStorage.removeItem(key)
  }
}
"""


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


@app.get("/")
def public(request: Request):
    root_url = gr.route_utils.get_root_url(request, "/", None)
    return RedirectResponse(url=f"{root_url}/app")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(gradio_app._favicon)


@app.route("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")


@app.route("/login")
async def login(request: Request):
    root_url = gr.route_utils.get_root_url(request, "/login", None)
    redirect_uri = f"{root_url}/auth"
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
    js=global_js,
) as login_demo:
    with gr.Column(elem_id="login-row"):
        gr.Markdown("<h1 style='text-align:center;'>Welcome to Kotaemon</h1>")
        gr.Button(
            "Login with Google",
            link="/login",
            variant="primary",
            elem_id="google-login",
        )
        # with gr.Accordion(
        #     "Or use your own Gemini API key",
        #     elem_id="user-api-key-wrapper",
        #     open=False,
        # ):
        #     api_key_input = gr.Textbox(
        #         placeholder="API Key",
        #         label="Enter your Gemini API key",
        #     )
        #     api_key_save_btn = gr.Button(
        #         "Save",
        #     )

    # api_key_save_btn.click(
    #     fn=lambda _: True,
    #     inputs=[api_key_input],
    #     js=save_api_key_js,
    # )

app = gr.mount_gradio_app(app, login_demo, path="/login-app")
app = gr.mount_gradio_app(
    app,
    main_demo,
    path="/app",
    allowed_paths=[
        "libs/ktem/ktem/assets",
        GRADIO_TEMP_DIR,
    ],
)
