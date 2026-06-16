from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import require_role
from app.core.database import get_db
from app.schemas.access_event import AccessEventIn, IngestResponse
from app.crud.access_event import bulk_upsert_access_events, bulk_upsert_raw_events
from app.pipeline.clean import clean
import tempfile
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


def parse_cleaned_df(df) -> list[AccessEventIn]:
    events = []
    for _, row in df.iterrows():
        try:
            event = AccessEventIn(
                badge_code=row.get("badge_code") if str(row.get("badge_code")) != "nan" else None,
                person_id=str(row["person_id"]),
                event_ts=row["event_ts"],
                direction=str(row["direction"]),
                location=row.get("location") if str(row.get("location")) != "nan" else None,
            )
            events.append(event)
        except Exception as e:
            logger.warning(f"Skipping invalid row: {e}")
    return events


@router.post("/access", response_model=IngestResponse)
async def ingest_access_log(
    file: UploadFile = File(...),
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are accepted")

    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        # Run clean pipeline
        df = clean(input_path=tmp_path)
        events = parse_cleaned_df(df)
        total_rows = len(df)

        # Store raw payloads
        raw_payloads = df.to_dict(orient="records")
        await bulk_upsert_raw_events(db, raw_payloads)

        # Upsert clean events
        result = await bulk_upsert_access_events(db, events)

    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to process file: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return IngestResponse(
        message="Ingestion complete",
        total_rows=total_rows,
        ingested=result["ingested"],
        skipped=result["skipped"],
    )


@router.post("/access/json", response_model=IngestResponse)
async def ingest_access_json(
    events: list[AccessEventIn],
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    total_rows = len(events)
    result = await bulk_upsert_access_events(db, events)
    return IngestResponse(
        message="Ingestion complete",
        total_rows=total_rows,
        ingested=result["ingested"],
        skipped=result["skipped"],
    )