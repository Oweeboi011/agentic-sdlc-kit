"""Generate the Spec Kit preset's constitution template from `instructions/`, so rules have one source.

Run `python -m kit_sync.preset` after changing instructions; a test fails while the file is stale.
"""

from __future__ import annotations

from pathlib import Path

from kit_sync.kit import Doc, Kit, load_kit
from kit_sync.paths import KIT_ROOT

CONSTITUTION = Path("presets/spec-kit/templates/constitution-template.md")

_DELIVERY = [
    "**Spec first.** Features follow `specify` → `clarify` → `plan` → `tasks` → `analyze` → `implement`, "
    "with a human review after each step. A change with no new behaviour (fix, dependency, docs) may skip "
    "the spec; its PR says why.",
    "**Traceable.** Requirement IDs (FR-###, SC-###, NFR-###) appear in the backlog item, the PR body, "
    "test names and release notes.",
    "**Questions are decided, not guessed.** Each open `[NEEDS CLARIFICATION]` becomes a `needs-decision` "
    "backlog item for the spec's code owners; build waits for the decision.",
    "**Agents propose; humans decide.** Agents open draft PRs and proposals. "
    "Only humans merge, approve and deploy.",
    "**Gate before hand-off.** The project gate in `AGENTS.md` passes before a PR is marked ready.",
]
_GOVERNANCE = (
    "These rules come from the agentic SDLC kit (`instructions/`). Change them in the kit, then upgrade "
    "the kit; add project-specific principles as extra sections here. Amendments are reviewed by the code "
    "owners and recorded with a new version and date below."
)
_FOOTER = (
    "**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE] | "
    "**Last Amended**: [LAST_AMENDED_DATE]\n"
)


def _section(doc: Doc) -> str:
    title, _, rules = doc.body.strip().partition("\n")
    scope = f"Applies to `{doc.meta['applyTo']}`"
    if doc.meta.get("stack"):
        scope += f" (stack: {', '.join(doc.meta['stack'])}; drop this section if the project does not use it)"
    return f"### {title.removeprefix('# ').strip()}\n\n{scope}.\n\n{rules.strip()}\n"


def constitution(kit: Kit) -> str:
    general = [d for d in kit.instructions.values() if d.meta["applyTo"] == "**"]
    scoped = [d for d in kit.instructions.values() if d.meta["applyTo"] != "**"]
    parts = [
        "# [PROJECT_NAME] Constitution\n",
        "<!-- Generated from agentic-sdlc-kit instructions/ by `python -m kit_sync.preset`. -->\n",
        "## Core Principles\n",
        *[_section(d) for d in general],
        "## Engineering Standards\n",
        *[_section(d) for d in scoped],
        "## Delivery Rules\n",
        "".join(f"- {rule}\n" for rule in _DELIVERY),
        "## Governance\n",
        f"{_GOVERNANCE}\n",
        "[GOVERNANCE_RULES]\n",
        _FOOTER,
    ]
    return "\n".join(parts)


def main() -> None:
    (KIT_ROOT / CONSTITUTION).write_text(constitution(load_kit(KIT_ROOT)), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
