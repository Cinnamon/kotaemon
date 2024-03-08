import hashlib

import gradio as gr
from ktem.app import BasePage
from ktem.db.models import User, engine
from sqlmodel import Session, select

fetch_creds = """
function() {
    const username = getStorage('username')
    const password = getStorage('password')
    return [username, password];
}
"""

signin_js = """
function(usn, pwd) {
    setStorage('username', usn);
    setStorage('password', pwd);
    return [usn, pwd];
}
"""


class LoginPage(BasePage):

    public_events = ["onSignIn"]

    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        gr.Markdown("Welcome to Kotaemon")
        self.usn = gr.Textbox(label="Username")
        self.pwd = gr.Textbox(label="Password", type="password")
        self.btn_login = gr.Button("Login")
        self._dummy = gr.State()

    def on_register_events(self):
        onSignIn = gr.on(
            triggers=[self.btn_login.click, self.pwd.submit],
            fn=self.login,
            inputs=[self.usn, self.pwd],
            outputs=[self._app.user_id, self.usn, self.pwd],
            show_progress="hidden",
            js=signin_js,
        )
        for event in self._app.get_event("onSignIn"):
            onSignIn = onSignIn.success(**event)

    def _on_app_created(self):
        self._app.app.load(
            None,
            inputs=None,
            outputs=[self.usn, self.pwd],
            js=fetch_creds,
        )

    def login(self, usn, pwd):

        hashed_password = hashlib.sha256(pwd.encode()).hexdigest()
        with Session(engine) as session:
            stmt = select(User).where(
                User.username_lower == usn.lower(), User.password == hashed_password
            )
            result = session.exec(stmt).all()
            if result:
                return result[0].id, "", ""

            gr.Warning("Invalid username or password")
            return None, usn, pwd
