import gradio as gr
import os
from ktem.app import BasePage
from ktem.db.engine import engine
from sqlalchemy.orm import Session
from kotaemon.base import RetrievedDocument
from ktem.utils.render import Render

ASSETS_DIR = "assets/icons"
if not os.path.isdir(ASSETS_DIR):
    ASSETS_DIR = "libs/ktem/ktem/assets/icons"

BASE_PATH = os.environ.get("GR_FILE_ROOT_PATH", "")

class FileList(BasePage):
    def __init__(self, app, index):
        self._app = app
        self.on_building_ui()
        self._index = index

    def on_building_ui(self):
        self.container = gr.HTML(visible=True)

    def update(self, file_ids):
        index = self._index

        if not file_ids:
            return gr.update(value="<div>No files found.</div>")

        Source = index._resources["Source"]
        with Session(engine) as session:
            files = session.query(Source).filter(Source.id.in_(file_ids)).all()

            file_dicts = []

            for file in files:
                file_dicts.append({
                    "id": file.id,
                    "name": file.name,
                    "path": file.path if file.path else "",
                    "date_created": file.date_created.strftime("%d/%m/%Y") if file.date_created else "",
                    "date_from_file_name": file.date_from_file_name.strftime("%d/%m/%Y") if file.date_from_file_name else "",
                    "date_from_content": file.date_from_content.strftime("%d/%m/%Y") if file.date_from_content else "",
                })

            if not file_dicts:
                return gr.update(value="<div>No files found.</div>")
            cards = []

            eye_icon_path = f"{ASSETS_DIR}/docu-eye.svg"
            with open(eye_icon_path, "r", encoding="utf-8") as f:
                eye_svg = f.read()

            calendar_icon_path = f"{ASSETS_DIR}/calendar.svg"
            with open(calendar_icon_path, "r", encoding="utf-8") as f:
                calendar_svg = f.read()

            for file in file_dicts:
                display_date = (
                    file["date_from_file_name"]
                    or file["date_from_content"]
                    or file["date_created"]
                )

                cards.append(f"""
                    <div style="background:#fff; border-radius:8px; padding:10px; margin-bottom:10px; display:flex; flex-direction:column; gap:8px; max-width:320px;">
                        <div style="font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                            {file["name"]}
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div style="display:flex; align-items:center; gap:6px; color:#5C667B;">
                                <span style="display:inline-flex; align-items:center; height:18px; width:18px; background:#fff; border-radius:4px">{calendar_svg}</span>
                                <span style="font-size:0.95em;">{display_date}</span>
                            </div>
                            <div>
                                <a 
                                    href="#" 
                                    class="pdf-file" 
                                    data-expand-pdf="true" 
                                    data-src="{BASE_PATH}/file={file["path"]}"
                                    style="
                                        align-self:flex-end;
                                        background:#E8F0FE;
                                        border-radius:12px;
                                        padding:2px 14px 2px 10px;
                                        cursor:pointer;
                                        display:flex;
                                        align-items:center;
                                        gap:6px;
                                        font-size:1.1em;
                                        font-weight:500;
                                        color:#222;
                                        box-shadow: 0px 2px 5px 0px rgba(0,0,0,0.05);
                                        transition:box-shadow 0.1s;
                                        text-decoration:none;
                                ">
                                    <span style="display:inline-flex; align-items:center; height:20px; width:20px;">{eye_svg}</span>
                                    <span>show</span>
                                </a>
                            </div>
                        </div>
                    </div>
                    """)
            return gr.update(value="".join(cards))