# Judging Rubric

Score each dimension from 1–5, but derive the verdict from gating conditions rather than an average. Compatibility or licensing can block an INSTALL; security enters a report only on clear evidence of deliberate malice, and the user can override any verdict. "Target" means whatever was linked — a skill pack, a developer tool, or a full application.

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

## 4. Maintenance & honesty

Compare meaningful commit history, releases, issue handling, and documentation with the shipped files. Separate “not available” from “bad.” Do not invent maintenance claims when hosting metadata or history is unavailable.

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

Every report must name the best-fit usage scenario(s): when would the user actually reach for this? When reading (not marketing) reveals it, state how the target compares to the obvious alternative — and, for CHERRY-PICK, the exact part worth taking and the condition. Fit feeds the verdict sentence. A report that cannot tell a newcomer how to run the target has not finished the audit: the "How to run it" section must answer what it is, where it runs, and the documented install paths — with the one recommended for the user's environment — before the detailed scoring.

## 10. Audit completeness

Record the exact revision and note in one line anything left unread or sampled rather than read. Unread material lowers confidence in the scores it would have informed; it does not block a verdict.

## Verdict gates

- 🟢 **INSTALL:** Substance is at least 4; the mechanism is real; the target matches the user's platform; dependencies and adoption cost are acceptable; license use is allowed; no clear evidence of deliberate malice. Worth installing the tool, deploying the application, or adding the dependency.
- 🟡 **CHERRY-PICK:** Specific components pass every INSTALL gate, but the whole is uneven, bloated, or incompatible. Name the exact part — a subset of a pack, a module, a usage scenario, or a design worth stealing — and the condition, then obtain user approval before installing it.
- 🔴 **SKIP:** Substance is at most 2, claims are unsupported, compatibility or licensing blocks use, or there is clear evidence of deliberate malice. Name a better alternative when possible.

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
