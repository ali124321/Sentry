import logging
import time
from datetime import datetime, timezone
from pydriller import Repository
from github import Github, GithubException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.auth.config import auth_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Rate-limit-aware GitHub API helper ──────────────────────────────────────

def get_github_client(token: str = None) -> Github:
    t = token or auth_settings.GITHUB_TOKEN
    if not t:
        raise ValueError("No GitHub token available (pass one or set GITHUB_TOKEN in .env)")
    return Github(t)


def rate_limit_wait(gh: Github, min_remaining: int = 100):
    """Pause if API rate limit is running low."""
    rate = gh.get_rate_limit().rate
    logger.info(f"GitHub API rate limit: {rate.remaining}/{rate.limit}")
    if rate.remaining < min_remaining:
        reset_time = rate.reset.timestamp() - time.time()
        wait = max(reset_time + 5, 0)
        logger.warning(f"Rate limit low — waiting {wait:.0f}s")
        time.sleep(wait)


# ── Complexity estimation ────────────────────────────────────────────────────

def estimate_complexity(diff: str) -> int:
    if not diff:
        return 0
    keywords = ["if ", "elif ", "else:", "for ", "while ", "case ", " && ", " || ", "except", "catch"]
    return sum(
        line.count(kw)
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
        for kw in keywords
    )


# ── PyDriller: mine commits from local clone ────────────────────────────────

def mine_commits(repo_path: str, since: datetime = None, to: datetime = None) -> list[dict]:
    logger.info(f"Mining commits from {repo_path}")
    results = []

    kwargs = {}
    if since:
        kwargs["since"] = since
    if to:
        kwargs["to"] = to

    for commit in Repository(repo_path, **kwargs).traverse_commits():
        for mod in commit.modified_files:
            if mod.filename and mod.filename.endswith(".lock"):
                continue
            results.append({
                "sha": commit.hash,
                "author_id": commit.author.email,
                "filename": mod.filename,
                "additions": mod.added_lines,
                "deletions": mod.deleted_lines,
                "complexity": estimate_complexity(mod.diff),
                "committed_at": commit.committer_date.astimezone(timezone.utc).replace(tzinfo=None),
            })

    logger.info(f"Mined {len(results)} file changes from {repo_path}")
    return results


# ── GitHub API: PRs, reviews, CI, deployments ───────────────────────────────

def fetch_pull_requests(gh: Github, repo_name: str) -> list[dict]:
    rate_limit_wait(gh)
    repo = gh.get_repo(repo_name)
    prs = []

    for pr in repo.get_pulls(state="all", sort="updated", direction="desc"):
        rate_limit_wait(gh, min_remaining=50)
        prs.append({
            "pr_number": pr.number,
            "repo": repo_name,
            "title": pr.title,
            "author_id": pr.user.email if pr.user else None,
            "state": pr.state,
            "merged": pr.merged,
            "opened_at": pr.created_at,
            "merged_at": pr.merged_at,
            "closed_at": pr.closed_at,
        })

    logger.info(f"Fetched {len(prs)} PRs from {repo_name}")
    return prs


def fetch_pr_reviews(gh: Github, repo_name: str) -> list[dict]:
    rate_limit_wait(gh)
    repo = gh.get_repo(repo_name)
    reviews = []

    for pr in repo.get_pulls(state="all"):
        rate_limit_wait(gh, min_remaining=50)
        for review in pr.get_reviews():
            reviews.append({
                "pr_number": pr.number,
                "repo": repo_name,
                "reviewer_id": review.user.email if review.user else None,
                "state": review.state,
                "submitted_at": review.submitted_at,
            })

    logger.info(f"Fetched {len(reviews)} PR reviews from {repo_name}")
    return reviews


def fetch_check_runs(gh: Github, repo_name: str) -> list[dict]:
    rate_limit_wait(gh)
    repo = gh.get_repo(repo_name)
    check_runs = []

    for commit in repo.get_commits()[:50]:
        rate_limit_wait(gh, min_remaining=50)
        try:
            for run in commit.get_check_runs():
                check_runs.append({
                    "sha": commit.sha,
                    "name": run.name,
                    "status": run.status,
                    "conclusion": run.conclusion,
                    "started_at": run.started_at,
                    "completed_at": run.completed_at,
                })
        except GithubException as e:
            logger.warning(f"Could not fetch check runs for {commit.sha}: {e}")

    logger.info(f"Fetched {len(check_runs)} CI check runs")
    return check_runs


def fetch_deployments(gh: Github, repo_name: str) -> list[dict]:
    rate_limit_wait(gh)
    repo = gh.get_repo(repo_name)
    deployments = []

    for dep in repo.get_deployments():
        rate_limit_wait(gh, min_remaining=50)
        statuses = list(dep.get_statuses())
        latest_status = statuses[0].state if statuses else None
        deployments.append({
            "sha": dep.sha,
            "environment": dep.environment,
            "deployer_id": dep.creator.email if dep.creator else None,
            "status": latest_status,
            "deployed_at": dep.created_at,
        })

    logger.info(f"Fetched {len(deployments)} deployments")
    return deployments


# ── DB Insert helpers ────────────────────────────────────────────────────────

async def save_file_changes(db: AsyncSession, changes: list[dict]):
    for c in changes:
        await db.execute(text("""
            INSERT INTO git_file_change
                (id, sha, author_id, filename, additions, deletions, complexity, committed_at)
            VALUES
                (gen_random_uuid(), :sha, :author_id, :filename, :additions, :deletions, :complexity, :committed_at)
            ON CONFLICT DO NOTHING
        """), c)
    await db.commit()
    logger.info(f"Saved {len(changes)} file changes to DB")


async def save_pull_requests(db: AsyncSession, prs: list[dict]):
    for pr in prs:
        await db.execute(text("""
            INSERT INTO pull_request
                (id, pr_number, repo, title, author_id, state, merged, opened_at, merged_at, closed_at)
            VALUES
                (gen_random_uuid(), :pr_number, :repo, :title, :author_id, :state, :merged, :opened_at, :merged_at, :closed_at)
            ON CONFLICT DO NOTHING
        """), pr)
    await db.commit()
    logger.info(f"Saved {len(prs)} PRs to DB")


async def save_check_runs(db: AsyncSession, runs: list[dict]):
    for run in runs:
        await db.execute(text("""
            INSERT INTO ci_check_run
                (id, sha, name, status, conclusion, started_at, completed_at)
            VALUES
                (gen_random_uuid(), :sha, :name, :status, :conclusion, :started_at, :completed_at)
            ON CONFLICT DO NOTHING
        """), run)
    await db.commit()
    logger.info(f"Saved {len(runs)} CI check runs to DB")


async def save_deployments(db: AsyncSession, deployments: list[dict]):
    for dep in deployments:
        await db.execute(text("""
            INSERT INTO deployment
                (id, sha, environment, deployer_id, status, deployed_at)
            VALUES
                (gen_random_uuid(), :sha, :environment, :deployer_id, :status, :deployed_at)
            ON CONFLICT DO NOTHING
        """), dep)
    await db.commit()
    logger.info(f"Saved {len(deployments)} deployments to DB")


# ── Main sync entry point ────────────────────────────────────────────────────

async def sync_github(
    db: AsyncSession,
    repo_name: str,
    local_clone_path: str,
    since: datetime = None,
    github_token: str = None,
):
    logger.info(f"Starting GitHub sync for {repo_name}")

    # Step 1 — Mine commits locally
    changes = mine_commits(local_clone_path, since=since)
    await save_file_changes(db, changes)

    # Step 2 — Fetch from API
    gh = get_github_client(token=github_token)

    prs = fetch_pull_requests(gh, repo_name)
    await save_pull_requests(db, prs)

    runs = fetch_check_runs(gh, repo_name)
    await save_check_runs(db, runs)

    deps = fetch_deployments(gh, repo_name)
    await save_deployments(db, deps)

    logger.info(f"GitHub sync complete for {repo_name}")