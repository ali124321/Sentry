import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

random.seed(42)  # reproducible

PERSON_IDS = [f"P{i:03d}" for i in range(1, 16)]  # 15 people
LOCATIONS = ["Main Gate", "Side Gate"]
FILENAMES = [
    "app/main.py", "app/routes/auth.py", "app/routes/users.py", "app/routes/occupancy.py",
    "app/routes/code_quality.py", "app/pipeline/clean.py", "app/pipeline/github_sync.py",
    "app/pipeline/szz.py", "app/auth/dependencies.py", "app/crud/user.py",
    "src/app/dashboard/page.tsx", "src/lib/auth/AuthContext.tsx",
]
LANGUAGES = {"py": "python", "tsx": "typescript", "ts": "typescript"}
AUTHORS = [f"author{i}@example.com" for i in range(1, 6)]


async def seed_access_events(db: AsyncSession, days: int = 30):
    """Generate enough access events for 15 people across 30 days for cohort clustering."""
    logger.info("Seeding access events...")
    count = 0
    base_date = datetime(2026, 2, 1)

    for person in PERSON_IDS:
        # Each person has a behavioral pattern: early/long, hybrid, or late/short
        pattern = random.choice(["early_long", "hybrid", "late_short"])
        n_days = random.randint(15, days)

        for day_offset in random.sample(range(days), n_days):
            day = base_date + timedelta(days=day_offset)

            if pattern == "early_long":
                arrival_hour = random.randint(7, 8)
                session_hours = random.uniform(8, 10)
            elif pattern == "late_short":
                arrival_hour = random.randint(10, 11)
                session_hours = random.uniform(4, 6)
            else:
                arrival_hour = random.randint(8, 10)
                session_hours = random.uniform(6, 8)

            entry_ts = day.replace(hour=arrival_hour, minute=random.randint(0, 59))
            exit_ts = entry_ts + timedelta(hours=session_hours)
            location = random.choice(LOCATIONS)

            for ts, direction in [(entry_ts, "IN"), (exit_ts, "OUT")]:
                await db.execute(text("""
                    INSERT INTO fact_access_event (id, person_id, event_ts, direction, location)
                    VALUES (gen_random_uuid(), :person_id, :event_ts, :direction, :location)
                    ON CONFLICT (person_id, event_ts, direction) DO NOTHING
                """), {
                    "person_id": person, "event_ts": ts, "direction": direction, "location": location,
                })
                count += 1

    await db.commit()
    logger.info(f"Seeded {count} access events")
    return count


async def seed_github_data(db: AsyncSession, n_prs: int = 40):
    """Generate PRs, reviews, CI runs and deployments."""
    logger.info("Seeding GitHub data...")
    base_date = datetime(2026, 2, 1)
    repo = "ali124321/Sentry"

    for i in range(1, n_prs + 1):
        author = random.choice(AUTHORS)
        opened_at = base_date + timedelta(days=random.randint(0, 60), hours=random.randint(0, 23))
        merged = random.random() < 0.8
        lead_hours = random.uniform(1, 72)
        merged_at = opened_at + timedelta(hours=lead_hours) if merged else None
        state = "merged" if merged else random.choice(["open", "closed"])

        pr_id = str(uuid.uuid4())
        await db.execute(text("""
            INSERT INTO pull_request (id, pr_number, repo, title, author_id, state, merged, opened_at, merged_at, closed_at)
            VALUES (:id, :pr_number, :repo, :title, :author_id, :state, :merged, :opened_at, :merged_at, :closed_at)
        """), {
            "id": pr_id, "pr_number": i, "repo": repo, "title": f"PR #{i}: feature update",
            "author_id": author, "state": state, "merged": merged,
            "opened_at": opened_at, "merged_at": merged_at,
            "closed_at": merged_at if merged else (opened_at + timedelta(hours=lead_hours) if state == "closed" else None),
        })

        # Reviews — most PRs get reviewed within a few hours
        if random.random() < 0.85:
            reviewer = random.choice([a for a in AUTHORS if a != author])
            review_hours = random.uniform(0.5, 24)
            await db.execute(text("""
                INSERT INTO pr_review (id, pr_id, reviewer_id, state, submitted_at)
                VALUES (gen_random_uuid(), :pr_id, :reviewer_id, :state, :submitted_at)
            """), {
                "pr_id": pr_id, "reviewer_id": reviewer,
                "state": random.choice(["approved", "changes_requested", "commented"]),
                "submitted_at": opened_at + timedelta(hours=review_hours),
            })

        # Deployment — for merged PRs, ~70% get deployed
        if merged and random.random() < 0.7:
            deploy_sha = uuid.uuid4().hex[:40]
            deploy_at = merged_at + timedelta(hours=random.uniform(0.5, 12))
            failed = random.random() < 0.12  # ~12% change failure rate
            await db.execute(text("""
                INSERT INTO deployment (id, sha, environment, deployer_id, status, deployed_at)
                VALUES (gen_random_uuid(), :sha, :environment, :deployer_id, :status, :deployed_at)
            """), {
                "sha": deploy_sha, "environment": random.choice(["production", "staging"]),
                "deployer_id": author, "status": "failure" if failed else "success",
                "deployed_at": deploy_at,
            })

            # If it failed, add a later successful deployment (restore)
            if failed:
                restore_at = deploy_at + timedelta(hours=random.uniform(0.5, 6))
                await db.execute(text("""
                    INSERT INTO deployment (id, sha, environment, deployer_id, status, deployed_at)
                    VALUES (gen_random_uuid(), :sha, :environment, :deployer_id, 'success', :deployed_at)
                """), {
                    "sha": uuid.uuid4().hex[:40], "environment": "production",
                    "deployer_id": author, "deployed_at": restore_at,
                })

            # CI run for the deploy sha
            await db.execute(text("""
                INSERT INTO ci_check_run (id, sha, name, status, conclusion, started_at, completed_at)
                VALUES (gen_random_uuid(), :sha, :name, 'completed', :conclusion, :started, :completed)
            """), {
                "sha": deploy_sha, "name": "build-and-test",
                "conclusion": "failure" if failed else "success",
                "started": deploy_at - timedelta(minutes=15), "completed": deploy_at - timedelta(minutes=2),
            })

    await db.commit()
    logger.info(f"Seeded {n_prs} PRs with reviews, deployments and CI runs")


async def seed_code_quality_data(db: AsyncSession, repository_id: int = 1):
    """Generate code_file_metric, lint_finding and secret_scan_alert rows."""
    logger.info("Seeding code quality data...")
    now = datetime.utcnow()

    for filename in FILENAMES:
        ext = filename.split(".")[-1]
        language = LANGUAGES.get(ext, "python")
        complexity = round(random.uniform(2, 25), 2)
        churn_30 = random.randint(0, 40)
        churn_90 = churn_30 + random.randint(0, 60)
        commits_30 = random.randint(1, 15)
        authors_30 = random.randint(1, 4)

        await db.execute(text("""
            INSERT INTO code_file_metric
                (repository_id, commit_sha, filename, language, complexity_score, cognitive_complexity,
                 loc, loc_comment, functions_count, classes_count, churn_30d, churn_90d,
                 commit_count_30d, commit_count_90d, distinct_authors_30d, churn_complexity_score, snapshotted_at)
            VALUES
                (:repository_id, :commit_sha, :filename, :language, :complexity, :cognitive,
                 :loc, :loc_comment, :functions, :classes, :churn_30, :churn_90,
                 :commits_30, :commits_90, :authors_30, :hotspot, :snapshotted_at)
        """), {
            "repository_id": repository_id, "commit_sha": uuid.uuid4().hex[:40], "filename": filename,
            "language": language, "complexity": complexity, "cognitive": round(complexity * 1.3, 2),
            "loc": random.randint(50, 400), "loc_comment": random.randint(5, 50),
            "functions": random.randint(2, 20), "classes": random.randint(0, 5),
            "churn_30": churn_30, "churn_90": churn_90, "commits_30": commits_30,
            "commits_90": commits_30 + random.randint(0, 10), "authors_30": authors_30,
            "hotspot": round(complexity * churn_30 / 10, 2), "snapshotted_at": now,
        })

        # Lint findings for some files
        if random.random() < 0.5:
            for _ in range(random.randint(1, 4)):
                await db.execute(text("""
                    INSERT INTO lint_finding
                        (repository_id, commit_sha, filename, line_start, tool, rule_id, severity, message, category, status, ingested_at)
                    VALUES
                        (:repository_id, :commit_sha, :filename, :line, :tool, :rule_id, :severity, :message, :category, 'open', :ingested_at)
                """), {
                    "repository_id": repository_id, "commit_sha": uuid.uuid4().hex[:40], "filename": filename,
                    "line": random.randint(1, 200), "tool": random.choice(["ruff", "eslint"]),
                    "rule_id": random.choice(["E501", "F401", "no-unused-vars", "B008"]),
                    "severity": random.choice(["error", "warning", "warning", "info"]),
                    "message": "Example lint finding for seeded test data",
                    "category": random.choice(["style", "bug-risk", "unused"]),
                    "ingested_at": now,
                })

    # A couple of secret alerts
    for _ in range(3):
        await db.execute(text("""
            INSERT INTO secret_scan_alert
                (repository_id, secret_type, secret_type_display, tool, filename, commit_sha,
                 line_number, validity, state, push_protection_bypassed, created_at, updated_at, ingested_at)
            VALUES
                (:repository_id, :secret_type, :secret_type_display, 'github', :filename, :commit_sha,
                 :line, :validity, 'open', false, :now, :now, :now)
        """), {
            "repository_id": repository_id, "secret_type": "aws_access_key_id",
            "secret_type_display": "AWS Access Key ID", "filename": random.choice(FILENAMES),
            "commit_sha": uuid.uuid4().hex[:40], "line": random.randint(1, 100),
            "validity": random.choice(["active", "inactive"]), "now": now,
        })

    await db.commit()
    logger.info("Seeded code quality data")


async def seed_all_test_data(db: AsyncSession) -> dict:
    """Run all seed functions."""
    access_count = await seed_access_events(db)
    await seed_github_data(db)
    await seed_code_quality_data(db)
    return {
        "access_events": access_count,
        "persons": len(PERSON_IDS),
        "files_seeded": len(FILENAMES),
        "message": "Test data seeded successfully. Now run: SZZ tracing, defect-risk model, cohort model, occupancy/DORA view refreshes.",
    }