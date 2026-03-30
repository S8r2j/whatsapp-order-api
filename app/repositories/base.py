"""
Generic async CRUD repository.

All concrete repositories inherit from ``BaseRepository`` to get standard
create / read / update / delete operations without boilerplate.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Provides async CRUD operations for a SQLAlchemy model.

    Args:
        model: The SQLAlchemy model class this repository manages.
    """

    def __init__(self, model: Type[ModelType]) -> None:
        self.model = model

    async def get(self, db: AsyncSession, id: uuid.UUID) -> Optional[ModelType]:
        """Fetch a single record by primary key.

        Returns:
            The model instance, or ``None`` if not found.
        """
        result = await db.execute(select(self.model).where(self.model.id == id))  # type: ignore[attr-defined]
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        filters: Optional[List[Any]] = None,
        order_by: Optional[Any] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[ModelType], int]:
        """Fetch a paginated list of records with optional filters.

        Args:
            db: Async database session.
            filters: List of SQLAlchemy filter expressions.
            order_by: Column to sort by (default: created_at desc).
            skip: Number of records to skip.
            limit: Maximum records to return.

        Returns:
            Tuple of (list of records, total count matching filters).
        """
        base_query = select(self.model)
        count_query = select(func.count()).select_from(self.model)

        if filters:
            for f in filters:
                base_query = base_query.where(f)
                count_query = count_query.where(f)

        if order_by is not None:
            base_query = base_query.order_by(order_by)
        else:
            base_query = base_query.order_by(self.model.created_at.desc())  # type: ignore[attr-defined]

        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        result = await db.execute(base_query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> ModelType:
        """Insert a new record.

        Args:
            db: Async database session.
            obj_in: Dictionary of column values.

        Returns:
            The newly created model instance (refreshed from DB).
        """
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, updates: Dict[str, Any]
    ) -> ModelType:
        """Apply a partial update to an existing record.

        Args:
            db: Async database session.
            db_obj: The existing model instance to update.
            updates: Dictionary of columns to update and their new values.

        Returns:
            The updated model instance.
        """
        for field, value in updates.items():
            if value is not None or field in updates:
                setattr(db_obj, field, value)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: uuid.UUID) -> Optional[ModelType]:
        """Delete a record by primary key.

        Returns:
            The deleted instance, or ``None`` if it was not found.
        """
        db_obj = await self.get(db, id)
        if db_obj is not None:
            await db.delete(db_obj)
            await db.flush()
        return db_obj
