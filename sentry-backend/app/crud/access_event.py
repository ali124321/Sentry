from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.schemas.access_event import AccessEventIn
import logging
import json
import math

logger = logging.getLogger(__name__)


async def bulk_upsert_access_events(
    db: AsyncSession,
    events: list[AccessEventIn]
) -> dict:
    if not events:
        return {"ingested": 0, "skipped": 0}

    ingested = 0
    skipped = 0

    for event in events:
        try:
            # Strip timezone for storage
            event_ts = event.event_ts.replace(tzinfo=None) if event.event_ts.tzinfo else event.event_ts

            await db.execute(
                text("""
                    INSERT INTO fact_access_event
                        (id, person_id, event_ts, direction, location)
                    VALUES
                        (gen_random_uuid(), :person_id, :event_ts, :direction, :location)
                    ON CONFLICT (person_id, event_ts, direction)
                    DO NOTHING
                """),
                {
                    "person_id": event.person_id,
                    "event_ts": event_ts,
                    "direction": event.direction,
                    "location": event.location,
                }
            )
            ingested += 1
        except Exception as e:
            logger.error(f"Error inserting event: {e}")
            skipped += 1

    await db.commit()
    return {"ingested": ingested, "skipped": skipped}


async def bulk_upsert_raw_events(
    db: AsyncSession,
    payloads: list[dict]
) -> None:
    for payload in payloads:
        clean_payload = {
            k: (None if (isinstance(v, float) and math.isnan(v)) else v)
            for k, v in payload.items()
        }
        payload_json = json.dumps(clean_payload, default=str)
        await db.execute(
            text("""
                INSERT INTO raw_access_events (id, payload)
                VALUES (gen_random_uuid(), CAST(:payload AS jsonb))
            """),
            {"payload": payload_json}
        )
    await db.commit()