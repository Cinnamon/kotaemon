import os

from sqlmodel import Session, select

from ...db.models import engine
from .page_preview_runtime import ensure_pdf_preview_copy


class PreviewFileResolver:
    def __init__(self, app, file_name_cache: dict[str, str]):
        self._app = app
        self._file_name_cache = file_name_cache

    @staticmethod
    def extract_first_selected_file_id(selected_file_ids):
        if not selected_file_ids:
            return ""

        selected = selected_file_ids[0]
        if isinstance(selected, str) and selected.startswith("["):
            try:
                import json

                selected_items = json.loads(selected)
                return selected_items[0] if selected_items else ""
            except Exception:
                return ""

        return selected

    def resolve_file_path_by_id(self, file_id: str) -> str:
        if not file_id:
            return ""
        for index in self._app.index_manager.indices:
            resources = getattr(index, "_resources", {}) or {}
            source_table = resources.get("Source")
            file_storage_path = resources.get("FileStoragePath")
            if source_table is None:
                continue

            with Session(engine) as session:
                statement = select(source_table).where(source_table.id == file_id)
                source_obj = session.exec(statement).first()
            if not source_obj:
                continue

            self._file_name_cache[file_id] = getattr(source_obj, "name", "") or ""
            stored_path = getattr(source_obj, "path", "") or ""
            if not stored_path:
                continue

            if file_storage_path:
                candidate_storage_path = os.path.join(str(file_storage_path), stored_path)
                if os.path.isfile(candidate_storage_path):
                    return candidate_storage_path
            if os.path.isfile(stored_path):
                return stored_path
        return ""

    def resolve_file_name_by_id(self, file_id: str) -> str:
        if not file_id:
            return ""
        if file_id in self._file_name_cache:
            return self._file_name_cache[file_id]
        _ = self.resolve_file_path_by_id(file_id)
        return self._file_name_cache.get(file_id, "")

    def resolve_selected_file(self, first_selector_choices, selected_file_ids):
        del first_selector_choices

        file_id = self.extract_first_selected_file_id(selected_file_ids)
        if not file_id:
            return "", "", ""

        file_name = ""
        resolved_path = ""
        for index in self._app.index_manager.indices:
            resources = getattr(index, "_resources", {}) or {}
            source_table = resources.get("Source")
            file_storage_path = resources.get("FileStoragePath")
            if source_table is None:
                continue

            with Session(engine) as session:
                statement = select(source_table).where(source_table.id == file_id)
                source_obj = session.exec(statement).first()

            if not source_obj:
                continue

            file_name = getattr(source_obj, "name", "") or ""
            stored_path = getattr(source_obj, "path", "") or ""

            if stored_path and file_storage_path:
                candidate_storage_path = os.path.join(str(file_storage_path), stored_path)
                if os.path.isfile(candidate_storage_path):
                    resolved_path = candidate_storage_path
                    break

            if stored_path and os.path.isfile(stored_path):
                resolved_path = stored_path
                break

        if not file_name:
            file_name = self.resolve_file_name_by_id(file_id)
        if not resolved_path:
            resolved_path = self.resolve_file_path_by_id(file_id)

        resolved_path = ensure_pdf_preview_copy(resolved_path, file_name)
        return file_id, file_name, resolved_path