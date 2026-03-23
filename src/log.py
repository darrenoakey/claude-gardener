import json
import time
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent.resolve() / "output"
DETAIL_LOG = OUTPUT_DIR / "detail.jsonl"
SUMMARY_LOG = OUTPUT_DIR / "summary.jsonl"


# ##################################################################
# append jsonl
# write a single json object as one line to a jsonl file
def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


# ##################################################################
# log skip
# record that a run was skipped and why
def log_skip(reason: str) -> None:
    record = {
        "timestamp": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "event": "skip",
        "reason": reason,
    }
    append_jsonl(DETAIL_LOG, record)


# ##################################################################
# log cycle start
# record the beginning of a gardening cycle
def log_cycle_start(changed_count: int, unchanged_count: int) -> None:
    record = {
        "timestamp": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "event": "cycle_start",
        "changed_files": changed_count,
        "unchanged_files": unchanged_count,
    }
    append_jsonl(DETAIL_LOG, record)


# ##################################################################
# log ai result
# record the full ai response text for detailed audit
def log_ai_result(result_text: str, model_used: str) -> None:
    record = {
        "timestamp": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "event": "ai_result",
        "model": model_used,
        "result_length": len(result_text),
        "result": result_text[:5000],
    }
    append_jsonl(DETAIL_LOG, record)


# ##################################################################
# log commit
# record a git commit made by the gardener
def log_commit(repo: str, message: str, pushed: bool) -> None:
    record = {
        "timestamp": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "event": "commit",
        "repo": repo,
        "message": message,
        "pushed": pushed,
    }
    append_jsonl(DETAIL_LOG, record)


# ##################################################################
# log no changes
# record that the ai reviewed files but made no changes
def log_no_changes() -> None:
    record = {
        "timestamp": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "event": "no_changes",
    }
    append_jsonl(DETAIL_LOG, record)


# ##################################################################
# log error
# record an error that occurred during a cycle
def log_error(error: str) -> None:
    record = {
        "timestamp": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "event": "error",
        "error": error,
    }
    append_jsonl(DETAIL_LOG, record)


# ##################################################################
# log summary
# write a one-line summary of a completed cycle to the summary log
def log_summary(changes_made: bool, repos_committed: list[str], repos_pushed: list[str], summary: str) -> None:
    record = {
        "timestamp": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "changes_made": changes_made,
        "repos_committed": repos_committed,
        "repos_pushed": repos_pushed,
        "summary": summary,
    }
    append_jsonl(SUMMARY_LOG, record)
