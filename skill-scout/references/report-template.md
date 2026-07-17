# Scout Report Template

Use this exact structure. Length discipline: a single-skill repo → ~1 page; a 50-skill pack → 2 pages max. The report exists so the user does NOT have to read the repo — every sentence must earn its place.

Write the whole report in the language the user asked in (translate the section headings too); keep verdict icons and file paths unchanged. In pre-install-gate mode with a 🔴 SKIP verdict, the Bottom line must open with an unmistakable "do not install this" and the reasons, not a soft suggestion.

---

# Scout Report: <repo name>

**Verdict: 🟢 INSTALL | 🟡 CHERRY-PICK | 🔴 SKIP** — <one sentence: the decisive reason>

> <2-3 line TL;DR: what it actually is, the one thing that makes it work (or fail), and what to do about it. A reader who stops here should still make the right call.>

## What it actually is
One short paragraph: the repo's real identity, which may differ from its marketing. Include honest scale ("14 skills, ~4,000 lines, 3 working scripts") and how the claim compares to the contents.

## How it works — the mechanism
The heart of the report. Explain the machine the way a CTO explains architecture to a CEO: the workflow from trigger to output, where state lives, what loops or verifies, and how the pieces interact. Trace one concrete invocation end to end. Use a small diagram (mermaid or indented text) when the flow has branches or loops — skip it for linear flows.

## The active ingredients (the essential 20%)
For multi-skill packs, a table:

| Skill | What it does | Why it's essential |
|---|---|---|

Then one sentence on what the remaining skills are and why they didn't make the cut. For single skills, name the 1-2 components that pass the removal test (often a script or a checklist, not the prose).

## The filler
Be specific and brief: "skills X, Y, Z are the same template with nouns swapped", "the 12 'expert persona' files add nothing a plain prompt wouldn't". If there's genuinely no filler, say that — it's a strong green flag worth stating.

## 10-minute reading map
For the curious user who wants to learn from the source. An ordered curriculum, not a file list — 2-4 real paths from the repo, minutes summing to ~10, each with what to notice:

1. `path/to/file.md` (4 min) — <what to notice while reading>
2. `path/to/script.py` (3 min) — <what to notice>

Everything not listed here is covered by this report; say so explicitly.

## Safety
One line if clean ("Scanned scripts and hooks; no network calls, credential access, or persistence — clean"). If anything was flagged, quote the exact line with its file path and give your read on whether it's benign.

## Worth stealing
2-4 design patterns the author used that the user could apply to their own skills — this is the learning payoff, and it applies even to SKIP-rated repos (a failed repo often teaches one good trick). Skip the section only if there is truly nothing.

## Bottom line
Restate the verdict as a concrete action: "Install it, start with skill X on a real task", "Extract only `foo/` and `bar/`, ignore the rest", or "Skip; if you want this capability, <the better alternative>."
