from typing import Any

from ktem.db.models import RerankingTable
from sqlalchemy import select, update

from kotaemon.rerankings.factory import RerankingVendor

from .base import BaseCRUD


class RerankingCRUD(BaseCRUD):
    """CRUD operations for the reranking model table."""

    def clear_defaults(self) -> None:
        self.session.execute(update(RerankingTable).values(default=False))

    def create(
        self,
        name: str,
        vendor: RerankingVendor,
        spec: dict[str, Any],
        *,
        default: bool = False,
    ) -> RerankingTable:
        if not name:
            raise ValueError("Name must not be empty")
        if self.get(name) is not None:
            raise ValueError(f"Reranking model '{name}' already exists")
        if default:
            self.clear_defaults()
        item = RerankingTable(name=name, vendor=vendor, spec=spec, default=default)
        self.session.add(item)
        self.commit()
        self.session.refresh(item)
        return item

    def get(self, name: str) -> RerankingTable | None:
        return self.session.get(RerankingTable, name)

    def list_all(self) -> list[RerankingTable]:
        return list(self.session.scalars(select(RerankingTable)).all())

    def update(
        self,
        name: str,
        *,
        vendor: RerankingVendor | None = None,
        spec: dict[str, Any] | None = None,
        default: bool | None = None,
        new_name: str | None = None,
    ) -> RerankingTable:
        item = self.get(name)
        if item is None:
            raise ValueError(f"Reranking model '{name}' not found")
        if new_name and new_name != name:
            if self.get(new_name) is not None:
                raise ValueError(f"Reranking model '{new_name}' already exists")
            if default:
                self.clear_defaults()
            new_item = RerankingTable(
                name=new_name,
                vendor=vendor if vendor is not None else item.vendor,
                spec=spec if spec is not None else item.spec,
                default=default if default is not None else item.default,
            )
            self.session.delete(item)
            self.session.add(new_item)
            self.commit()
            self.session.refresh(new_item)
            return new_item
        if default:
            self.clear_defaults()
        if vendor is not None:
            item.vendor = vendor
        if spec is not None:
            item.spec = spec
        if default is not None:
            item.default = default
        self.commit()
        self.session.refresh(item)
        return item

    def delete(self, name: str) -> None:
        item = self.get(name)
        if item is None:
            raise ValueError(f"Reranking model '{name}' not found")
        self.session.delete(item)
        self.commit()
