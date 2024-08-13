import copy
from datetime import datetime

from sqlmodel import Session, select

from ktem.db.base_models import TagType, TagProcessStatus
from ktem.db.models import Tag, ChunkTagIndex


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

    def create(self, name: str, prompt: str, config: str, type: str = "text", valid_classes: str = None) -> str:
        print(
            f"On creating tag with "
            f"name: {name}, "
            f"prompt: {prompt}, "
            f"config: {config}, "
            f"type: {type}, "
            f"valid_classes: {valid_classes}"
        )

        meta = {}
        if type == TagType.classification:
            assert valid_classes is not None and valid_classes != "", "Invalid valid classes!"
            meta["valid_classes"] = valid_classes

        with Session(self._engine) as session:
            # tag name must be unique
            existed_result = self.query_by_name(name)
            if existed_result:
                raise Exception(
                    f"Tag name: {name} has already been existed!"
                )

            tag: Tag = Tag(
                name=name,
                prompt=prompt,
                config=config,
                type=type,
                meta=meta
            )
            session.add(tag)
            session.commit()

            return tag.id

    def query_by_id(self, tag_id: str) -> dict | None:
        with Session(self._engine) as session:
            statement = select(Tag).where(Tag.id == tag_id)

            result = session.exec(statement).first()
            if result:
                return dict(result)
        return

    def query_by_name(self, tag_name: str) -> dict | None:
        with Session(self._engine) as session:
            statement = select(Tag).where(Tag.name == tag_name)

            result = session.exec(statement).first()
            if result:
                return dict(result)

        return


class ChunkTagIndexCRUD:
    def __init__(self, engine):
        self._engine = engine

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
            if result:
                return dict(result)
        return

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

    def create(self, tag_id: str, chunk_id: str, content: str) -> str:
        print(f"On creating chunk-tag-index with "
              f"tag_id: {tag_id}, "
              f"chunk_id: {chunk_id}, "
              )

        default_status = TagProcessStatus.pending.value

        with Session(self._engine) as session:
            new_index: ChunkTagIndex = ChunkTagIndex(
                tag_id=tag_id,
                chunk_id=chunk_id,
                content=content,
                status=default_status
            )

            session.add(new_index)
            session.commit()

            return new_index.id
