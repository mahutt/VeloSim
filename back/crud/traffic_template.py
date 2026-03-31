"""
MIT License

Copyright (c) 2025 VeloSim Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from typing import List, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from back.exceptions import BadRequestError, ItemNotFoundError
from back.models.traffic_template import TrafficTemplate
from back.schemas.traffic_template import TrafficTemplateCreate, TrafficTemplateUpdate


class TrafficTemplateCRUD:
    """CRUD operations for traffic templates keyed by user-provided stable keys."""

    def create(
        self, db: Session, template_data: TrafficTemplateCreate
    ) -> TrafficTemplate:
        """Create a new traffic template.

        Args:
            db: Active database session.
            template_data: Template payload to persist.

        Returns:
            Newly created traffic template model.
        """
        if not template_data.key:
            raise BadRequestError("Traffic template key is required")
        if not template_data.content:
            raise BadRequestError("Traffic template content is required")

        db_template = TrafficTemplate(
            key=template_data.key,
            content=template_data.content,
            description=template_data.description,
        )
        db.add(db_template)
        db.commit()
        db.refresh(db_template)
        return db_template

    def get_by_key(self, db: Session, key: str) -> TrafficTemplate:
        """Retrieve a traffic template by key.

        Args:
            db: Active database session.
            key: Stable template key.

        Returns:
            Matching traffic template model.
        """
        template = db.query(TrafficTemplate).filter(TrafficTemplate.key == key).first()
        if not template:
            raise ItemNotFoundError(f"Traffic template '{key}' not found")
        return template

    def get_optional_by_key(self, db: Session, key: str) -> TrafficTemplate | None:
        """Retrieve a traffic template by key, returning None when not found.

        Args:
            db: Active database session.
            key: Stable template key.

        Returns:
            Matching traffic template model, or None when missing.
        """
        return db.query(TrafficTemplate).filter(TrafficTemplate.key == key).first()

    def get_all(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> Tuple[List[TrafficTemplate], int]:
        """Get all traffic templates with pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Tuple of templates for the requested page and total row count.
        """
        total = db.query(func.count(TrafficTemplate.id)).scalar() or 0
        templates = (
            db.query(TrafficTemplate)
            .order_by(TrafficTemplate.id.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return templates, total

    def update(
        self, db: Session, key: str, template_data: TrafficTemplateUpdate
    ) -> TrafficTemplate:
        """Update mutable fields for a traffic template by key.

        Args:
            db: Active database session.
            key: Stable template key to update.
            template_data: Partial update payload.

        Returns:
            Updated traffic template model.
        """
        template = self.get_by_key(db, key)

        update_data = template_data.model_dump(exclude_unset=True)
        if not update_data:
            raise BadRequestError("No valid fields to update")

        for field, value in update_data.items():
            setattr(template, field, value)

        db.commit()
        db.refresh(template)
        return template

    def delete(self, db: Session, key: str) -> None:
        """Delete a traffic template by key.

        Args:
            db: Active database session.
            key: Stable template key to delete.

        Returns:
            None.
        """
        template = self.get_by_key(db, key)
        db.delete(template)
        db.commit()


traffic_template_crud = TrafficTemplateCRUD()
