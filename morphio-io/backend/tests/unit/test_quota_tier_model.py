"""Purpose: Guard quota-tier ORM compatibility with the historical schema.
Responsibilities: Verify renamed app terminology still maps onto migrated database columns.
Scope: Unit coverage for the `QuotaTierAssignment` SQLAlchemy model definition.
Usage: Run with pytest as part of backend unit validation.
Invariants/Assumptions: Public code should use `tier`, while the persisted column name remains `plan` for migration stability.
"""

from app.models.quota_tier import QuotaTierAssignment


def test_quota_tier_assignment_maps_tier_to_historical_plan_column() -> None:
    tier_column = QuotaTierAssignment.__table__.columns["plan"]

    assert tier_column.name == "plan"
    assert QuotaTierAssignment.tier.property.columns[0].name == "plan"
