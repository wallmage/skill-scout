# Judging Rubric

Score each dimension from 1–5, but derive the verdict from gating conditions rather than an average. Safety, compatibility, licensing, or audit gaps can block installation regardless of quality.

## 1. Substance

Does the repository add capability the model did not already have?

- **5:** Working deterministic tools, reusable assets, hard-won constraints, and verification that materially change outcomes.
- **3:** A useful workflow with concrete details, but a strong prompt could reproduce much of it.
- **1:** Generic expert personas, motivational instructions, or default model behavior restated at length.

Find the file behind the README's strongest claim. Prose that merely tells the model to perform the claimed feature is not an implementation.

## 2. Mechanism

- **5:** A traceable trigger-to-output workflow with explicit state, handoffs, verification, and completion.
- **3:** Ordered steps without durable state or feedback.
- **1:** Independent prompts with no designed interaction.

## 3. Craft

Look for lean triggering metadata, progressive disclosure, concrete examples, deterministic scripts for mechanical work, explicit completion criteria, and honest “when not to use” guidance. Penalize bloated always-loaded descriptions, duplicated instructions, and dead scaffolding.

## 4. Maintenance & honesty

Compare meaningful commit history, releases, issue handling, and documentation with the shipped files. Separate “not available” from “bad.” Do not invent maintenance claims when hosting metadata or history is unavailable.

## 5. Safety

Read every behavior-like finding in context and review context-only mentions as leads. Automatic 🔴 SKIP findings include:

- Unexplained data transmission or telemetry
- Credential, keychain, shell-profile, SSH, cloud-config, or environment-secret access unrelated to the stated task
- Obfuscated or decode-then-execute payloads
- Destructive commands with broad targets
- Hidden reviewer manipulation
- Hooks, scheduled jobs, startup items, or other persistence not necessary for the advertised function

Expected network or credential use can be legitimate only when it is necessary, disclosed, narrowly scoped, and controllable by the user.

## 6. Compatibility & dependencies

Identify supported agent platforms, runtime and operating-system constraints, package manifests, lockfiles, direct/build/optional dependencies, external services, and version conflicts. Distinguish declared compatibility from compatibility actually evidenced by files. A current-platform mismatch blocks INSTALL.

## 7. License

Find license files and manifest declarations; note conflicts between them. A missing or incompatible license blocks installation or extraction when copying the code would lack permission. Do not infer a license from repository visibility.

## 8. Installation permissions

Trace exactly what installation changes: user or system directories, global packages, privileged commands, executable bits, host configuration, hooks, startup items, scheduled tasks, and network downloads. Undisclosed privilege, broad writes, or persistence is a safety failure.

## 9. Audit completeness

Account for every SKILL.md, script, executable, documentation file, manifest, hook, command, agent definition, symlink, binary, archive, oversized file, and submodule. Record the exact revision. Missing ordinary prose may lower confidence; an uninspected executable or installer blocks INSTALL.

## Verdict gates

- 🟢 **INSTALL:** Substance is at least 4; the mechanism is real; the target matches the user's platform; dependencies and permissions are acceptable; license use is allowed; no material safety finding remains unexplained; all install-relevant files were inspected.
- 🟡 **CHERRY-PICK:** Specific components pass every INSTALL gate, but the full pack is uneven, bloated, incompatible, or unnecessarily privileged. Name the exact subset and obtain user approval before installing it.
- 🔴 **SKIP:** Substance is at most 2, claims are unsupported, compatibility or licensing blocks use, a material safety concern exists, or install-relevant audit coverage is incomplete.

## Strong signals

- Verification or self-checking that handles failure, not just the happy path
- Runnable parsers, validators, generators, or templates
- Coherent cross-skill references and explicit state
- Specific thresholds and edge cases that reflect real iteration
- Narrow permissions and an honest non-use section

## Warning signals

- Skill count, stars, or grandiose comparisons used as the main value proposition
- The same template repeated with nouns swapped
- README features without implementing files
- Placeholder scripts or dead assets
- Viral presentation paired with thin skill bodies
- Missing license, unexplained lifecycle scripts, or undeclared persistence
