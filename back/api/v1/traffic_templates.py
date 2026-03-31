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

import math

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from back.auth.dependency import get_user_id
from back.crud.traffic_template import traffic_template_crud
from back.crud.user import user_crud
from back.database.session import get_db
from back.exceptions import (
    BadRequestError,
    ItemNotFoundError,
    UnexpectedError,
    VelosimPermissionError,
)
from back.schemas.traffic_template import (
    TrafficTemplateCreate,
    TrafficTemplateCreateRequest,
    TrafficTemplateListResponse,
    TrafficTemplateResponse,
    TrafficTemplateUpdate,
    TrafficTemplateUpdateRequest,
    TrafficTemplateValidationRequest,
    TrafficTemplateValidationResponse,
)
from grafana_logging.logger import get_logger
from sim.entities.map_payload import TrafficConfig
from sim.traffic.traffic_parser import TrafficParseError, TrafficParser

logger = get_logger(__name__)

router = APIRouter(prefix="/trafficTemplates", tags=["trafficTemplates"])


def _ensure_admin(requesting_user: int, db: Session) -> None:
    """Require that the requesting user exists, is enabled, and is admin."""
    user = user_crud.get(db, requesting_user)
    if not user:
        raise VelosimPermissionError("User not found; cannot manage traffic templates.")
    if not user.is_enabled:
        raise VelosimPermissionError(
            "User account is disabled; cannot manage traffic templates."
        )
    if not user.is_admin:
        raise VelosimPermissionError(
            "Admin role required; cannot manage traffic templates."
        )


@router.post("/validate", response_model=TrafficTemplateValidationResponse)
def validate_traffic_template(
    request: TrafficTemplateValidationRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> TrafficTemplateValidationResponse:
    """Validate CSV template content without creating a template.

    Args:
        request: Request payload containing CSV content to validate.
        requesting_user: ID of the authenticated user.
        db: Active database session.

    Returns:
        Validation result with a boolean status and parse errors, if any.
    """
    _ensure_admin(requesting_user, db)

    parser = TrafficParser(
        TrafficConfig(
            traffic_csv_data=request.content,
            sim_start_time="day1:00:00",
            sim_end_time="day2:00:00",
        )
    )
    try:
        parser.parse()
        return TrafficTemplateValidationResponse(valid=True, errors=[])
    except TrafficParseError as err:
        return TrafficTemplateValidationResponse(valid=False, errors=err.errors)


@router.get("/example")
def get_traffic_template_example(
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Return an example payload for traffic template creation.

    Args:
        requesting_user: ID of the authenticated user.
        db: Active database session.

    Returns:
        Example request payload with key, CSV content, and description fields.
    """

    return {
        "key": "example_template",
        "content": (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,08:00,"((-73.5731,45.5013),(-73.5610,45.5070))",'
            "morning_congestion,1800,0.65"
        ),
        "description": "Example traffic template CSV content",
    }


@router.get("/", response_model=TrafficTemplateListResponse)
def get_traffic_templates(
    skip: int = Query(0, ge=0, description="Number of templates to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of templates to retrieve"),
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> TrafficTemplateListResponse:
    """List all traffic templates with pagination.

    Args:
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        requesting_user: ID of the authenticated user.
        db: Active database session.

    Returns:
        Paginated traffic template list response.
    """

    templates, total = traffic_template_crud.get_all(db, skip=skip, limit=limit)
    total_pages = math.ceil(total / limit) if total > 0 else 0
    page = (skip // limit) + 1

    return TrafficTemplateListResponse(
        templates=[TrafficTemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=page,
        per_page=limit,
        total_pages=total_pages,
    )


@router.get("/{template_key}", response_model=TrafficTemplateResponse)
def get_traffic_template(
    template_key: str,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> TrafficTemplateResponse:
    """Get a traffic template by key.

    Args:
        template_key: Stable template key.
        requesting_user: ID of the authenticated user.
        db: Active database session.

    Returns:
        Traffic template response for the requested key.
    """

    template = traffic_template_crud.get_by_key(db, template_key)
    return TrafficTemplateResponse.model_validate(template)


@router.post(
    "/", response_model=TrafficTemplateResponse, status_code=status.HTTP_201_CREATED
)
def create_traffic_template(
    request: TrafficTemplateCreateRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> TrafficTemplateResponse:
    """Create a traffic template with a user-provided stable key (admin only).

    Args:
        request: Template create request containing key and CSV content.
        requesting_user: ID of the authenticated user.
        db: Active database session.

    Returns:
        Newly created traffic template response.
    """
    _ensure_admin(requesting_user, db)

    try:
        existing = traffic_template_crud.get_optional_by_key(db, request.key)
        if existing:
            raise BadRequestError(
                f"A traffic template with key '{request.key}' already exists."
            )

        parser = TrafficParser(
            TrafficConfig(
                traffic_csv_data=request.content,
                sim_start_time="day1:00:00",
                sim_end_time="day2:00:00",
            )
        )
        parser.parse()

        template = traffic_template_crud.create(
            db,
            TrafficTemplateCreate(
                key=request.key,
                content=request.content,
                description=request.description,
            ),
        )
        return TrafficTemplateResponse.model_validate(template)
    except (BadRequestError, ItemNotFoundError, VelosimPermissionError):
        raise
    except TrafficParseError as err:
        raise BadRequestError(
            "Invalid traffic template content: " + "; ".join(err.errors)
        )
    except IntegrityError:
        raise BadRequestError(
            f"A traffic template with key '{request.key}' already exists."
        )
    except Exception as err:
        logger.exception("Unexpected error: %s", err)
        raise UnexpectedError() from err


@router.put("/{template_key}", response_model=TrafficTemplateResponse)
def update_traffic_template(
    template_key: str,
    request: TrafficTemplateUpdateRequest,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> TrafficTemplateResponse:
    """Update mutable fields for a traffic template (admin only).

    Args:
        template_key: Stable template key to update.
        request: Template update request with mutable fields.
        requesting_user: ID of the authenticated user.
        db: Active database session.

    Returns:
        Updated traffic template response.
    """
    _ensure_admin(requesting_user, db)

    try:
        if request.content is not None:
            parser = TrafficParser(
                TrafficConfig(
                    traffic_csv_data=request.content,
                    sim_start_time="day1:00:00",
                    sim_end_time="day2:00:00",
                )
            )
            parser.parse()

        template = traffic_template_crud.update(
            db,
            template_key,
            TrafficTemplateUpdate(
                content=request.content,
                description=request.description,
            ),
        )
        return TrafficTemplateResponse.model_validate(template)
    except (BadRequestError, ItemNotFoundError, VelosimPermissionError):
        raise
    except TrafficParseError as err:
        raise BadRequestError(
            "Invalid traffic template content: " + "; ".join(err.errors)
        )
    except Exception as err:
        logger.exception("Unexpected error: %s", err)
        raise UnexpectedError() from err


@router.delete("/{template_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_traffic_template(
    template_key: str,
    requesting_user: int = Depends(get_user_id),
    db: Session = Depends(get_db),
) -> None:
    """Delete a traffic template by key (admin only).

    Args:
        template_key: Stable template key to delete.
        requesting_user: ID of the authenticated user.
        db: Active database session.

    Returns:
        None.
    """
    _ensure_admin(requesting_user, db)

    try:
        traffic_template_crud.delete(db, template_key)
    except (BadRequestError, ItemNotFoundError, VelosimPermissionError):
        raise
    except Exception as err:
        logger.exception("Unexpected error: %s", err)
        raise UnexpectedError() from err
