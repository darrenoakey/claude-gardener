import subprocess
import time
from pathlib import Path

GARDENER_PREFIX = "[gardener]"
PRE_GARDENER_PREFIX = "[pre-gardener]"


# ##################################################################
# run git
# execute a git command in a given directory and return stdout
def run_git(repo: Path, *args: str, check: bool = True, timeout: int = 60) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo)] + list(args),
        capture_output=True, text=True, timeout=timeout,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}: {result.stderr.strip()}")
    return result.stdout.strip()


# ##################################################################
# is git repo
# check if a directory is a git repository
def is_git_repo(path: Path) -> bool:
    try:
        run_git(path, "rev-parse", "--git-dir")
        return True
    except (RuntimeError, subprocess.TimeoutExpired):
        return False


# ##################################################################
# init repo
# initialize a new git repository with an initial commit
def init_repo(path: Path) -> None:
    run_git(path, "init")
    gitignore = path / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("")
    run_git(path, "add", ".gitignore")
    run_git(path, "commit", "-m", f"{PRE_GARDENER_PREFIX} initial commit")


# ##################################################################
# has real changes
# check for actual content changes, filtering out pure symlink typechanges
def has_real_changes(repo: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True, text=True, timeout=60,
    )
    raw = result.stdout
    if not raw.strip():
        return False
    for line in raw.splitlines():
        if len(line) < 4:
            continue
        indicator = line[:2]
        filepath = line[3:].strip('"')
        full_path = repo / filepath
        if indicator.strip() == "T" and full_path.is_symlink():
            if _symlink_content_matches_head(repo, filepath, full_path):
                continue
        return True
    return False


# ##################################################################
# symlink content matches head
# check if a symlink's target content matches what git has committed
def _symlink_content_matches_head(repo: Path, git_path: str, full_path: Path) -> bool:
    committed_hash = run_git(repo, "rev-parse", f"HEAD:{git_path}", check=False)
    if not committed_hash:
        return False
    current_hash = run_git(repo, "hash-object", str(full_path.resolve()), check=False)
    return committed_hash == current_hash


# ##################################################################
# stage tracked files
# add files then fix any symlinks so git tracks content not link targets
def stage_tracked_files(repo: Path) -> None:
    run_git(repo, "add", "-A", timeout=120)
    _fix_symlinks_in_index(repo)


# ##################################################################
# fix symlinks in index
# replace symlink index entries with content blobs so git detects content changes
def _fix_symlinks_in_index(repo: Path) -> None:
    ls_output = run_git(repo, "ls-files", "-s", check=False)
    for line in ls_output.splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        mode = parts[0]
        filepath = parts[3]
        if mode != "120000":
            continue
        full_path = repo / filepath
        if not full_path.is_symlink():
            continue
        if not full_path.resolve().is_file():
            continue
        blob_hash = run_git(repo, "hash-object", "-w", str(full_path.resolve()))
        run_git(repo, "update-index", "--replace", "--cacheinfo", f"100644,{blob_hash},{filepath}")


# ##################################################################
# commit uncommitted
# stage and commit any outstanding changes as a pre-gardener snapshot
def commit_uncommitted(repo: Path) -> bool:
    if not has_real_changes(repo):
        return False
    stage_tracked_files(repo)
    status = run_git(repo, "status", "--porcelain", check=False)
    if not status:
        return False
    timestamp = time.strftime("%Y-%m-%d %H:%M")
    run_git(repo, "commit", "-m", f"{PRE_GARDENER_PREFIX} snapshot of uncommitted work ({timestamp})")
    return True


# ##################################################################
# last commit is ours
# check if the most recent commit was made by the gardener
def last_commit_is_ours(repo: Path) -> bool:
    try:
        msg = run_git(repo, "log", "-1", "--format=%s")
        return msg.startswith(GARDENER_PREFIX) or msg.startswith(PRE_GARDENER_PREFIX)
    except RuntimeError:
        return False


# ##################################################################
# has changes since commit
# true if there are real content changes since the last commit
def has_changes_since_commit(repo: Path) -> bool:
    return has_real_changes(repo)


# ##################################################################
# commit gardener changes
# stage and commit changes made by the gardener with a summary
def commit_gardener(repo: Path, summary: str) -> bool:
    if not has_real_changes(repo):
        return False
    stage_tracked_files(repo)
    status = run_git(repo, "status", "--porcelain", check=False)
    if not status:
        return False
    message = f"{GARDENER_PREFIX} {summary}"
    run_git(repo, "commit", "-m", message)
    return True


# ##################################################################
# has remote
# check if the repo has any remote configured
def has_remote(repo: Path) -> bool:
    try:
        remotes = run_git(repo, "remote")
        return len(remotes) > 0
    except RuntimeError:
        return False


# ##################################################################
# push
# push to the default remote if one exists
def push(repo: Path) -> bool:
    if not has_remote(repo):
        return False
    try:
        run_git(repo, "push", check=True, timeout=120)
        return True
    except RuntimeError:
        return False


# ##################################################################
# get diff summary
# return a short summary of changes in the working tree
def get_diff_summary(repo: Path) -> str:
    return run_git(repo, "diff", "--stat", "HEAD", check=False)


# ##################################################################
# find repo for file
# walk up from a file to find its enclosing git repository
def find_repo_for_file(file_path: Path) -> Path | None:
    current = file_path.parent
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


# ##################################################################
# discover repos
# find all unique git repositories that contain in-scope files
def discover_repos(files: list[Path]) -> dict[Path, list[Path]]:
    repos: dict[Path, list[Path]] = {}
    for f in files:
        repo = find_repo_for_file(f)
        if repo is not None:
            repos.setdefault(repo, []).append(f)
    return repos
