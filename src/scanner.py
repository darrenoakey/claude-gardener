import hashlib
import json
import time
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
STATE_FILE = Path(__file__).parent.parent.resolve() / "local" / "state.json"
DEBOUNCE_SECONDS = 300
GARDENER_COMMIT_PREFIX = "[gardener]"

EXCLUDED_SKILL_DIRS = {".system", ".DS_Store"}

EXCLUDED_TOP_LEVEL = {
    "agents", "backups", "cache", "chrome", "debug", "file-history",
    "hooks", "paste-cache", "plans", "plugins", "session-env", "sessions",
    "shell-snapshots", "statsig", "tasks", "telemetry", "todos",
    "usage-data", ".mcp.json", "settings.json", "settings.local.json",
    "keybindings.json", ".DS_Store",
}


# ##################################################################
# file checksum
# compute sha256 of file content for change detection
def file_checksum(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except (OSError, PermissionError):
        return ""


# ##################################################################
# load state
# read last-run state from disk, return empty dict if missing
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


# ##################################################################
# save state
# persist current checksums and timestamp for next run comparison
def save_state(checksums: dict[str, str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "last_run": time.time(),
        "checksums": checksums,
    }
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ##################################################################
# discover files
# find all in-scope markdown files across claude config and skills
def discover_files() -> list[Path]:
    files = []
    claude_md = CLAUDE_DIR / "CLAUDE.md"
    if claude_md.exists():
        files.append(claude_md.resolve())
    learned_dir = CLAUDE_DIR / "learned"
    if learned_dir.is_dir():
        for f in sorted(learned_dir.glob("*.md")):
            files.append(f.resolve())
    skills_dir = CLAUDE_DIR / "skills"
    if skills_dir.exists():
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            if skill_dir.name in EXCLUDED_SKILL_DIRS:
                continue
            if skill_dir.name.startswith("."):
                continue
            for md in sorted(skill_dir.rglob("*.md")):
                if md.name == "README.md":
                    continue
                if ".pytest_cache" in str(md):
                    continue
                files.append(md.resolve())
    memory_dir = CLAUDE_DIR / "projects"
    if memory_dir.is_dir():
        for mem_file in sorted(memory_dir.rglob("memory/*.md")):
            files.append(mem_file.resolve())
    return files


# ##################################################################
# partition changed
# split files into changed and unchanged based on stored checksums
def partition_changed(files: list[Path]) -> tuple[list[Path], list[Path]]:
    state = load_state()
    old_checksums = state.get("checksums", {})
    changed = []
    unchanged = []
    for f in files:
        current = file_checksum(f)
        stored = old_checksums.get(str(f), "")
        if current != stored:
            changed.append(f)
        else:
            unchanged.append(f)
    return changed, unchanged


# ##################################################################
# current checksums
# compute checksums for all discovered files
def current_checksums(files: list[Path]) -> dict[str, str]:
    return {str(f): file_checksum(f) for f in files}


# ##################################################################
# any recently modified
# true if any in-scope file was modified in the last n seconds
def any_recently_modified(files: list[Path], seconds: int = DEBOUNCE_SECONDS) -> bool:
    cutoff = time.time() - seconds
    for f in files:
        try:
            if f.stat().st_mtime > cutoff:
                return True
        except OSError:
            continue
    return False
