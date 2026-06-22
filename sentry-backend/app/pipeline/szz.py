import logging
import subprocess
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)

FIX_KEYWORDS = ["fix", "bug", "patch", "hotfix", "resolve"]


def is_fix_commit(message: str) -> bool:
    """Heuristic: commit message contains a fix-related keyword."""
    msg = message.lower()
    return any(kw in msg for kw in FIX_KEYWORDS)


def run_git_blame(repo_path: str, sha: str, filename: str) -> list[dict]:
    """
    Run `git log -p` style blame on the parent of the fix commit to find
    which commit last touched the lines this fix changes (classic SZZ approach:
    blame the *pre-fix* version of the file at the lines the diff removes).
    """
    try:
        # Get the parent commit of the fix
        parent = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", f"{sha}^"],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        # Get the diff for this file in this commit to find changed line ranges
        diff_output = subprocess.run(
            ["git", "-C", repo_path, "show", sha, "--", filename],
            capture_output=True, text=True, check=True
        ).stdout

        # Find removed line numbers (lines starting with '-' in the old file)
        removed_lines = []
        old_line_num = 0
        for line in diff_output.splitlines():
            if line.startswith("@@"):
                # parse hunk header like "@@ -12,5 +12,7 @@"
                try:
                    old_start = line.split("-")[1].split(",")[0].split("+")[0].strip()
                    old_line_num = int(old_start)
                except (IndexError, ValueError):
                    continue
            elif line.startswith("-") and not line.startswith("---"):
                removed_lines.append(old_line_num)
                old_line_num += 1
            elif not line.startswith("+"):
                old_line_num += 1

        if not removed_lines:
            return []

        # Blame the parent version of the file at the removed line numbers
        results = []
        for line_no in removed_lines[:20]:  # cap to avoid excessive subprocess calls
            try:
                blame_out = subprocess.run(
                    ["git", "-C", repo_path, "blame", "-L", f"{line_no},{line_no}",
                     parent, "--", filename, "--porcelain"],
                    capture_output=True, text=True, check=True
                ).stdout
                first_line = blame_out.splitlines()[0] if blame_out else None
                if first_line:
                    bug_sha = first_line.split()[0]
                    results.append({"bug_sha": bug_sha, "line": line_no})
            except subprocess.CalledProcessError:
                continue

        return results

    except subprocess.CalledProcessError as e:
        logger.warning(f"git blame failed for {sha} / {filename}: {e}")
        return []


def get_commit_metadata(repo_path: str, sha: str) -> dict:
    """Get author email and commit date for a sha."""
    try:
        output = subprocess.run(
            ["git", "-C", repo_path, "show", "-s", "--format=%ae|%ci", sha],
            capture_output=True, text=True, check=True
        ).stdout.strip()
        author, date_str = output.split("|", 1)
        committed_at = datetime.strptime(date_str.strip()[:19], "%Y-%m-%d %H:%M:%S")
        return {"author": author, "committed_at": committed_at}
    except Exception as e:
        logger.warning(f"Could not get metadata for {sha}: {e}")
        return {"author": None, "committed_at": None}


async def run_szz_tracing(db: AsyncSession, repo_path: str, limit_commits: int = 100) -> dict:
    """
    F7 — SZZ tracing.
    For each recent commit whose message looks like a fix, trace each changed
    file back to the commit that last modified the now-removed lines
    (the bug-introducing commit).
    """
    logger.info(f"Starting SZZ tracing on {repo_path}")

    try:
        log_output = subprocess.run(
            ["git", "-C", repo_path, "log", f"-{limit_commits}",
             "--name-only", "--pretty=format:COMMIT|%H|%s"],
            capture_output=True, text=True, check=True
        ).stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"git log failed: {e}")
        return {"fix_commits_scanned": 0, "traces_found": 0}

    # Parse commits and their files
    commits = []
    current = None
    for line in log_output.splitlines():
        if line.startswith("COMMIT|"):
            if current:
                commits.append(current)
            _, sha, message = line.split("|", 2)
            current = {"sha": sha, "message": message, "files": []}
        elif line.strip() and current:
            current["files"].append(line.strip())
    if current:
        commits.append(current)

    fix_commits = [c for c in commits if is_fix_commit(c["message"])]
    logger.info(f"Found {len(fix_commits)} fix-like commits out of {len(commits)} scanned")

    traces_found = 0
    for commit in fix_commits:
        fix_meta = get_commit_metadata(repo_path, commit["sha"])
        for filename in commit["files"]:
            blame_results = run_git_blame(repo_path, commit["sha"], filename)
            for result in blame_results:
                bug_sha = result["bug_sha"]
                if bug_sha == commit["sha"] or bug_sha.startswith("0000000"):
                    continue  # skip self-blame or uncommitted

                bug_meta = get_commit_metadata(repo_path, bug_sha)

                await db.execute(text("""
                    INSERT INTO szz_trace
                        (id, fix_sha, bug_introducing_sha, filename,
                         fix_author_id, bug_author_id, fix_committed_at, bug_committed_at, created_at)
                    VALUES
                        (gen_random_uuid(), :fix_sha, :bug_sha, :filename,
                         :fix_author, :bug_author, :fix_ts, :bug_ts, NOW())
                """), {
                    "fix_sha": commit["sha"],
                    "bug_sha": bug_sha,
                    "filename": filename,
                    "fix_author": fix_meta["author"],
                    "bug_author": bug_meta["author"],
                    "fix_ts": fix_meta["committed_at"],
                    "bug_ts": bug_meta["committed_at"],
                })
                traces_found += 1

    await db.commit()
    logger.info(f"SZZ tracing complete: {traces_found} bug-introducing commits traced")

    return {
        "commits_scanned": len(commits),
        "fix_commits_found": len(fix_commits),
        "traces_found": traces_found,
    }
