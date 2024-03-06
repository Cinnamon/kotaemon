import hashlib

import gradio as gr
from ktem.app import BasePage
from ktem.db.models import Settings, User, engine
from sqlmodel import Session, select

gr_cls_single_value = {
    "text": gr.Textbox,
    "number": gr.Number,
    "checkbox": gr.Checkbox,
}


gr_cls_choices = {
    "dropdown": gr.Dropdown,
    "radio": gr.Radio,
    "checkboxgroup": gr.CheckboxGroup,
}


def render_setting_item(setting_item, value):
    """Render the setting component into corresponding Gradio UI component"""
    kwargs = {
        "label": setting_item.name,
        "value": value,
        "interactive": True,
    }

    if setting_item.component in gr_cls_single_value:
        return gr_cls_single_value[setting_item.component](**kwargs)

    kwargs["choices"] = setting_item.choices

    if setting_item.component in gr_cls_choices:
        return gr_cls_choices[setting_item.component](**kwargs)

    raise ValueError(
        f"Unknown component {setting_item.component}, allowed are: "
        f"{list(gr_cls_single_value.keys()) + list(gr_cls_choices.keys())}.\n"
        f"Setting item: {setting_item}"
    )


class SettingsPage(BasePage):
    """Responsible for allowing the users to customize the application

    **IMPORTANT**: the name and id of the UI setting components should match the
    name of the setting in the `app.default_settings`
    """

    public_events = ["onSignIn", "onSignOut", "onCreateUser"]

    def __init__(self, app):
        """Initiate the page and render the UI"""
        self._app = app

        self._settings_state = app.settings_state
        self._user_id = app.user_id
        self._default_settings = app.default_settings
        self._settings_dict = self._default_settings.flatten()
        self._settings_keys = list(self._settings_dict.keys())

        self._components = {}
        self._reasoning_mode = {}

        self.on_building_ui()

    def on_building_ui(self):
        self.setting_save_btn = gr.Button("Save settings")
        if not self._app.dev_mode:
            with gr.Tab("User settings"):
                self.user_tab()
        with gr.Tab("General application settings"):
            self.app_tab()
        with gr.Tab("Index settings"):
            self.index_tab()
        with gr.Tab("Reasoning settings"):
            self.reasoning_tab()

    def on_subscribe_public_events(self):
        pass

    def on_register_events(self):
        self.setting_save_btn.click(
            self.save_setting,
            inputs=[self._user_id] + self.components(),
            outputs=self._settings_state,
        )
        self._components["reasoning.use"].change(
            self.change_reasoning_mode,
            inputs=[self._components["reasoning.use"]],
            outputs=list(self._reasoning_mode.values()),
            show_progress="hidden",
        )
        if not self._app.dev_mode:
            self.password_change_btn.click(
                self.change_password,
                inputs=[
                    self._user_id,
                    self.password_change,
                    self.password_change_confirm,
                ],
                outputs=None,
                show_progress="hidden",
            )

            onSignInClick = self.signin.click(
                self.sign_in,
                inputs=[self.username, self.password],
                outputs=[self._user_id, self.username, self.password]
                + self.signed_in_state()
                + [self.user_out_state],
                show_progress="hidden",
            ).then(
                self.load_setting,
                inputs=self._user_id,
                outputs=[self._settings_state] + self.components(),
                show_progress="hidden",
            )
            for event in self._app.get_event("onSignIn"):
                onSignInClick = onSignInClick.then(**event)

            onSignInSubmit = self.password.submit(
                self.sign_in,
                inputs=[self.username, self.password],
                outputs=[self._user_id, self.username, self.password]
                + self.signed_in_state()
                + [self.user_out_state],
                show_progress="hidden",
            ).then(
                self.load_setting,
                inputs=self._user_id,
                outputs=[self._settings_state] + self.components(),
                show_progress="hidden",
            )
            for event in self._app.get_event("onSignIn"):
                onSignInSubmit = onSignInSubmit.then(**event)

            onCreateUserClick = self.create_btn.click(
                self.create_user,
                inputs=[
                    self.username_new,
                    self.password_new,
                    self.password_new_confirm,
                ],
                outputs=[
                    self._user_id,
                    self.username_new,
                    self.password_new,
                    self.password_new_confirm,
                ]
                + self.signed_in_state()
                + [self.user_out_state],
                show_progress="hidden",
            ).then(
                self.load_setting,
                inputs=self._user_id,
                outputs=[self._settings_state] + self.components(),
                show_progress="hidden",
            )
            for event in self._app.get_event("onCreateUser"):
                onCreateUserClick = onCreateUserClick.then(**event)

            onSignOutClick = self.signout.click(
                self.sign_out,
                inputs=None,
                outputs=[self._user_id]
                + self.signed_in_state()
                + [self.user_out_state],
                show_progress="hidden",
            ).then(
                self.load_setting,
                inputs=self._user_id,
                outputs=[self._settings_state] + self.components(),
                show_progress="hidden",
            )
            for event in self._app.get_event("onSignOut"):
                onSignOutClick = onSignOutClick.then(**event)

    def user_tab(self):
        with gr.Row() as self.user_out_state:
            with gr.Column():
                gr.Markdown("Sign in")
                self.username = gr.Textbox(label="Username", interactive=True)
                self.password = gr.Textbox(
                    label="Password", type="password", interactive=True
                )
                self.signin = gr.Button("Login")

            with gr.Column():
                gr.Markdown("Create new account")
                self.username_new = gr.Textbox(label="Username", interactive=True)
                self.password_new = gr.Textbox(
                    label="Password", type="password", interactive=True
                )
                self.password_new_confirm = gr.Textbox(
                    label="Confirm password", type="password", interactive=True
                )
                self.create_btn = gr.Button("Create account")

        # user management
        self.current_name = gr.Markdown("Current user: ___", visible=False)
        self.signout = gr.Button("Logout", visible=False)

        self.password_change = gr.Textbox(
            label="New password", interactive=True, type="password", visible=False
        )
        self.password_change_confirm = gr.Textbox(
            label="Confirm password", interactive=True, type="password", visible=False
        )
        self.password_change_btn = gr.Button(
            "Change password", interactive=True, visible=False
        )

    def signed_out_state(self):
        return [
            self.username,
            self.password,
            self.signin,
            self.username_new,
            self.password_new,
            self.password_new_confirm,
            self.create_btn,
        ]

    def signed_in_state(self):
        return [
            self.current_name,  # always the first one
            self.signout,
            self.password_change,
            self.password_change_confirm,
            self.password_change_btn,
        ]

    def sign_in(self, username: str, password: str):
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user_id, clear_username, clear_password = None, username, password
        with Session(engine) as session:
            statement = select(User).where(
                User.username == username,
                User.password == hashed_password,
            )
            result = session.exec(statement).all()
            if result:
                user_id = result[0].id
                clear_username, clear_password = "", ""
            else:
                gr.Warning("Username or password is incorrect")

        output: list = [user_id, clear_username, clear_password]
        if user_id is None:
            output += [
                gr.update(visible=False) for _ in range(len(self.signed_in_state()))
            ]
            output.append(gr.update(visible=True))
        else:
            output.append(gr.update(visible=True, value=f"Current user: {username}"))
            output += [
                gr.update(visible=True) for _ in range(len(self.signed_in_state()) - 1)
            ]
            output.append(gr.update(visible=False))

        return output

    def create_user(self, username, password, password_confirm):
        user_id, usn, pwd, pwdc = None, username, password, password_confirm
        if password != password_confirm:
            gr.Warning("Password does not match")
        else:
            with Session(engine) as session:
                statement = select(User).where(
                    User.username == username,
                )
                result = session.exec(statement).all()
                if result:
                    gr.Warning(f'Username "{username}" already exists')
                else:
                    hashed_password = hashlib.sha256(password.encode()).hexdigest()
                    user = User(username=username, password=hashed_password)
                    session.add(user)
                    session.commit()
                    user_id = user.id
                    usn, pwd, pwdc = "", "", ""
                    print(user_id)

        output: list = [user_id, usn, pwd, pwdc]
        if user_id is not None:
            output.append(gr.update(visible=True, value=f"Current user: {username}"))
            output += [
                gr.update(visible=True) for _ in range(len(self.signed_in_state()) - 1)
            ]
            output.append(gr.update(visible=False))
        else:
            output += [
                gr.update(visible=False) for _ in range(len(self.signed_in_state()))
            ]
            output.append(gr.update(visible=True))

        return output

    def sign_out(self):
        output = [None]
        output += [gr.update(visible=False) for _ in range(len(self.signed_in_state()))]
        output.append(gr.update(visible=True))
        return output

    def change_password(self, user_id, password, password_confirm):
        if password != password_confirm:
            gr.Warning("Password does not match")
            return

        with Session(engine) as session:
            statement = select(User).where(User.id == user_id)
            result = session.exec(statement).all()
            if result:
                user = result[0]
                hashed_password = hashlib.sha256(password.encode()).hexdigest()
                user.password = hashed_password
                session.add(user)
                session.commit()
                gr.Info("Password changed")
            else:
                gr.Warning("User not found")

    def app_tab(self):
        for n, si in self._default_settings.application.settings.items():
            obj = render_setting_item(si, si.value)
            self._components[f"application.{n}"] = obj

    def index_tab(self):
        # TODO: double check if we need general
        # with gr.Tab("General"):
        #     for n, si in self._default_settings.index.settings.items():
        #         obj = render_setting_item(si, si.value)
        #         self._components[f"index.{n}"] = obj

        for pn, sig in self._default_settings.index.options.items():
            with gr.Tab(f"Index {pn}"):
                for n, si in sig.settings.items():
                    obj = render_setting_item(si, si.value)
                    self._components[f"index.options.{pn}.{n}"] = obj

    def reasoning_tab(self):
        with gr.Group():
            for n, si in self._default_settings.reasoning.settings.items():
                if n == "use":
                    continue
                obj = render_setting_item(si, si.value)
                self._components[f"reasoning.{n}"] = obj

        gr.Markdown("### Reasoning-specific settings")
        self._components["reasoning.use"] = render_setting_item(
            self._default_settings.reasoning.settings["use"],
            self._default_settings.reasoning.settings["use"].value,
        )

        for idx, (pn, sig) in enumerate(
            self._default_settings.reasoning.options.items()
        ):
            with gr.Group(
                visible=idx == 0,
                elem_id=pn,
            ) as self._reasoning_mode[pn]:
                gr.Markdown("**Name**: Description")
                for n, si in sig.settings.items():
                    obj = render_setting_item(si, si.value)
                    self._components[f"reasoning.options.{pn}.{n}"] = obj

    def change_reasoning_mode(self, value):
        output = []
        for each in self._reasoning_mode.values():
            if value == each.elem_id:
                output.append(gr.update(visible=True))
            else:
                output.append(gr.update(visible=False))
        return output

    def load_setting(self, user_id=None):
        settings = self._settings_dict
        with Session(engine) as session:
            statement = select(Settings).where(Settings.user == user_id)
            result = session.exec(statement).all()
            if result:
                settings = result[0].setting

        output = [settings]
        output += tuple(settings[name] for name in self.component_names())
        return output

    def save_setting(self, user_id: int, *args):
        """Save the setting to disk and persist the setting to session state

        Args:
            user_id: the user id
            args: all the values from the settings
        """
        setting = {key: value for key, value in zip(self.component_names(), args)}
        if user_id is None:
            gr.Warning("Need to login before saving settings")
            return setting

        with Session(engine) as session:
            statement = select(Settings).where(Settings.user == user_id)
            try:
                user_setting = session.exec(statement).one()
            except Exception:
                user_setting = Settings()
                user_setting.user = user_id
            user_setting.setting = setting
            session.add(user_setting)
            session.commit()

        gr.Info("Setting saved")
        return setting

    def components(self) -> list:
        """Get the setting components"""
        output = []
        for name in self._settings_keys:
            output.append(self._components[name])
        return output

    def component_names(self):
        """Get the setting components"""
        return self._settings_keys
