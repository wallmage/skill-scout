# Scout Report Template

Use this structure. Keep a single-target report near one page and a large-repository report under two pages. Write in the user's language; preserve verdict icons, source paths, commit hashes, content hashes, dependency names, and license identifiers.

The report contains no security commentary — no flaw lists, no hygiene notes, no vulnerability caveats. The single exception is clear evidence of deliberate malice, which becomes the verdict's decisive reason on line one.

---

# Scout Report: <repository>

**Verdict: 🟢 INSTALL | 🟡 CHERRY-PICK | 🔴 SKIP** — <one sentence naming the decisive reason>

> <Two or three lines: what it really is, its active ingredient or fatal weakness, and the action to take.>

## How to run it

Answer "how do I run this?" before the audit detail, written for a reader who does not know the tooling. Every report gets this section. No technology is treated as scary, privileged, or mandatory: each documented path is one honest peer line. Derive it from the repo's own install docs and files (verified paths, not marketing); describe, do not test-run. If the project's own docs are unclear, say so explicitly — that is report-worthy evidence about the project.

- **What kind of thing it is, in plain words** — one sentence naming the shape: a skill you copy into Claude Code/Codex; a CLI you install; a library for your code; a desktop app; or a self-hosted application you run as its own service (its own product with a web page you open in a browser, not something that lives inside another tool).
- **Where it runs** — supported platforms/hosts, stated concretely (macOS/Linux/Windows; arm64/x86_64). Distinguish "officially supported" from "evidenced by files."
- **The paths** — list *all* documented install paths as neutral peers, one line each: `<path> — needs <prereqs>; suits <who>`. Order them by what upstream documents as primary, then by simplicity — never by the reviewer's tooling preferences. Gloss a jargon term once, in one line, the first time a path uses it ("Docker — an app that runs the whole stack in an isolated box so you install nothing else"), then move on; give no single technology extended treatment.
  - **On your machine** — which documented path this user is closest to for the detected environment (§Detect the environment): what is already satisfied, what is missing, and the one-line command to get each missing piece with their detected package manager (`brew install …`, `apt install …`). "Closest" means fewest new installs and least new infrastructure. If probing was impossible (no shell), say so and leave the paths un-tailored.
- **What you must have first** — accounts and API keys required before anything works.

## Source and audit coverage

- Source: `<URL or local path>`
- Resolved from: `<input link → repository, or “input was the repository”>`
- Revision: `<commit SHA, release, or “not available”>`
- Local state: `<clean/dirty/not applicable>`
- Not read: `<one line — unread or sampled areas, or “nothing material”>`

## What it actually is

One paragraph comparing the claim with the contents. State the archetype in plain words ("a self-hosted research-agent application", "a prompt pack", "a CLI"), give honest scale, and identify whether this is a system, a recipe, or a prompt collection.

## How it works — the mechanism

Trace one concrete invocation from trigger to output: state, handoffs, scripts, verification, and completion. For an application this is one end-to-end run (input → orchestration → output); for a library, one public API call to its effect. Use a small diagram only when branches or loops make prose harder to follow.

## The active ingredients

For a pack or a multi-component target, use:

| Skill/component | What it does | Why it materially changes the result |
|---|---|---|

For a single-purpose target, name the one or two components or subsystems that survive the removal test.

## The filler

Name duplicated, generic, decorative, or misleading components. If none exists, say so briefly.

## Best fit

1–3 bullets: the key usage scenarios where this target earns its keep, and who should not bother.

- <Reach for it when …>
- <Skip it if …>

## Compatibility and ownership

| Check | Evidence | Consequence |
|---|---|---|
| Platform/runtime | <declared and observed constraints> | <works, mismatch, or unverified> |
| Dependencies | <direct, build, optional, external services> | <cost and risk> |
| License | <file/expression or missing> | <allowed use or blocker> |
| Install/deploy footprint | <global writes, privilege, hooks, persistence, deployment complexity, required keys/services, infra> | <what it costs to adopt and keep> |
| Maintenance | <history, releases, issues> | <healthy, stale, or unverified> |
| Context footprint | <descriptions and loaded content> | <trigger/cost impact> |

## 10-minute reading map

List 2–4 real paths in reading order; estimates must total about ten minutes. For an application, point at orchestration and config files rather than SKILL.mds.

1. `path/to/file` (4 min) — <what to notice>
2. `path/to/file` (3 min) — <what to notice>

Everything not listed is covered by the report.

## Worth stealing

Name 2–4 reusable design patterns. Omit only when there is genuinely nothing useful.

## Bottom line

State the concrete action. For CHERRY-PICK, name the exact subset and ask for approval before installation. For SKIP, name a better alternative or what evidence would change the verdict.

After a 🟢 verdict — or a 🟡 or overridden verdict the user has approved — close with one offer: whether you should install and set it up for them, naming the recommended **On your machine** path. Ask once; make no offer after an unapproved 🔴.
