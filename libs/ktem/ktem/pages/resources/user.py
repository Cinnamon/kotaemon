import hashlib

import gradio as gr
import pandas as pd
from ktem.app import BasePage
from ktem.db.models import User, engine
from sqlmodel import Session, select
from theflow.settings import settings as flowsettings

USERNAME_RULE = """**Username rule:**

- Username is case-insensitive
- Username must be at least 3 characters long
- Username must be at most 32 characters long
- Username must contain only alphanumeric characters and underscores
"""


PASSWORD_RULE = """**Password rule:**

- Password must be at least 8 characters long
- Password must contain at least one uppercase letter
- Password must contain at least one lowercase letter
- Password must contain at least one digit
- Password must contain at least one special character from the following:
    ^ $ * . [ ] { } ( ) ? - " ! @ # % & / \\ , > < ' : ; | _ ~  + =
"""


def validate_username(usn):
    """Validate that whether username is valid

    Args:
        usn (str): Username
    """
    errors = []
    if len(usn) < 3:
        errors.append("Username must be at least 3 characters long")

    if len(usn) > 32:
        errors.append("Username must be at most 32 characters long")

    if not usn.replace("_", "").isalnum():
        errors.append(
            "Username must contain only alphanumeric characters and underscores"
        )

    return "; ".join(errors)


def validate_password(pwd, pwd_cnf):
    """Validate that whether password is valid

    - Password must be at least 8 characters long
    - Password must contain at least one uppercase letter
    - Password must contain at least one lowercase letter
    - Password must contain at least one digit
    - Password must contain at least one special character from the following:
        ^ $ * . [ ] { } ( ) ? - " ! @ # % & / \\ , > < ' : ; | _ ~  + =

    Args:
        pwd (str): Password
        pwd_cnf (str): Confirm password

    Returns:
        str: Error message if password is not valid
    """
    errors = []
    if pwd != pwd_cnf:
        errors.append("Password does not match")

    if len(pwd) < 8:
        errors.append("Password must be at least 8 characters long")

    if not any(c.isupper() for c in pwd):
        errors.append("Password must contain at least one uppercase letter")

    if not any(c.islower() for c in pwd):
        errors.append("Password must contain at least one lowercase letter")

    if not any(c.isdigit() for c in pwd):
        errors.append("Password must contain at least one digit")

    special_chars = "^$*.[]{}()?-\"!@#%&/\\,><':;|_~+="
    if not any(c in special_chars for c in pwd):
        errors.append(
            "Password must contain at least one special character from the "
            f"following: {special_chars}"
        )

    if errors:
        return "; ".join(errors)

    return ""


def create_user(usn, pwd) -> bool:
    with Session(engine) as session:
        statement = select(User).where(User.username_lower == usn.lower())
        result = session.exec(statement).all()
        if result:
            print(f'User "{usn}" already exists')
            return False

        else:
            hashed_password = hashlib.sha256(pwd.encode()).hexdigest()
            user = User(
                username=usn,
                username_lower=usn.lower(),
                password=hashed_password,
                admin=True,
            )
            session.add(user)
            session.commit()

            return True


class UserManagement(BasePage):
    def __init__(self, app):
        self._app = app

        self.on_building_ui()
        if hasattr(flowsettings, "KH_FEATURE_USER_MANAGEMENT_ADMIN") and hasattr(
            flowsettings, "KH_FEATURE_USER_MANAGEMENT_PASSWORD"
        ):
            usn = flowsettings.KH_FEATURE_USER_MANAGEMENT_ADMIN
            pwd = flowsettings.KH_FEATURE_USER_MANAGEMENT_PASSWORD

            is_created = create_user(usn, pwd)
            if is_created:
                gr.Info(f'User "{usn}" created successfully')

    def on_building_ui(self):
        with gr.Tab(label="User list"):
            self.state_user_list = gr.State(value=None)
            self.user_list = gr.DataFrame(
                headers=["id", "name", "admin"],
                interactive=False,
            )

            with gr.Group(visible=False) as self._selected_panel:
                self.selected_user_id = gr.Number(value=-1, visible=False)
                self.usn_edit = gr.Textbox(label="Username")
                with gr.Row():
                    self.pwd_edit = gr.Textbox(label="Change password", type="password")
                    self.pwd_cnf_edit = gr.Textbox(
                        label="Confirm change password",
                        type="password",
                    )
                self.admin_edit = gr.Checkbox(label="Admin")

            with gr.Row(visible=False) as self._selected_panel_btn:
                with gr.Column():
                    self.btn_edit_save = gr.Button("Save")
                with gr.Column():
                    self.btn_delete = gr.Button("Delete")
                    with gr.Row():
                        self.btn_delete_yes = gr.Button(
                            "Confirm delete", variant="primary", visible=False
                        )
                        self.btn_delete_no = gr.Button("Cancel", visible=False)
                with gr.Column():
                    self.btn_close = gr.Button("Close")

        with gr.Tab(label="Create user"):
            self.usn_new = gr.Textbox(label="Username", interactive=True)
            self.pwd_new = gr.Textbox(
                label="Password", type="password", interactive=True
            )
            self.pwd_cnf_new = gr.Textbox(
                label="Confirm password", type="password", interactive=True
            )
            with gr.Row():
                gr.Markdown(USERNAME_RULE)
                gr.Markdown(PASSWORD_RULE)
            self.btn_new = gr.Button("Create user")

    def on_register_events(self):
        self.btn_new.click(
            self.create_user,
            inputs=[self.usn_new, self.pwd_new, self.pwd_cnf_new],
            outputs=[self.usn_new, self.pwd_new, self.pwd_cnf_new],
        ).then(
            self.list_users,
            inputs=self._app.user_id,
            outputs=[self.state_user_list, self.user_list],
        )
        self.user_list.select(
            self.select_user,
            inputs=self.user_list,
            outputs=[self.selected_user_id],
            show_progress="hidden",
        )
        self.selected_user_id.change(
            self.on_selected_user_change,
            inputs=[self.selected_user_id],
            outputs=[
                self._selected_panel,
                self._selected_panel_btn,
                # delete section
                self.btn_delete,
                self.btn_delete_yes,
                self.btn_delete_no,
                # edit section
                self.usn_edit,
                self.pwd_edit,
                self.pwd_cnf_edit,
                self.admin_edit,
            ],
            show_progress="hidden",
        )
        self.btn_delete.click(
            self.on_btn_delete_click,
            inputs=[self.selected_user_id],
            outputs=[self.btn_delete, self.btn_delete_yes, self.btn_delete_no],
            show_progress="hidden",
        )
        self.btn_delete_yes.click(
            self.delete_user,
            inputs=[self._app.user_id, self.selected_user_id],
            outputs=[self.selected_user_id],
            show_progress="hidden",
        ).then(
            self.list_users,
            inputs=self._app.user_id,
            outputs=[self.state_user_list, self.user_list],
        )
        self.btn_delete_no.click(
            lambda: (
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
            ),
            inputs=[],
            outputs=[self.btn_delete, self.btn_delete_yes, self.btn_delete_no],
            show_progress="hidden",
        )
        self.btn_edit_save.click(
            self.save_user,
            inputs=[
                self.selected_user_id,
                self.usn_edit,
                self.pwd_edit,
                self.pwd_cnf_edit,
                self.admin_edit,
            ],
            outputs=[self.pwd_edit, self.pwd_cnf_edit],
            show_progress="hidden",
        ).then(
            self.list_users,
            inputs=self._app.user_id,
            outputs=[self.state_user_list, self.user_list],
        )
        self.btn_close.click(
            lambda: -1,
            outputs=[self.selected_user_id],
        )

    def on_subscribe_public_events(self):
        self._app.subscribe_event(
            name="onSignIn",
            definition={
                "fn": self.list_users,
                "inputs": [self._app.user_id],
                "outputs": [self.state_user_list, self.user_list],
            },
        )
        self._app.subscribe_event(
            name="onSignOut",
            definition={
                "fn": lambda: ("", "", "", None, None, -1),
                "outputs": [
                    self.usn_new,
                    self.pwd_new,
                    self.pwd_cnf_new,
                    self.state_user_list,
                    self.user_list,
                    self.selected_user_id,
                ],
            },
        )

    def create_user(self, usn, pwd, pwd_cnf):
        errors = validate_username(usn)
        if errors:
            gr.Warning(errors)
            return usn, pwd, pwd_cnf

        errors = validate_password(pwd, pwd_cnf)
        print(errors)
        if errors:
            gr.Warning(errors)
            return usn, pwd, pwd_cnf

        with Session(engine) as session:
            statement = select(User).where(User.username_lower == usn.lower())
            result = session.exec(statement).all()
            if result:
                gr.Warning(f'Username "{usn}" already exists')
                return

            hashed_password = hashlib.sha256(pwd.encode()).hexdigest()
            user = User(
                username=usn, username_lower=usn.lower(), password=hashed_password
            )
            session.add(user)
            session.commit()
            gr.Info(f'User "{usn}" created successfully')

        return "", "", ""

    def list_users(self, user_id):
        if user_id is None:
            return [], pd.DataFrame.from_records(
                [{"id": "-", "username": "-", "admin": "-"}]
            )

        with Session(engine) as session:
            statement = select(User).where(User.id == user_id)
            user = session.exec(statement).one()
            if not user.admin:
                return [], pd.DataFrame.from_records(
                    [{"id": "-", "username": "-", "admin": "-"}]
                )

            statement = select(User)
            results = [
                {"id": user.id, "username": user.username, "admin": user.admin}
                for user in session.exec(statement).all()
            ]
            if results:
                user_list = pd.DataFrame.from_records(results)
            else:
                user_list = pd.DataFrame.from_records(
                    [{"id": "-", "username": "-", "admin": "-"}]
                )

        return results, user_list

    def select_user(self, user_list, ev: gr.SelectData):
        if ev.value == "-" and ev.index[0] == 0:
            gr.Info("No user is loaded. Please refresh the user list")
            return -1

        if not ev.selected:
            return -1

        return int(user_list["id"][ev.index[0]])

    def on_selected_user_change(self, selected_user_id):
        if selected_user_id == -1:
            _selected_panel = gr.update(visible=False)
            _selected_panel_btn = gr.update(visible=False)
            btn_delete = gr.update(visible=True)
            btn_delete_yes = gr.update(visible=False)
            btn_delete_no = gr.update(visible=False)
            usn_edit = gr.update(value="")
            pwd_edit = gr.update(value="")
            pwd_cnf_edit = gr.update(value="")
            admin_edit = gr.update(value=False)
        else:
            _selected_panel = gr.update(visible=True)
            _selected_panel_btn = gr.update(visible=True)
            btn_delete = gr.update(visible=True)
            btn_delete_yes = gr.update(visible=False)
            btn_delete_no = gr.update(visible=False)

            with Session(engine) as session:
                statement = select(User).where(User.id == int(selected_user_id))
                user = session.exec(statement).one()

            usn_edit = gr.update(value=user.username)
            pwd_edit = gr.update(value="")
            pwd_cnf_edit = gr.update(value="")
            admin_edit = gr.update(value=user.admin)

        return (
            _selected_panel,
            _selected_panel_btn,
            btn_delete,
            btn_delete_yes,
            btn_delete_no,
            usn_edit,
            pwd_edit,
            pwd_cnf_edit,
            admin_edit,
        )

    def on_btn_delete_click(self, selected_user_id):
        if selected_user_id is None:
            gr.Warning("No user is selected")
            btn_delete = gr.update(visible=True)
            btn_delete_yes = gr.update(visible=False)
            btn_delete_no = gr.update(visible=False)
            return

        btn_delete = gr.update(visible=False)
        btn_delete_yes = gr.update(visible=True)
        btn_delete_no = gr.update(visible=True)

        return btn_delete, btn_delete_yes, btn_delete_no

    def save_user(self, selected_user_id, usn, pwd, pwd_cnf, admin):
        errors = validate_username(usn)
        if errors:
            gr.Warning(errors)
            return pwd, pwd_cnf

        if pwd:
            errors = validate_password(pwd, pwd_cnf)
            if errors:
                gr.Warning(errors)
                return pwd, pwd_cnf

        with Session(engine) as session:
            statement = select(User).where(User.id == int(selected_user_id))
            user = session.exec(statement).one()
            user.username = usn
            user.username_lower = usn.lower()
            user.admin = admin
            if pwd:
                user.password = hashlib.sha256(pwd.encode()).hexdigest()
            session.commit()
            gr.Info(f'User "{usn}" updated successfully')

        return "", ""

    def delete_user(self, current_user, selected_user_id):
        if current_user == selected_user_id:
            gr.Warning("You cannot delete yourself")
            return selected_user_id

        with Session(engine) as session:
            statement = select(User).where(User.id == int(selected_user_id))
            user = session.exec(statement).one()
            session.delete(user)
            session.commit()
            gr.Info(f'User "{user.username}" deleted successfully')
        return -1
