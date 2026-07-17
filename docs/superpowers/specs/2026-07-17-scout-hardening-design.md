# Skill Scout Hardening Design

## Goal

Turn `skill-scout` from a useful prompt plus a lightweight grep script into a reliable, read-only pre-install audit workflow whose claims match its implementation.

## Constraints

- Keep the shipped skill and all repository documentation in English.
- Keep the inventory tool dependency-free and compatible with Python 3.9+.
- Never execute code from the target repository.
- Preserve a single-script distribution.
- Treat static analysis as evidence, not proof of safety.
- Apply the N-1 subagent rule dynamically from models the current platform actually exposes. Examples explain the rule; they are not a model registry.

## Scanner architecture

`inventory.py` will separate collection from rendering:

1. `scan_repository(root)` safely traverses the target and returns an `Inventory` object.
2. Small helpers classify files, parse known manifests, and detect behavior-like patterns.
3. `render_inventory(inventory)` produces the human-readable report used by agents.

This keeps the CLI simple while making behavior directly testable.

## Safe traversal

- Use `lstat`/`O_NOFOLLOW` where available and never open symbolic links.
- Verify every opened path remains inside the scanned root.
- Record skipped symlinks, binaries, oversized files, and read errors.
- Cap text reads at 2 MiB per file.
- Do not recurse into generated, dependency, VCS, or cache directories.

## Inventory coverage

The scanner will report:

- Every `SKILL.md`, documentation file, and text footprint.
- Known script extensions, shebang scripts, and files with executable permission.
- Files under `hooks/`, `commands/`, and `agents/`, plus common agent/plugin metadata.
- Package and plugin manifests.
- Declared dependencies from common JSON, TOML, requirements, and Go manifests.
- License files and declared license metadata.
- Declared runtime/platform constraints and evidence-based platform hints.
- Installer files and lines requesting elevated privileges, global installs, persistence, or writes outside the repository.
- Full audit coverage: files inspected and every file skipped.

Compatibility and dependency output remains descriptive. The scanner does not resolve packages, query vulnerability databases, or claim that a platform was tested.

## Finding quality

Findings will be split into:

- **Behavior-like findings:** syntax that appears to perform a network call, read credentials, execute a shell, install persistence, decode a payload, or make a destructive change.
- **Context-only mentions:** relevant words in prose that deserve review but do not themselves perform an action.

The report must never call a repository “clean.” It states what was inspected, what was skipped, and whether suspicious behavior was found in that scope.

## Skill workflow

The inspection phase never installs or executes target code. After the verdict:

- `INSTALL`: return to the authorized host installation workflow.
- `CHERRY-PICK`: name the subset and ask the user to approve the changed scope before installation.
- `SKIP`: stop; a user may install manually after a quality-only rejection, but the agent does not override a material safety rejection.

The short frontmatter description contains triggers only. Detailed workflow, response language, and N-1 behavior stay in the body.

## N-1 subagents

For large packs, query the current harness for available model tiers and select exactly the next lower tier. Do not infer or invent a model name from examples. If the platform cannot expose or select a lower tier, run sequentially and disclose that limitation. The main model reviews all security-sensitive findings and owns the verdict.

## Tests and release

Use only `unittest` and temporary directories. Cover symlink refusal, extensionless executables, exact line counts, size/binary limits, integration directories, manifests, dependencies, licenses, compatibility hints, installation permissions, and finding separation. Rebuild `skill-scout.skill` from the verified source files and test the archive before pushing.
