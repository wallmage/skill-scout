# Scout Report Template

Use this structure. Keep a single-skill report near one page and a large-pack report under two pages. Write in the user's language; preserve verdict icons, source paths, commit hashes, dependency names, and license identifiers.

---

# Scout Report: <repository>

**Verdict: 🟢 INSTALL | 🟡 CHERRY-PICK | 🔴 SKIP** — <one sentence naming the decisive reason>

> <Two or three lines: what it really is, its active ingredient or fatal weakness, and the action to take.>

## Source and audit coverage

- Source: `<URL or local path>`
- Revision: `<commit SHA, release, or “not available”>`
- Inspected: `<counts for skills, scripts/executables, docs, manifests, hooks/commands/agents>`
- Skipped or unavailable: `<symlinks, binaries, oversized files, submodules, history, issues, or “none”>`

If an executable or install-relevant item was not inspected, explain why the verdict is capped at 🔴 SKIP FOR NOW.

## What it actually is

One paragraph comparing the claim with the contents. Include honest scale and identify whether this is a system, a recipe, or a prompt collection.

## How it works — the mechanism

Trace one concrete invocation from trigger to output: state, handoffs, scripts, verification, and completion. Use a small diagram only when branches or loops make prose harder to follow.

## The active ingredients

For a pack, use:

| Skill/component | What it does | Why it materially changes the result |
|---|---|---|

For a single skill, name the one or two components that survive the removal test.

## The filler

Name duplicated, generic, decorative, or misleading components. If none exists, say so briefly.

## Compatibility and ownership

| Check | Evidence | Consequence |
|---|---|---|
| Platform/runtime | <declared and observed constraints> | <works, mismatch, or unverified> |
| Dependencies | <direct, build, optional, external services> | <cost and risk> |
| License | <file/expression or missing> | <allowed use or blocker> |
| Installation permissions | <global writes, privilege, hooks, persistence> | <what changes on the machine> |
| Maintenance | <history, releases, issues> | <healthy, stale, or unverified> |
| Context footprint | <descriptions and loaded content> | <trigger/cost impact> |

## Safety

- Behavior-like findings: `<file:line evidence and contextual judgment, or “none found in inspected files”>`
- Context-only mentions: `<relevant leads or “none”>`
- Coverage limits: `<anything static analysis could not inspect>`

Static review cannot prove safety. State only what was or was not found within the inspected revision and scope.

## 10-minute reading map

List 2–4 real paths in reading order; estimates must total about ten minutes.

1. `path/to/file` (4 min) — <what to notice>
2. `path/to/file` (3 min) — <what to notice>

Everything not listed is covered by the report.

## Worth stealing

Name 2–4 reusable design patterns. Omit only when there is genuinely nothing useful.

## Bottom line

State the concrete action. For CHERRY-PICK, name the exact subset and ask for approval before installation. For SKIP, name a better alternative or what evidence would change the verdict.
