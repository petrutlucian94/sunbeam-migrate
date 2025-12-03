# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import datetime
import typing
import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import as_declarative

from sunbeam_migrate.db import session_utils


@as_declarative()
class BaseModel(object):
    """Base model class."""

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), nullable=True)
    archived = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.datetime.now())
    updated_at = Column(DateTime, onupdate=lambda: datetime.datetime.now())

    @session_utils.ensure_session
    def save(self, session=None):
        """Save this database record."""
        if not self.uuid:
            self.uuid = str(uuid.uuid4())

        session.add(self)
        session.flush()
        session.refresh(self)
        return self.id

    def to_dict(self, serializable=True) -> dict[str, typing.Any]:
        """Convert the model to dict."""
        _dict = {col.name: getattr(self, col.name) for col in self.__table__.columns}  # type: ignore [attr-defined]
        for key, value in _dict.items():
            if isinstance(value, datetime.datetime):
                _dict[key] = value.isoformat()
        return _dict

    def __eq__(self, other) -> bool:
        """Compare database records."""
        if not isinstance(other, BaseModel):
            return False

        return bool(
            self.__table__.name == other.__table__.name and self.uuid == other.uuid  # type: ignore [attr-defined]
        )

    @session_utils.ensure_session
    def delete(self, session=None):
        """Delete this database record."""
        session.query(self.__class__).filter_by(id=self.id).delete()


class Migration(BaseModel):
    """Migration model."""

    __tablename__ = "migrations"

    service = Column(Text)
    resource_type = Column(Text)
    source_cloud = Column(Text)
    destination_cloud = Column(Text)

    # Migrated resource name.
    source_id = Column(Text)
    # Resulting resource name.
    destination_id = Column(Text)

    # Whether the resource was removed on the source side after
    # a successful migration.
    source_removed = Column(Boolean, default=False)
    # Whether the resource was migrated externally.
    external = Column(Boolean, default=False)

    status = Column(Text)
    error_message = Column(Text)
