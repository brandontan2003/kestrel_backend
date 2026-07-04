from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declared_attr
from sqlalchemy.sql import func


class Auditable:
    """Automatically adds created_at and updated_at to any model."""

    @declared_attr
    def created_at(cls):
        # Generates timestamp on insert
        return Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    @declared_attr
    def updated_at(cls):
        # Generates timestamp on insert AND updates it automatically on save/update
        return Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), server_default=func.now())
