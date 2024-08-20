# mypy: ignore-errors
from collections import defaultdict
from datetime import datetime
from functools import cached_property
from typing import Any

from ktem.db.base_models import TagProcessStatus, TagScope, TagType
from ktem.db.models import ChunkTagIndex, Tag
from sqlmodel import Session, select, update


class TagCRUD:
    def __init__(self, engine):
        self._engine = engine

    def list_all(self) -> list[Tag]:
        with Session(self._engine) as session:
            statement = select(Tag)
            results = session.exec(statement).all()

            return results

    def create(
        self,
        name: str,
        prompt: str,
        config: str,
        type: str | TagType = TagType.text,
        scope: str | TagType = TagScope.chunk,
        valid_classes: str | None = None,
    ) -> str | None:
        meta = {}

        assert name != "" and prompt != "", "Invalid name or prompt: cannot be empty."

        if type == TagType.classification:
            assert (
                valid_classes is not None and valid_classes != ""
            ), "Invalid valid classes!"
            meta["valid_classes"] = valid_classes

        with Session(self._engine) as session:
            # tag name must be unique
            existed_result = self.query_by_name(name)
            if existed_result:
                raise Exception(f"Tag name: {name} has already been existed!")

            tag: Tag = Tag(
                name=name,
                prompt=prompt,
                config=config,
                type=type.value if isinstance(type, TagType) else type,
                scope=scope.value if isinstance(type, TagScope) else scope,
                meta=meta,
            )
            session.add(tag)
            session.commit()

            return tag.id

    def query_by_id(self, tag_id: str) -> Tag | None:
        with Session(self._engine) as session:
            statement = select(Tag).where(Tag.id == tag_id)

            result = session.exec(statement).first()
            return result

    def query_by_ids(self, tag_ids: list[str]) -> list[Tag] | None:
        with Session(self._engine) as session:
            statement = select(Tag).where(Tag.id.in_(tag_ids))

            results = session.exec(statement).all()
        return results

    def query_by_name(self, tag_name: str) -> Tag | None:
        with Session(self._engine) as session:
            statement = select(Tag).where(Tag.name == tag_name)

            result = session.exec(statement).first()
            return result

    def delete_by_name(self, tag_name: str):
        with Session(self._engine) as session:
            statement = select(Tag).where(Tag.name == tag_name)
            result = session.exec(statement).first()

            if result:
                tag_id = result.id
                tag_idx_crud = ChunkTagIndexCRUD(self._engine)
                chunk_tag_items = tag_idx_crud.query_by_tag_ids([tag_id])
                if len(chunk_tag_items) == 0:
                    session.delete(result)
                    session.commit()
                else:
                    raise Exception(f"Tag with name-{tag_name} is still in use!")

            else:
                raise Exception(f"Record with name-{tag_name} does not exist!")

    def update_by_name(
        self,
        name: str,
        new_name: str | None = None,
        prompt: str | None = None,
        config: str | None = None,
        scope: str | None = None,
        type: str | None = None,
        valid_classes: str | None = None,
    ):
        assert name != "" and prompt != "", "Invalid name or prompt: cannot be empty."

        fields_to_update = {
            "prompt": prompt,
            "config": config,
            "type": type,
            "scope": scope,
            "name": new_name,
        }

        # Add `meta` update based on valid_classes
        if valid_classes is not None:
            if type == TagType.classification.value:
                fields_to_update["meta"] = {"valid_classes": valid_classes}
            else:
                fields_to_update["meta"] = {}

        # Ensure that only non-None values are updated
        fields_to_update = {k: v for k, v in fields_to_update.items() if v is not None}

        stmt = update(Tag).where(Tag.name == name).values(**fields_to_update)

        with Session(self._engine) as session:
            session.execute(stmt)
            session.commit()

        return False

    def get_all_tags(self) -> list[str]:
        """Present tag pools option for gradio"""
        return [item.name for item in self.list_all()]


class ChunkTagIndexCRUD:
    def __init__(self, engine):
        self._engine = engine

    @cached_property
    def tag_crud(self) -> TagCRUD:
        return TagCRUD(self._engine)

    def list_all(self) -> list[ChunkTagIndex]:
        with Session(self._engine) as session:
            statement = select(ChunkTagIndex)
            results = session.exec(statement).all()

        return results

    def query_by_id(self, record_id: str) -> ChunkTagIndex | None:
        with Session(self._engine) as session:
            statement = select(ChunkTagIndex).where(ChunkTagIndex.id == record_id)

            result = session.exec(statement).first()
            return result

    def query_by_chunk_ids(self, chunk_ids: list[str]) -> dict[str, dict[str, Any]]:
        chunk_id_to_tags = defaultdict(dict)
        tag_ids = set()

        with Session(self._engine) as session:
            statement = select(ChunkTagIndex).where(
                ChunkTagIndex.chunk_id.in_(chunk_ids)
            )

            results = session.exec(statement).all()
            for result in results:
                chunk_id = result.chunk_id
                tag_id = result.tag_id
                tag_ids.add(tag_id)
                chunk_id_to_tags[chunk_id][tag_id] = {
                    "content": result.content,
                    "status": result.status,
                }

        tags: list[Tag] = self.tag_crud.query_by_ids(list(tag_ids))
        tag_id_to_tag: dict[str, str] = {tag.id: tag.name for tag in tags}
        for chunk_id, tags_dict in chunk_id_to_tags.items():
            for tag_id, tag_dict in tags_dict.items():
                tag_dict["name"] = tag_id_to_tag[tag_id]

        return chunk_id_to_tags

    def query_by_tag_ids(self, tag_ids: list[str]) -> list[ChunkTagIndex]:
        with Session(self._engine) as session:
            statement = select(ChunkTagIndex).where(ChunkTagIndex.tag_id.in_(tag_ids))

            results = session.exec(statement).all()
        return results

    def update_content_by_id(self, record_id: str, new_content: str) -> bool:
        with Session(self._engine) as session:
            statement = select(ChunkTagIndex).where(ChunkTagIndex.id == record_id)
            result = session.exec(statement).first()

            if result:
                # Update the content and date_updated fields
                result.content = new_content
                result.date_updated = datetime.utcnow()

                session.add(result)
                session.commit()

                return True
            else:
                raise Exception(f"Record with id-{record_id} does not exist!")

        return False

    def update_status_by_id(self, record_id: str, new_status: TagProcessStatus) -> bool:
        with Session(self._engine) as session:
            statement = select(ChunkTagIndex).where(ChunkTagIndex.id == record_id)
            result = session.exec(statement).first()

            if result:
                # Update the status and date_updated fields
                result.status = new_status.value
                result.date_updated = datetime.utcnow()

                session.add(result)
                session.commit()

                return True
            else:
                raise Exception(f"Record with id-{record_id} does not exist!")

        return False

    def delete_by_chunk_ids(self, chunk_ids: list[str]) -> list[ChunkTagIndex]:
        with Session(self._engine) as session:
            statement = select(ChunkTagIndex).where(
                ChunkTagIndex.chunk_id.in_(chunk_ids)
            )
            results = session.exec(statement).all()

            for result in results:
                session.delete(result)

            session.commit()
            return results

    def create(self, tag_id: str, chunk_id: str, content: str) -> str:
        default_status = TagProcessStatus.pending.value

        with Session(self._engine) as session:
            new_index: ChunkTagIndex = ChunkTagIndex(
                tag_id=tag_id, chunk_id=chunk_id, content=content, status=default_status
            )

            session.add(new_index)
            session.commit()

            return new_index.id
