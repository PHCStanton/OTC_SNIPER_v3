# Research: Cline Skills Integration for `mattpocock/skills`

Date: 2026-05-12

## Summary

The `mattpocock/skills` repository is primarily aimed at Claude Code, but its core assets are portable because they use the common `SKILL.md` directory convention. Cline supports the same practical structure: one folder per skill containing a required `SKILL.md` file and optional supporting files.

## Sources Checked

- Local project memory: `.agent-memory/activeContext.md`, `.agent-memory/progress.md`
- Local global/project Cline folders:
  - `C:\Users\piete\.cline\`
  - `C:\v3\OTC_SNIPER\.cline\`
- Cline global state: `C:\Users\piete\.cline\data\globalState.json`
- Web/MCP search results for Cline skills paths and Cline 3.48+ skills support
- GitHub API tree for `https://github.com/mattpocock/skills`
- Raw repository files from `mattpocock/skills`, including README and selected `SKILL.md` files

> Note: The user requested Context7 MCP. A Context7 tool was not exposed in this session, so the assessment used the available Brave MCP/web search and GitHub API inspection.

## Cline Skill Locations

Recommended locations:

```text
Global:  C:\Users\piete\.cline\skills\<skill-name>\SKILL.md
Project: C:\v3\OTC_SNIPER\.cline\skills\<skill-name>\SKILL.md
```

Global skills apply across projects. Project skills are scoped to this repository and are better for repo-specific commands, paths, and development protocols.

## Repository Assessment

The Matt Pocock repository includes engineering, productivity, misc, personal, deprecated, and in-progress skills.

Recommended to integrate directly/adapt:

- `grill-me`
- `zoom-out`
- `write-a-skill`
- `diagnose` adapted as `diagnose-quflx`
- `tdd` adapted as `tdd-quflx`
- `handoff` adapted as `handoff-quflx`
- architecture review concept adapted as `architecture-review-quflx`

Recommended to avoid for now:

- `git-guardrails-claude-code` — Claude Code hook-specific.
- `setup-matt-pocock-skills` — assumes Matt's setup/config flow.
- `setup-pre-commit` — potentially invasive.
- `migrate-to-shoehorn` — not relevant to this project.
- `scaffold-exercises` — not relevant.
- `caveman` — conflicts with the project's clear review/reporting style.
- `personal/*`, `deprecated/*`, `in-progress/*` — unsuitable for stable project workflow.

## Integration Decision

Created a curated pack instead of copying the full repository.

Global skills:

```text
C:\Users\piete\.cline\skills\grill-me\SKILL.md
C:\Users\piete\.cline\skills\zoom-out\SKILL.md
C:\Users\piete\.cline\skills\write-a-skill\SKILL.md
```

Project skills:

```text
C:\v3\OTC_SNIPER\.cline\skills\diagnose-quflx\SKILL.md
C:\v3\OTC_SNIPER\.cline\skills\tdd-quflx\SKILL.md
C:\v3\OTC_SNIPER\.cline\skills\architecture-review-quflx\SKILL.md
C:\v3\OTC_SNIPER\.cline\skills\handoff-quflx\SKILL.md
```

## Rationale

- Global skills are generic and safe across projects.
- Project skills encode OTC_SNIPER-specific memory, review, testing, PowerShell, and `QuFLX-v2` conventions.
- Avoiding Claude Code hook/config skills prevents tool-specific assumptions from leaking into Cline.
- Keeping the pack small reduces activation noise and avoids conflicting with the existing `AGENTS.md`, `.clinerules/`, and Phase Review Protocol.

## Follow-Up

Restart or reload Cline / begin a new task if newly created skills do not appear immediately. If Cline exposes a Skills UI toggle, confirm these skills are enabled there.

For future projects, use the reusable installation playbook instead of this research/audit note:

- `Research/Install_Skills_Guide.md`
