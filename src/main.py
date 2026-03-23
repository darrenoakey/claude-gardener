import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

import setproctitle

import git_ops
import log
import manifest
import scanner

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
DEFAULT_INTERVAL = 3600
DEBOUNCE_SECONDS = 300

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("gardener")


# ##################################################################
# parse args
# command line interface for the gardener daemon
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Claude Configuration Gardener")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Seconds between cycles")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--no-debounce", action="store_true", help="Skip debounce check")
    return parser.parse_args()


# ##################################################################
# ensure repos exist
# initialize git repos for files that don't have one yet
def ensure_repos_exist() -> None:
    claude_dir = Path.home() / ".claude"
    claude_gitignore = claude_dir / ".gitignore"
    if not git_ops.is_git_repo(claude_dir):
        logger.info("Initializing git repo at %s", claude_dir)
        _write_claude_gitignore(claude_gitignore)
        git_ops.init_repo(claude_dir)
    skills_dir = claude_dir / "skills"
    if skills_dir.exists():
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            if skill_dir.name.startswith("."):
                continue
            resolved = skill_dir.resolve()
            if not git_ops.is_git_repo(resolved):
                logger.info("Initializing git repo at %s", resolved)
                git_ops.init_repo(resolved)


# ##################################################################
# write claude gitignore
# create a gitignore for the root claude directory
def _write_claude_gitignore(path: Path) -> None:
    path.write_text(
        "# Whitelist approach — ignore everything, un-ignore what we track\n"
        "*\n"
        "!.gitignore\n"
        "!CLAUDE.md\n"
        "!learned/\n"
        "!learned/*.md\n"
    )


# ##################################################################
# run cycle
# execute one gardening cycle: scan, review, commit, push
async def run_cycle(skip_debounce: bool = False) -> None:
    files = scanner.discover_files()
    if not files:
        logger.info("No files in scope")
        log.log_skip("no_files")
        return
    if not skip_debounce and scanner.any_recently_modified(files, DEBOUNCE_SECONDS):
        logger.info("Files modified recently, debounce skip")
        log.log_skip("debounce")
        return
    ensure_repos_exist()
    repos = git_ops.discover_repos(files)
    all_ours = all(git_ops.last_commit_is_ours(repo) for repo in repos)
    changed, unchanged = scanner.partition_changed(files)
    if all_ours and not changed:
        logger.info("No changes since last gardener run, skipping")
        log.log_skip("no_changes_since_last_run")
        return
    for repo in repos:
        if git_ops.has_real_changes(repo):
            logger.info("Committing uncommitted work in %s", repo)
            git_ops.commit_uncommitted(repo)
    if not changed:
        changed, unchanged = scanner.partition_changed(files)
    if not changed:
        logger.info("No changed files to review")
        log.log_skip("no_changed_files")
        scanner.save_state(scanner.current_checksums(files))
        return
    changed_content = {}
    for f in changed:
        try:
            changed_content[f] = f.read_text()
        except OSError as err:
            logger.warning("Cannot read %s: %s", f, err)
    if not changed_content:
        log.log_skip("unreadable_files")
        return
    logger.info("Reviewing %d changed files (%d unchanged)", len(changed_content), len(unchanged))
    log.log_cycle_start(len(changed_content), len(unchanged))
    mfst = manifest.load_manifest()
    manifest_text = manifest.format_for_prompt(mfst)
    from reviewer import build_prompt, review
    prompt = build_prompt(changed_content, unchanged, manifest_text)
    try:
        result_text, model_used = await review(prompt)
    except Exception as err:
        logger.error("AI review failed: %s", err)
        log.log_error(str(err))
        return
    log.log_ai_result(result_text, model_used)
    repos_committed = []
    repos_pushed = []
    for repo in repos:
        if git_ops.has_changes_since_commit(repo):
            summary = _extract_summary(result_text)
            committed = git_ops.commit_gardener(repo, summary)
            if committed:
                repos_committed.append(str(repo))
                logger.info("Committed changes in %s", repo)
                log.log_commit(str(repo), summary, False)
                if git_ops.has_remote(repo):
                    pushed = git_ops.push(repo)
                    if pushed:
                        repos_pushed.append(str(repo))
                        logger.info("Pushed %s", repo)
    if repos_committed:
        log.log_summary(True, repos_committed, repos_pushed, _extract_summary(result_text))
    else:
        logger.info("AI reviewed but made no changes")
        log.log_no_changes()
        log.log_summary(False, [], [], "no changes needed")
    scanner.save_state(scanner.current_checksums(files))
    manifest.save_manifest(mfst)


# ##################################################################
# extract summary
# pull a short summary from the ai result text for commit messages
def _extract_summary(result_text: str) -> str:
    first_line = result_text.strip().split("\n")[0] if result_text.strip() else "maintenance"
    if len(first_line) > 72:
        first_line = first_line[:69] + "..."
    return first_line


# ##################################################################
# main
# daemon entry point: run cycles on an interval
def main() -> int:
    setproctitle.setproctitle("claude-gardener")
    args = parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    logger.info("Claude Gardener starting (interval=%ds, once=%s)", args.interval, args.once)
    while True:
        try:
            asyncio.run(run_cycle(skip_debounce=args.no_debounce))
        except Exception as err:
            logger.exception("Cycle failed: %s", err)
            log.log_error(str(err))
        if args.once:
            break
        logger.info("Sleeping %ds until next cycle", args.interval)
        time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
