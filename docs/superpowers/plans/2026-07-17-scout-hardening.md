# Skill Scout Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `skill-scout` deliver the complete, safe, low-noise pre-install audit promised by its documentation.

**Architecture:** Keep one standard-library Python CLI, but split its internals into safe collection, classification, manifest parsing, finding detection, and rendering functions. Drive every behavior through a returned `Inventory` structure so tests do not scrape incidental terminal formatting.

**Tech Stack:** Python 3.9+ standard library, `unittest`, Markdown, ZIP packaging.

## Global Constraints

- All repository and shipped skill content remains English.
- Target repository code is never executed.
- Symbolic links are never followed.
- Static analysis reports scope and uncertainty; it never proves safety.
- Subagents follow dynamic N-1 selection without invented model names.

---

### Task 1: Safe scanner contract

**Files:**
- Create: `tests/test_inventory.py`
- Modify: `skill-scout/scripts/inventory.py`

**Interfaces:**
- Produces: `scan_repository(root: str, max_file_bytes: int = 2 * 1024 * 1024) -> Inventory`
- Produces: `render_inventory(inventory: Inventory) -> str`

- [ ] Write failing tests proving symlinks are recorded but not read, extensionless executable files are listed, line counts are exact, and binary/oversized files are skipped with reasons.
- [ ] Run `python3 -m unittest discover -s tests -v`; verify failures refer to missing scanner interfaces or old behavior.
- [ ] Introduce immutable record types for files, findings, skipped paths, and the aggregate inventory.
- [ ] Implement bounded, no-follow reads and safe traversal.
- [ ] Run the test suite and verify Task 1 passes.

### Task 2: Complete repository inventory

**Files:**
- Modify: `tests/test_inventory.py`
- Modify: `skill-scout/scripts/inventory.py`

**Interfaces:**
- `Inventory.integration_paths`: entries under `hooks`, `commands`, and `agents`
- `Inventory.manifests`: detected package/plugin metadata files
- `Inventory.dependencies`: declared dependency name, version, group, and source manifest
- `Inventory.licenses`: license files and declared license expressions
- `Inventory.compatibility`: evidence-based platform/runtime constraints
- `Inventory.install_surfaces`: permission, persistence, global-install, and outside-repository write evidence

- [ ] Add failing fixtures for agent directories, executable assets, package manifests, requirements, license metadata, runtime constraints, and privileged install commands.
- [ ] Run the focused tests and confirm the old scanner omits them.
- [ ] Add classifiers and parsers for common JSON, TOML, requirements, Go, and plugin manifests, degrading to “manifest detected; manual review required” when parsing is unavailable.
- [ ] Render each promised section with source paths and evidence.
- [ ] Run all tests.

### Task 3: Reduce safety-scan noise

**Files:**
- Modify: `tests/test_inventory.py`
- Modify: `skill-scout/scripts/inventory.py`

**Interfaces:**
- `Finding.strength`: `behavior` or `context`
- `Finding.source_kind`: `executable` or `documentation`

- [ ] Add failing cases that distinguish executable network/credential behavior from prose such as “no network calls.”
- [ ] Replace broad keyword matching with action-shaped patterns plus a separate context-only pass.
- [ ] Print behavior-like findings before contextual mentions and include file/line evidence.
- [ ] Run all tests and self-scan the skill.

### Task 4: Align skill and public documentation

**Files:**
- Modify: `skill-scout/SKILL.md`
- Modify: `skill-scout/references/rubric.md`
- Modify: `skill-scout/references/report-template.md`
- Create: `skill-scout/agents/openai.yaml`
- Modify: `README.md`
- Modify: `INSTALL.md`
- Modify: `docs/index.html`

- [ ] Shorten frontmatter to concrete triggers.
- [ ] Make inspection and installation separate phases, requiring confirmation before a cherry-picked install.
- [ ] Document full audit coverage, compatibility/dependency/license/permission checks, and static-analysis limits.
- [ ] State dynamic N-1 behavior and keep model mappings explicitly illustrative.
- [ ] Remove definitive “clean” language from reports and public claims.
- [ ] Generate valid OpenAI UI metadata from the finished skill.

### Task 5: Package, validate, review, and publish

**Files:**
- Modify: `skill-scout.skill`

- [ ] Run `python3 -m unittest discover -s tests -v`.
- [ ] Run the official skill validator and validate `agents/openai.yaml`.
- [ ] Run the scanner against this repository and representative hostile fixtures.
- [ ] Rebuild the ZIP from the four required resources plus `agents/openai.yaml`.
- [ ] Run `unzip -t skill-scout.skill` and compare archive files with the source tree.
- [ ] Request an independent N-1 review; fix every critical or important finding.
- [ ] Re-run the full verification set, commit, and push the branch to GitHub.
