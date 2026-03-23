from pathlib import Path

from daz_agent_sdk import agent, Tier

CLAUDE_DIR = Path.home() / ".claude"

SYSTEM_PROMPT = """You are the Claude Configuration Gardener. You maintain and improve Claude Code configuration files at ~/.claude.

## Your Responsibilities
1. Move content from CLAUDE.md to the most specific skill where it's relevant
2. Eliminate duplication across files — each piece of information lives in exactly one place
3. Split files over 200 lines into logical sub-files with clear references
4. Tighten prose without changing meaning
5. Create new skills when content doesn't fit any existing skill
6. Absorb learned/*.md content into appropriate skills
7. CLAUDE.md should trend toward a high-level index with only truly universal rules

## Rules
- Do NOT change the meaning or intent of any advice
- Do NOT touch files under plugins/ or skills/.system/
- Put information in the MOST SPECIFIC place it's relevant to
- Domain-specific gotchas go in domain skills (FastAPI → python, Gio → golang, etc.)
- Generic programming advice that applies across languages may need a "programming" skill
- When creating a new skill, create the directory and SKILL.md with proper frontmatter:
  ---
  name: skill-name
  description: one-line description
  ---
- When splitting a file, ensure the main file instructs the reader to read sub-files
- A run with zero changes is perfectly fine — don't force changes
- Prefer small, focused improvements over sweeping restructures
- Each run should make at most a few targeted improvements
- If you read an unchanged file for context, that's fine, but focus edits on changed files unless you spot clear cross-file issues (duplication, misplaced content)

## What Belongs Where
- CLAUDE.md: Universal commandments (no mocks, no fabrication, DRY>KISS>YAGNI), skill index, truly cross-cutting rules
- Skill SKILL.md: Domain-specific standards, gotchas, patterns, examples for that domain
- learned/*.md: DEPRECATED — content should migrate into appropriate skills over time
- projects/*/memory/*.md: Per-project context — clean up stale entries, remove duplicates

## File Size Guideline
Files over 200 lines should be split. For skills, use sub-files:
- SKILL.md (main, under 200 lines, references sub-files)
- Sub-files named descriptively: GOTCHAS.md, EXAMPLES.md, SETUP.md, etc.
The main SKILL.md must contain a note like: "**If working with X**, read `sub-file.md` in this directory."
"""


# ##################################################################
# build prompt
# assemble the full prompt with manifest, changed files, and unchanged file list
def build_prompt(changed_files: dict[Path, str], unchanged_files: list[Path], manifest_text: str) -> str:
    sections = []
    sections.append(f"## Skill Scopes (Manifest)\n{manifest_text}")
    sections.append("## Changed Files (REVIEW THESE — full content follows)\n")
    for path, content in changed_files.items():
        relative = _relative_path(path)
        line_count = content.count("\n")
        sections.append(f"### {relative} ({line_count} lines)\n```\n{content}\n```\n")
    sections.append("## Unchanged Files (for reference — use Read tool if you need content)\n")
    for path in unchanged_files:
        relative = _relative_path(path)
        sections.append(f"- {relative}")
    sections.append("\n## Instructions")
    sections.append("Review the changed files above. Make improvements where warranted.")
    sections.append("If nothing needs changing, respond with 'No changes needed.' and make no edits.")
    sections.append("For any edits you make, explain your reasoning briefly.")
    return "\n".join(sections)


# ##################################################################
# relative path
# convert absolute path to a readable path relative to ~/.claude
def _relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(CLAUDE_DIR.resolve()))
    except ValueError:
        try:
            return str(path.relative_to(Path.home()))
        except ValueError:
            return str(path)


# ##################################################################
# review
# send context to ai and let it edit files using tools
async def review(prompt: str) -> tuple[str, str]:
    result = await agent.ask(
        prompt,
        system=SYSTEM_PROMPT,
        tools=["Read", "Write", "Edit", "Glob", "Grep"],
        max_turns=30,
        tier=Tier.HIGH,
        cwd=str(CLAUDE_DIR),
    )
    model_name = ""
    if result.model_used:
        model_name = result.model_used.qualified_name
    return result.text, model_name
