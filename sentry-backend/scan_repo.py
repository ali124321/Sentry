import asyncio
import sys
from app.core.database import AsyncSessionLocal
from app.services.scanners.complexity import scan_repo_complexity
from app.services.scanners.churn import scan_repo_churn

async def scan(repository_id: int, repo_path: str, commit_sha: str):
    async with AsyncSessionLocal() as db:
        print(f"Scanning complexity for repo {repository_id}...")
        count = await scan_repo_complexity(db, repository_id, commit_sha, repo_path)
        print(f"Scanned {count} files for complexity")

        print(f"Scanning churn for repo {repository_id}...")
        count = await scan_repo_churn(db, repository_id, commit_sha, repo_path)
        print(f"Scanned {count} files for churn")
        print("Done!")

if __name__ == "__main__":
    repo_id = int(sys.argv[1])
    repo_path = sys.argv[2]
    commit_sha = sys.argv[3]
    asyncio.run(scan(repo_id, repo_path, commit_sha))
