# backend/app/core/mixins.py
from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declared_attr

class SoftDeleteMixin:
    """
    A mixin to add soft delete (archive) capabilities to any model.
    It automatically adds the `is_archived` and `archived_by_id` columns,
    along with the `archived_by` relationship to the User model.
    """
    is_archived = Column(Boolean, default=False, nullable=False)
    archived_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    @declared_attr
    def archived_by(cls):
        return relationship("app.modules.users.models.User", foreign_keys=[cls.archived_by_id])
