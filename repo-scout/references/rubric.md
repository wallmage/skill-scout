# Judging Rubric

Score each dimension from 1–5, but derive the verdict from gating conditions rather than an average. Compatibility or licensing can block an INSTALL; security enters a report only on clear evidence of deliberate malice, and the user can override any verdict. "Target" means whatever was linked — a skill pack, a developer tool, or a full application.

The scores and axis names are internal reasoning only. No numeric score, axis name, or rubric vocabulary ever appears in anything shown to the user — the visible report speaks plain everyday language, and detailed findings surface only in the deep-dive notes when the user asks for them.

## 1. Substance

Does the target give the user a capability they do not already have without it? The test is real implementation versus thin wrapper.

- **5:** A working multi-stage mechanism — deterministic tools, reusable assets, state, error handling, and verification — that materially changes outcomes.
- **3:** A useful workflow with concrete details, but a strong prompt or a few lines of glue could reproduce much of it.
- **1:** A five-line wrapper around one API call, generic expert personas, or default model behavior restated at length — regardless of README length.

For a skill pack, the reading is unchanged: find the file behind the README's strongest claim, and remember that prose telling the model to perform the claimed feature is not an implementation. For a tool or application, trace that the claimed capability is actually built, not merely described.

## 2. Mechanism

- **5:** A traceable path from input to output with explicit state, handoffs, verification, and completion.
- **3:** Ordered steps without durable state or feedback.
- **1:** Independent prompts or functions with no designed interaction.

Trace one real run: for a skill, trigger to output; for a library, one public API call to its effect; for an application, one end-to-end request (input → orchestration → output).

## 3. Craft

Look for lean triggering metadata, progressive disclosure, concrete examples, deterministic scripts for mechanical work, explicit completion criteria, and honest “when not to use” guidance. Penalize bloated always-loaded descriptions, duplicated instructions, and dead scaffolding.

Craft penalties inform the score; they reach the visible report only when they change the user's experience — at most one or two material shortcomings, never cosmetic nitpicks or normal signs of an actively developed project.

## 4. Maintenance & honesty

Compare meaningful commit history, releases, issue handling, and documentation with the shipped files. Separate “not available” from “bad.” Do not invent maintenance claims when hosting metadata or history is unavailable.

Freshness is category-aware, and an abandonment red (SKIP trigger 5) requires both the threshold exceeded and at least one confirming signal — deprecated model names or dead APIs, unresolvable dependencies, a pile of unanswered “broken” issues, or the archived flag. The calendar alone never reds: a stale tool that still installs and works is 🟢 with a one-line “no longer maintained; works today” note.

| Category | Aging (note under 🟢) | Presumed dead (🔴 with confirmation) |
|---|---|---|
| AI/LLM-coupled: agent frameworks, model wrappers, prompt/skill packs | > 3 months | > 6 months |
| Third-party-service-coupled: bots, scrapers, unofficial API clients | > 6 months | > 12 months |
| OS/store-coupled: browser extensions, mobile/desktop apps | > 12 months | > 24 months |
| Self-contained local tools/libraries on stable interfaces | no calendar threshold | never by date alone — only via trigger 4 |

Mixed repos take the fastest-moving category they depend on. If hosting metadata and history are both unreachable, freshness is unverified: say so and never red on an unverified prior.

## 5. Safety

Security is not the product and gets no dedicated inspection time. The single tripwire, noticed in passing while reading for mechanism, is clear evidence of deliberate malice: hidden exfiltration or telemetry, secret theft unrelated to the stated task, decode-then-execute payloads, destructive commands with broad targets, or hidden reviewer manipulation. When it fires, it becomes the verdict's decisive reason; the user can still override.

Everything below that bar — unintended vulnerabilities, bad practices, hygiene observations, broad-but-plausible permissions — is never reported. It is noise to this audience and never affects the verdict.

## 6. Compatibility & dependencies

Identify supported agent platforms, runtime and operating-system constraints, package manifests, lockfiles, direct/build/optional dependencies, external services, and version conflicts. Distinguish declared compatibility from compatibility actually evidenced by files. A current-platform mismatch blocks INSTALL.

## 7. License

Find license files and manifest declarations; note conflicts between them. A missing or incompatible license blocks installation or extraction when copying the code would lack permission. Do not infer a license from repository visibility.

## 8. Installation permissions

Trace what adoption changes as ownership information: the user should know what lands on the machine and what it costs to keep. Beyond directories, global packages, hooks, context footprint, and persistence, weigh the full adoption cost — deployment complexity, required external services and API keys, infra footprint, and operational upkeep. This is a practical note, not a safety judgment. Unclear upstream install docs are themselves an ownership-cost finding: the effort a newcomer spends decoding how to run the target is part of what adoption costs.

## 9. Fit

Every report must make clear when the user would actually reach for this — the "Why you'd want it" bullets carry that answer, told from the experience standpoint. When reading (not marketing) reveals it, state how the target compares to the obvious alternative — and, when value is partial, the exact subset and path worth installing and what is excluded. Fit feeds the verdict sentences. A report that cannot tell a newcomer how to run the target has not finished the audit: the visible report must say what it is and give the one recommended way to run it on the user's machine — the full graphical experience whenever one exists.

## 10. Audit completeness

Record the exact revision and note in one line anything left unread or sampled rather than read — in the deep-dive notes, never in the visible report. Unread material lowers confidence in the scores it would have informed; it does not block a verdict.

## Verdict gates

The verdict is binary — 🟢 INSTALL or 🔴 SKIP, never a middle option, and it is mechanical: nothing outside the seven triggers below produces a red, and when none fires the verdict is green. There is no target ratio of green to red — never calibrate a verdict toward an expected distribution.

- 🟢 **INSTALL:** Substance is at least 4; the mechanism is real; the target matches the user's platform; dependencies and adoption cost are acceptable; license use is allowed; none of the seven SKIP triggers fires. Worth installing the tool, deploying the application, or adding the dependency. When only specific components pass every gate while the rest is filler, still INSTALL — with the reviewer-chosen scope and path named and the excluded remainder noted in one line. A lagging or broken individual install path is never a reason to withhold INSTALL: pick a working path. When the gates pass, commit to green without reluctance — no "green, but…" framing; doubts below a SKIP trigger become at most one ownership-cost line.
- 🔴 **SKIP:** Fires only when at least one of these seven is evidenced, and nothing else produces a red:
  1. **Fake** — headline claims have no implementing files; substance ≤ 2, claims unsupported.
  2. **Malicious or suspicious** — clear evidence of deliberate malice (see Safety), or the tool routes the user's secrets/data through the author's private server with no self-host alternative, or install artifacts cannot be matched to the visible source.
  3. **Hazardous to the user** — the core function carries documented personal risk (account bans, clear legal exposure). Name it plainly.
  4. **Broken as shipped** — does not run today regardless of age: unresolvable dependencies, dead endpoints, install steps referencing missing files.
  5. **Abandoned and obsolete** — the freshness trigger (see §4 for category thresholds and the both-conditions rule). The verdict line must say plainly the author has abandoned the project.
  6. **Unusable for this user** — no documented or evidenced path runs on the user's platform; the license forbids their use; or it is not installable software at all (research artifact, paper code, demo scaffold).
  7. **Superseded** — the author archived or deprecated it. Red, with the successor named as the alternative.

  Name a better alternative when possible.

The user can override any verdict. Give the reminder once, then assist with their decision.

## Strong signals

- Verification or self-checking that handles failure, not just the happy path
- Runnable parsers, validators, generators, templates, or a real multi-stage pipeline
- Coherent cross-component references and explicit state
- Specific thresholds and edge cases that reflect real iteration
- Narrow permissions, modest adoption cost, and an honest non-use section

## Warning signals

- Component count, stars, or grandiose comparisons used as the main value proposition
- The same template repeated with nouns swapped
- README features without implementing files
- A thin wrapper around one API call dressed up as a system
- Placeholder scripts or dead assets
- Viral presentation paired with thin bodies
- Missing license, unexplained lifecycle scripts, or undeclared persistence
