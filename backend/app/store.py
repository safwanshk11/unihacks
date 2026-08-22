from datetime import datetime
import os

from sqlalchemy import JSON, Column, DateTime, Integer, String, Table, create_engine, select
from sqlalchemy.orm import Session, registry

from app.models import EnrichedProduct

database_path = os.environ.get("CATALOG_DB_PATH", "./catalog.db")
engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
mapper_registry = registry()

products_table = Table(
    "products",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("short_desc", String, nullable=False),
    Column("classpath", String, nullable=False),
    Column("status", String, nullable=False, default="pending"),
    Column("created_at", DateTime, nullable=False),
    Column("data", JSON, nullable=False),
)


def init_db() -> None:
    mapper_registry.metadata.create_all(engine)


def clear_products() -> None:
    with Session(engine) as session:
        session.execute(products_table.delete())
        session.commit()


def insert_product(product: EnrichedProduct) -> EnrichedProduct:
    with Session(engine) as session:
        result = session.execute(
            products_table.insert().values(
                short_desc=product.short_desc.value,
                classpath=product.classpath.value,
                status=product.status,
                created_at=product.created_at,
                data=product.model_dump(mode="json"),
            )
        )
        session.commit()
        product.id = result.inserted_primary_key[0]
        return product


def _to_product(row) -> EnrichedProduct:
    product = EnrichedProduct.model_validate(row.data)
    product.id = row.id
    return product


def list_products() -> list[EnrichedProduct]:
    with Session(engine) as session:
        rows = session.execute(select(products_table).order_by(products_table.c.id.desc())).all()
        return [_to_product(row) for row in rows]


def get_product(product_id: int) -> EnrichedProduct | None:
    with Session(engine) as session:
        row = session.execute(
            select(products_table).where(products_table.c.id == product_id)
        ).first()
        return _to_product(row) if row else None


def update_product(product_id: int, product: EnrichedProduct) -> None:
    with Session(engine) as session:
        session.execute(
            products_table.update()
            .where(products_table.c.id == product_id)
            .values(
                short_desc=product.short_desc.value,
                classpath=product.classpath.value,
                status=product.status,
                data=product.model_dump(mode="json"),
            )
        )
        session.commit()
