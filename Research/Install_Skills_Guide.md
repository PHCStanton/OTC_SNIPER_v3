# Install Skills Guide for Cline

Purpose: give future agents a reusable, safe procedure for adding focused Cline skills to any project without blindly copying large skill repositories or weakening project-specific rules.

Last updated: 2026-05-12

## Quick Answer

Use the research note for historical context:

- `Research/research_cline_skills_integration_2026-05-12.md`

Use this guide as the reusable install playbook.

## What a Cline Skill Is

A Cline skill is a folder with a required `SKILL.md` file:

```text
skill-name/
  SKILL.md        required
  docs/           optional reference files
  scripts/        optional deterministic helpers
```

The `SKILL.md` must start with YAML frontmatter:

```md
---
name: skill-name
description: One sentence describing what the skill does. Use when specific trigger phrases or task contexts apply.
---
```

The `description` is critical because it tells Cline when the skill should be loaded.

## Install Locations

### Global Skills

Use global skills for behavior that should apply across all projects.

```text
Windows: C:\Users\<user>\.cline\skills\<skill-name>\SKILL.md
Generic: ~/.cline/skills/<skill-name>/SKILL.md
```

For this workstation:

```text
C:\Users\piete\.cline\skills\<skill-name>\SKILL.md
```

Good global candidates:

- clarification/interview skills
- generic architecture explanation skills
- generic skill-authoring skills
- generic handoff formats that do not mention one repo's paths

Avoid global skills that contain:

- project-specific commands
- project-specific file paths
- team/process rules that only apply to one repository
- tool-specific hooks for a different agent runtime

### Project Skills

Use project skills when a skill depends on that repository's architecture, commands, memory files, test suite, or workflow rules.

```text
<project-root>/.cline/skills/<skill-name>/SKILL.md
```

For OTC_SNIPER:

```text
C:\v3\OTC_SNIPER\.cline\skills\<skill-name>\SKILL.md
```

Good project-level candidates:

- repo-specific diagnosis workflow
- repo-specific TDD/test commands
- repo-specific architecture review protocol
- repo-specific handoff/memory update procedure
- deployment or environment workflows tied to one project

## Decision Tree

Before installing a skill, answer these questions in order.

### 1. Is the skill stable and maintained?

Install only from stable folders or reviewed local drafts.

Avoid by default:

- `deprecated/`
- `in-progress/`
- personal/private workflow skills
- scripts that modify system configuration without review

### 2. Is it generic or project-specific?

Choose **global** if the skill applies unchanged to multiple projects.

Choose **project-level** if it mentions:

- repo paths
- environment names
- test commands
- architecture modules
- team-specific review gates
- agent delegation conventions

### 3. Does it conflict with existing rules?

Check project instructions first:

- `AGENTS.md`
- `.clinerules/`
- `.agent-memory/`
- existing docs or workflow files

If a skill conflicts with these, adapt the skill or do not install it.

### 4. Does it require scripts?

Prefer instruction-only skills.

Only keep scripts if they are:

- deterministic
- easy to inspect
- safe by default
- non-destructive
- explicit about failures

Never install shell hooks from another tool, such as Claude Code hooks, without converting them to Cline-compatible behavior and getting user approval.

### 5. Will it increase or reduce activation noise?

Install fewer, sharper skills. A small focused set is better than dozens of overlapping skills.

## Recommended Install Workflow for Future Agents

### Phase 1 — Read Existing Context

For any project, inspect:

```text
AGENTS.md
.clinerules/
.agent-memory/
README.md
docs/ or Dev_Docs/
package.json / pyproject.toml / requirements files
existing tests
```

If a project has no memory/rules structure, ask the user whether skills should establish one.

### Phase 2 — Select Skills

Create a short recommendation table:

| Skill | Scope | Reason | Needs Adaptation? |
|---|---|---|---|
| `skill-name` | Global / Project | Why it helps | Yes / No |

Do not install everything from a third-party repository.

### Phase 3 — Adapt Skill Text

For every project-level skill, adapt:

- skill name, preferably with a project suffix, e.g. `diagnose-quflx`
- paths
- test commands
- terminal/shell conventions
- review and approval rules
- output format
- specialist/delegation language

Keep one responsibility per skill.

### Phase 4 — Create Files

Use this structure:

```text
.cline/skills/<skill-name>/SKILL.md
```

For global skills:

```text
C:\Users\piete\.cline\skills\<skill-name>\SKILL.md
```

### Phase 5 — Validate

Run a validation check that confirms every skill has frontmatter:

```powershell
$files = Get-ChildItem -Recurse -Filter SKILL.md .cline\skills
foreach ($f in $files) {
  $c = Get-Content -Raw -Path $f.FullName
  if ($c -notmatch '(?s)^---\s*\r?\nname:\s*[^\r\n]+\r?\ndescription:\s*[^\r\n]+\r?\n---') {
    throw "Invalid frontmatter $($f.FullName)"
  }
  Write-Output "OK $($f.FullName)"
}
```

For global skills on this workstation:

```powershell
$files = Get-ChildItem -Recurse -Filter SKILL.md C:\Users\piete\.cline\skills
foreach ($f in $files) {
  $c = Get-Content -Raw -Path $f.FullName
  if ($c -notmatch '(?s)^---\s*\r?\nname:\s*[^\r\n]+\r?\ndescription:\s*[^\r\n]+\r?\n---') {
    throw "Invalid frontmatter $($f.FullName)"
  }
  Write-Output "OK $($f.FullName)"
}
```

### Phase 6 — Reload Cline

If new skills do not appear immediately:

1. Start a new Cline task, or
2. Reload the VS Code window, or
3. Check Cline's skills UI/toggles if available.

## Template: Generic Skill

```md
---
name: skill-name
description: Describes exactly what this skill does. Use when the user asks for [specific trigger] or the task involves [specific context].
---

# Skill Name

## Purpose

One short paragraph.

## Workflow

1. Step one.
2. Step two.
3. Step three.

## Output Format

- **Summary**
- **Findings**
- **Recommended Next Step**

## Guardrails

- Do not conflict with project rules.
- Ask for clarification if required inputs are missing.
- Do not perform destructive operations without explicit approval.
```

## Template: Project-Specific Skill

```md
---
name: project-task-name
description: Performs [task] for [project]. Use when [specific triggers in this project].
---

# Project Task Name

## Mandatory Context

Read these files first:

- `AGENTS.md`
- `.agent-memory/activeContext.md`
- `.agent-memory/progress.md`
- relevant implementation plan

## Workflow

1. Confirm the exact domain area.
2. Inspect relevant files before changing anything.
3. Follow project-specific approval/review rules.
4. Run the narrowest relevant validation command.
5. Report results with paths and commands.

## Commands

```powershell
# project-specific validation command here
```

## Guardrails

- Respect project shell/environment rules.
- Do not bypass review gates.
- Preserve backward compatibility.
- Fail fast and report errors clearly.
```

## Applying This to `mattpocock/skills`

Recommended general/global candidates:

- `grill-me`
- `zoom-out`
- `write-a-skill`

Recommended project-adapted candidates:

- `diagnose`
- `tdd`
- `handoff`
- architecture review concepts

Avoid by default:

- Claude Code hook skills unless converted for Cline
- issue-tracker skills unless the project actually uses that issue tracker
- deprecated/in-progress/personal skills
- setup skills that assume another repository's conventions

## OTC_SNIPER Example

This repository installed:

Global:

```text
C:\Users\piete\.cline\skills\grill-me\SKILL.md
C:\Users\piete\.cline\skills\zoom-out\SKILL.md
C:\Users\piete\.cline\skills\write-a-skill\SKILL.md
```

Project:

```text
.cline/skills/diagnose-quflx/SKILL.md
.cline/skills/tdd-quflx/SKILL.md
.cline/skills/architecture-review-quflx/SKILL.md
.cline/skills/handoff-quflx/SKILL.md
```

The project skills were adapted to respect:

- `.agent-memory/`
- `.clinerules/`
- `Dev_Docs/`
- QuFLX-v2 conda commands
- PowerShell command syntax
- Phase Review Protocol
- specialist delegation conventions

## Final Rule

Do not treat skills as a bulk dependency. Treat them as workflow code: review, adapt, install narrowly, and verify.
