# mypy: ignore-errors

from collections import defaultdict
from datetime import datetime

from ktem.db.base_models import BaseTag, TagProcessStatus, TagType
from ktem.db.models import ChunkTagIndex, Tag
from sqlmodel import Session, select


class TagCRUD:
    def __init__(self, engine):
        self._engine = engine

    def list_all(self) -> list[dict]:
        with Session(self._engine) as session:
            statement = select(Tag)
            results = session.exec(statement).all()

        records: list[dict] = []
        for result in results:
            records += [dict(result)]

        return records

    def create(
        self,
        name: str,
        prompt: str,
        config: str,
        type: str = "text",
        scope: str = "chunk",
        valid_classes: str | None = None,
    ) -> str | None:
        meta = {}
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
                type=type,
                scope=scope,
                meta=meta,
            )
            session.add(tag)
            session.commit()

            return tag.id

    def query_by_id(self, tag_id: str) -> BaseTag | None:
        with Session(self._engine) as session:
            statement = select(Tag).where(Tag.id == tag_id)

            result = session.exec(statement).first()
            return result

    def query_by_ids(self, tag_ids: list[str]) -> list[dict]:
        with Session(self._engine) as session:
            statement = select(Tag).where(Tag.id.in_(tag_ids))

            results = session.exec(statement).all()
            results = [dict(result) for result in results]
        return results

    def query_by_name(self, tag_name: str) -> BaseTag | None:
        with Session(self._engine) as session:
            statement = select(Tag).where(Tag.name == tag_name)

            result = session.exec(statement).first()
            return result

    def delete_by_name(self, tag_name: str) -> bool:
        with Session(self._engine) as session:
            statement = select(Tag).where(Tag.name == tag_name)
            result = session.exec(statement).first()

            if result:
                session.delete(result)
                session.commit()
                return True

        return False

    def update_by_name(
        self,
        name: str,
        prompt: str | None = None,
        config: str | None = None,
        scope: str | None = None,
        type: str | None = None,
        valid_classes: str | None = None,
    ):
        with Session(self._engine) as session:
            statement = select(Tag).where(Tag.name == name)
            result = session.exec(statement).first()

            if result:
                # Update the status and date_updated fields
                if prompt is not None:
                    result.prompt = prompt

                if config is not None:
                    result.config = config

                if type is not None:
                    result.type = type

                if scope is not None:
                    result.scope = scope

                if valid_classes is not None:
                    if result.type != TagType.classification.value:
                        result.meta = {}
                    else:
                        result.meta = {"valid_classes": valid_classes}

                session.add(result)
                session.commit()

                return True

        return False


class ChunkTagIndexCRUD:
    def __init__(self, engine):
        self._engine = engine

    @property
    def tag_crud(self) -> TagCRUD:
        return TagCRUD(self._engine)

    def list_all(self) -> list[dict]:
        with Session(self._engine) as session:
            statement = select(ChunkTagIndex)
            results = session.exec(statement).all()

            results = [dict(result) for result in results]
        return results

    def query_by_id(self, record_id: str) -> dict | None:
        with Session(self._engine) as session:
            statement = select(ChunkTagIndex).where(ChunkTagIndex.id == record_id)

            result = session.exec(statement).first()
            return result

    def query_by_chunk_ids(self, chunk_ids: list[str]) -> dict[str, dict]:
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

        tags = self.tag_crud.query_by_ids(list(tag_ids))
        tag_id_to_tag = {tag["id"]: tag["name"] for tag in tags}
        for chunk_id, tags_dict in chunk_id_to_tags.items():
            for tag_id, tag_dict in tags_dict.items():
                tag_dict["name"] = tag_id_to_tag[tag_id]

        return chunk_id_to_tags

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
