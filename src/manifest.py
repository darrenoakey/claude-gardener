import json
from pathlib import Path

MANIFEST_FILE = Path(__file__).parent.parent.resolve() / "local" / "manifest.json"
CLAUDE_DIR = Path.home() / ".claude"

DEFAULT_SCOPES = {
    "ai": "daz-agent-sdk: provider-agnostic programmatic AI integration, tier routing, fallback",
    "arbiter": "GPU inference job server on spark: vision, image gen, background removal, TTS, transcription",
    "auto": "macOS daemon process manager: start, stop, restart, monitor background services",
    "bdd": "Behavior-Driven Development for UI projects: Gherkin scenarios, Playwright, test hooks",
    "commit": "Git workflow: stage, commit, push, then run improve and compact",
    "discord": "Discord bot integration",
    "dotnet": ".NET/C# development standards, testing, co-located tests",
    "generate_image": "Image generation via flux/stable diffusion",
    "golang": "Go development standards, Gio UI, testing, idiomatic patterns",
    "improve": "Meta-skill for continuous improvement after commits",
    "integrity": "Integrity scanning",
    "ios-publish": "iOS App Store publishing: Capacitor, XcodeGen, code signing",
    "peon-ping-config": "Peon ping sound notification configuration",
    "peon-ping-log": "Peon trainer exercise rep logging",
    "peon-ping-toggle": "Peon ping sound toggle on/off",
    "peon-ping-use": "Peon ping voice pack selection",
    "publish": "GitHub publishing with auto-generated banner and README",
    "pypi": "Python package deployment to PyPI",
    "python": "Python development: FastAPI, SQLAlchemy, SQLite, Playwright, stdlib, PyObjC, ML, PySide6",
    "remote": "Remote machine control via multi-server orchestration",
    "screenshot": "Browser screenshot capture",
    "spark": "NVIDIA Grace Blackwell GPU workloads, CUDA, Sonic talking head",
    "web-driver": "Browser automation library",
    "website": "Python web server development: static files, cache-busting, HTML templating",
}


# ##################################################################
# load manifest
# read skill scope manifest from disk, return defaults if missing
def load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        try:
            return json.loads(MANIFEST_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"scopes": dict(DEFAULT_SCOPES)}


# ##################################################################
# save manifest
# persist the manifest to disk
def save_manifest(manifest: dict) -> None:
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2))


# ##################################################################
# format manifest for prompt
# render the manifest as a readable string for the AI prompt
def format_for_prompt(manifest: dict) -> str:
    lines = []
    scopes = manifest.get("scopes", {})
    for name, scope in sorted(scopes.items()):
        lines.append(f"- **{name}**: {scope}")
    return "\n".join(lines)


# ##################################################################
# update scope
# add or update a skill's scope description in the manifest
def update_scope(manifest: dict, skill_name: str, description: str) -> dict:
    manifest.setdefault("scopes", {})[skill_name] = description
    return manifest
