from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.auth.suppression import suppress_small_groups

router = APIRouter(prefix="/api/v1/suppression", tags=["suppression"])


@router.get("/demo")
async def suppression_demo(current_user=Depends(get_current_user)):
    """
    Demo endpoint showing suppression in action.
    Groups with < 5 people have their metrics hidden.
    """
    sample_data = [
        {"cohort": "Engineering", "person_count": 12, "avg_hours": 7.5},
        {"cohort": "Design", "person_count": 3, "avg_hours": 6.2},   # suppressed
        {"cohort": "Product", "person_count": 8, "avg_hours": 7.1},
        {"cohort": "Sales", "person_count": 2, "avg_hours": 8.0},    # suppressed
        {"cohort": "Finance", "person_count": 6, "avg_hours": 6.8},
    ]

    return {
        "min_group_size": 5,
        "note": "Cohorts with fewer than 5 people have metrics suppressed for privacy.",
        "data": suppress_small_groups(
            sample_data,
            count_field="person_count",
            suppress_fields=["avg_hours"],
        )
    }