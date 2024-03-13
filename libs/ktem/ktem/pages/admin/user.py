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

    if not usn.strip("_").isalnum():
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


class UserManagement(BasePage):
    def __init__(self, app):
        self._app = app
        self.selected_panel_false = "Selected user: (please select above)"
        self.selected_panel_true = "Selected user: {name}"

        self.on_building_ui()
        if hasattr(flowsettings, "KH_FEATURE_USER_MANAGEMENT_ADMIN") and hasattr(
            flowsettings, "KH_FEATURE_USER_MANAGEMENT_PASSWORD"
        ):
            usn = flowsettings.KH_FEATURE_USER_MANAGEMENT_ADMIN
            pwd = flowsettings.KH_FEATURE_USER_MANAGEMENT_PASSWORD

            with Session(engine) as session:
                statement = select(User).where(User.username_lower == usn.lower())
                result = session.exec(statement).all()
                if result:
                    print(f'User "{usn}" already exists')

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
                    gr.Info(f'User "{usn}" created successfully')

    def on_building_ui(self):
        with gr.Accordion(label="Create user", open=False):
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

        gr.Markdown("## User list")
        self.btn_list_user = gr.Button("Refresh user list")
        self.state_user_list = gr.State(value=None)
        self.user_list = gr.DataFrame(
            headers=["id", "name", "admin"],
            interactive=False,
        )

        with gr.Row():
            self.selected_user_id = gr.State(value=None)
            self.selected_panel = gr.Markdown(self.selected_panel_false)
            self.deselect_button = gr.Button("Deselect", visible=False)

        with gr.Group():
            self.btn_delete = gr.Button("Delete user")
            with gr.Row():
                self.btn_delete_yes = gr.Button("Confirm", visible=False)
                self.btn_delete_no = gr.Button("Cancel", visible=False)

        gr.Markdown("## User details")
        self.usn_edit = gr.Textbox(label="Username")
        self.pwd_edit = gr.Textbox(label="Password", type="password")
        self.pwd_cnf_edit = gr.Textbox(label="Confirm password", type="password")
        self.admin_edit = gr.Checkbox(label="Admin")
        self.btn_edit_save = gr.Button("Save")

    def on_register_events(self):
        self.btn_new.click(
            self.create_user,
            inputs=[self.usn_new, self.pwd_new, self.pwd_cnf_new],
            outputs=None,
        )
        self.btn_list_user.click(
            self.list_users, inputs=None, outputs=[self.state_user_list, self.user_list]
        )
        self.user_list.select(
            self.select_user,
            inputs=self.user_list,
            outputs=[self.selected_user_id, self.selected_panel],
            show_progress="hidden",
        )
        self.selected_panel.change(
            self.on_selected_user_change,
            inputs=[self.selected_user_id],
            outputs=[
                self.deselect_button,
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
        self.deselect_button.click(
            lambda: (None, self.selected_panel_false),
            inputs=None,
            outputs=[self.selected_user_id, self.selected_panel],
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
            inputs=[self.selected_user_id],
            outputs=[self.selected_user_id, self.selected_panel],
            show_progress="hidden",
        )
        self.btn_delete_no.click(
            lambda: (
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
            ),
            inputs=None,
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
            outputs=None,
            show_progress="hidden",
        )

    def create_user(self, usn, pwd, pwd_cnf):
        errors = validate_username(usn)
        if errors:
            gr.Warning(errors)
            return

        errors = validate_password(pwd, pwd_cnf)
        print(errors)
        if errors:
            gr.Warning(errors)
            return

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

    def list_users(self):
        with Session(engine) as session:
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
            return None, self.selected_panel_false

        if not ev.selected:
            return None, self.selected_panel_false

        return user_list["id"][ev.index[0]], self.selected_panel_true.format(
            name=user_list["username"][ev.index[0]]
        )

    def on_selected_user_change(self, selected_user_id):
        if selected_user_id is None:
            deselect_button = gr.update(visible=False)
            btn_delete = gr.update(visible=True)
            btn_delete_yes = gr.update(visible=False)
            btn_delete_no = gr.update(visible=False)
            usn_edit = gr.update(value="")
            pwd_edit = gr.update(value="")
            pwd_cnf_edit = gr.update(value="")
            admin_edit = gr.update(value=False)
        else:
            deselect_button = gr.update(visible=True)
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
            deselect_button,
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
            return

        if pwd:
            errors = validate_password(pwd, pwd_cnf)
            if errors:
                gr.Warning(errors)
                return

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

    def delete_user(self, selected_user_id):
        with Session(engine) as session:
            statement = select(User).where(User.id == int(selected_user_id))
            user = session.exec(statement).one()
            session.delete(user)
            session.commit()
            gr.Info(f'User "{user.username}" deleted successfully')
        return None, self.selected_panel_false
