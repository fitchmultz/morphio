"""Admin usage export endpoints.

Provides CSV export of LLM usage data for billing and analytics.
"""

import csv
import io
import logging
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models.llm_usage import LLMUsageRecord
from ...models.user import User
from ...services.security import get_current_user
from ...utils.decorators import require_auth
from ...utils.enums import ResponseStatus
from ...utils.response_utils import create_response
from ...utils.route_helpers import common_responses, handle_route_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usage", tags=["Admin"])


@router.get(
    "/export",
    operation_id="export_llm_usage",
    responses={
        200: {"description": "CSV file download"},
        403: {"description": "Not authorized"},
        **common_responses,
    },
)
@require_auth
@handle_route_errors
async def export_llm_usage(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    start: date | None = Query(None, description="Start date (inclusive)"),
    end: date | None = Query(None, description="End date (inclusive)"),
    format: str = Query("csv", description="Export format (only csv supported)"),
):
    """
    Export LLM usage records as CSV for billing and analytics.

    Aggregates usage by date, user, provider, and model.
    Returns: date, user_id, user_email, provider, model, total_tokens, estimated_cost
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to export usage data",
        )

    if format.lower() != "csv":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV format is currently supported",
        )

    # Build query with date filters
    query = (
        select(
            func.date(LLMUsageRecord.created_at).label("date"),
            LLMUsageRecord.user_id,
            User.email.label("user_email"),
            LLMUsageRecord.provider,
            LLMUsageRecord.model,
            func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
            func.sum(LLMUsageRecord.cost_usd).label("estimated_cost"),
        )
        .join(User, LLMUsageRecord.user_id == User.id)
        .where(LLMUsageRecord.deleted_at.is_(None))
        .group_by(
            func.date(LLMUsageRecord.created_at),
            LLMUsageRecord.user_id,
            User.email,
            LLMUsageRecord.provider,
            LLMUsageRecord.model,
        )
        .order_by(func.date(LLMUsageRecord.created_at).desc())
    )

    if start:
        start_datetime = datetime.combine(start, datetime.min.time())
        query = query.where(LLMUsageRecord.created_at >= start_datetime)

    if end:
        end_datetime = datetime.combine(end, datetime.max.time())
        query = query.where(LLMUsageRecord.created_at <= end_datetime)

    result = await db.execute(query)
    rows = result.all()

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        ["date", "user_id", "user_email", "provider", "model", "total_tokens", "estimated_cost"]
    )

    # Write data rows
    for row in rows:
        writer.writerow(
            [
                row.date.isoformat() if row.date else "",
                row.user_id,
                row.user_email or "",
                row.provider,
                row.model,
                row.total_tokens or 0,
                float(row.estimated_cost) if row.estimated_cost else 0.0,
            ]
        )

    output.seek(0)

    # Generate filename with date range
    filename = "llm_usage"
    if start:
        filename += f"_from_{start.isoformat()}"
    if end:
        filename += f"_to_{end.isoformat()}"
    filename += ".csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/summary",
    operation_id="get_llm_usage_summary",
    responses={403: {"description": "Not authorized"}, **common_responses},
)
@require_auth
@handle_route_errors
async def get_llm_usage_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    start: date | None = Query(None, description="Start date (inclusive)"),
    end: date | None = Query(None, description="End date (inclusive)"),
):
    """
    Get summary statistics of LLM usage for display in admin dashboard.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view usage summary",
        )

    # Build date filters (shared between queries)
    filters = [LLMUsageRecord.deleted_at.is_(None)]
    if start:
        filters.append(LLMUsageRecord.created_at >= datetime.combine(start, datetime.min.time()))
    if end:
        filters.append(LLMUsageRecord.created_at <= datetime.combine(end, datetime.max.time()))

    # Total tokens and cost
    totals_query = select(
        func.count(LLMUsageRecord.id).label("total_requests"),
        func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
        func.sum(LLMUsageRecord.cost_usd).label("total_cost"),
    ).where(*filters)

    totals_result = await db.execute(totals_query)
    totals = totals_result.one()

    # Usage by provider
    provider_query = (
        select(
            LLMUsageRecord.provider,
            func.count(LLMUsageRecord.id).label("requests"),
            func.sum(LLMUsageRecord.total_tokens).label("tokens"),
            func.sum(LLMUsageRecord.cost_usd).label("cost"),
        )
        .where(*filters)
        .group_by(LLMUsageRecord.provider)
        .order_by(func.sum(LLMUsageRecord.total_tokens).desc())
    )

    provider_result = await db.execute(provider_query)
    providers = provider_result.all()

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Usage summary retrieved",
        data={
            "total_requests": totals.total_requests or 0,
            "total_tokens": totals.total_tokens or 0,
            "total_cost_usd": float(totals.total_cost) if totals.total_cost else 0.0,
            "by_provider": [
                {
                    "provider": p.provider,
                    "requests": p.requests,
                    "tokens": p.tokens or 0,
                    "cost_usd": float(p.cost) if p.cost else 0.0,
                }
                for p in providers
            ],
        },
    )
