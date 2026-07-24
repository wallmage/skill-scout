from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "repo-scout"


class SkillContractTests(unittest.TestCase):
    def setUp(self):
        self.skill = (SKILL_DIR / "SKILL.md").read_text()
        self.report = (SKILL_DIR / "references" / "report-template.md").read_text()
        self.rubric = (SKILL_DIR / "references" / "rubric.md").read_text()

    def test_description_is_short_and_trigger_focused(self):
        frontmatter = re.match(r"\A---\n(.*?)\n---", self.skill, re.DOTALL)
        self.assertIsNotNone(frontmatter)
        description_match = re.search(
            r'^description:\s*["\']?(.*?)["\']?$',
            frontmatter.group(1),
            re.MULTILINE,
        )
        self.assertIsNotNone(description_match)
        description = description_match.group(1)
        self.assertTrue(description.startswith("Use when"))
        self.assertLessEqual(len(description), 500)
        for cue in (
            "is this worth installing?",
            "is this worth adopting?",
            "thoughts?",
            "repository URL",
            "comparison",
            "install this",
            "/plugin install",
            "curl ... | sh",
            "any Git host",
            "project website",
            "package-registry page",
        ):
            self.assertIn(cue, description)
        self.assertIn(
            "Always run Repo Scout before every skill or plugin installation",
            description,
        )
        for workflow_summary in (
            "evidence-based read-only audit",
            "INSTALL / CHERRY-PICK / SKIP verdict",
            "file:line evidence",
            "coverage ledger",
            "read every",
            "run the scanner",
            "verdict on the first line",
        ):
            self.assertNotIn(workflow_summary, description.lower())
        self.assertNotIn("Reply in", description)
        self.assertNotIn("clone it", description)

    def test_codex_install_paths_match_current_skill_discovery(self):
        install = (ROOT / "INSTALL.md").read_text()
        readme = (ROOT / "README.md").read_text()
        landing = (ROOT / "docs" / "index.html").read_text()

        for surface in (install, readme, landing):
            self.assertIn(".agents/skills", surface)
            self.assertNotIn(".codex/skills", surface)
        self.assertIn("<project>/.agents/skills/repo-scout/SKILL.md", install)

    def test_install_commands_are_repeatable(self):
        install = (ROOT / "INSTALL.md").read_text()
        readme = (ROOT / "README.md").read_text()
        landing = (ROOT / "docs" / "index.html").read_text()

        for destination in (
            "~/.claude/skills/repo-scout",
            "~/.agents/skills/repo-scout",
        ):
            parent = destination.rsplit("/", 1)[0]
            for surface in (install, readme, landing):
                self.assertIn(f"mkdir -p {parent}", surface)
                self.assertIn(f"rm -rf {destination}", surface)
                self.assertIn(f'mv "$install_stage" {destination}', surface)

        self.assertIn(
            "mkdir -p <project>/.agents/skills",
            install,
        )
        self.assertIn(
            "rm -rf <project>/.agents/skills/repo-scout",
            install,
        )
        for surface in (install, readme, landing):
            self.assertIn('install_stage="$(mktemp -d ', surface)
            self.assertNotRegex(
                surface,
                r"cp -R repo-scout(?:/repo-scout)?/\. "
                r"(?:~/|<project>/).*?/repo-scout/",
            )
        self.assertIn(
            """trap 'rm -rf "$install_stage"' 0 1 2 15""",
            install,
        )
        self.assertEqual(
            3,
            install.count(
                'git archive HEAD repo-scout | tar -x -C "$install_stage" '
                "--strip-components=1"
            ),
        )
        for surface in (readme, landing):
            self.assertIn('source_stage="$(mktemp -d ', surface)
            self.assertIn(
                """trap 'rm -rf "$source_stage" "$install_stage"' 0 1 2 15""",
                surface,
            )
        self.assertEqual(3, install.count("```bash\n(\nset -e"))
        self.assertEqual(4, readme.count("```bash\n(\nset -e"))
        self.assertEqual(4, landing.count("<pre><code>(\nset -e"))
        self.assertNotIn("```bash\nset -e", install)
        self.assertNotIn("```bash\nset -e", readme)
        self.assertNotIn("<pre><code>set -e", landing)

    def test_codex_quick_start_installs_and_updates_from_the_remote(self):
        readme = (ROOT / "README.md").read_text()
        codex_block = re.search(
            r"\*\*OpenAI Codex\*\*\n```bash\n(.*?)\n```",
            readme,
            re.DOTALL,
        )
        self.assertIsNotNone(codex_block)

        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            source = root / "source"
            remote = root / "remote.git"
            install_cwd = root / "install"
            fake_home = root / "home"
            source_skill = source / "repo-scout" / "SKILL.md"
            source_skill.parent.mkdir(parents=True)
            install_cwd.mkdir()
            fake_home.mkdir()

            self._run_git("init", "-b", "main", str(source), cwd=root)
            self._run_git(
                "-C",
                str(source),
                "config",
                "user.email",
                "tests@example.invalid",
                cwd=root,
            )
            self._run_git(
                "-C",
                str(source),
                "config",
                "user.name",
                "Repo Scout Tests",
                cwd=root,
            )
            source_skill.write_text("version 1\n")
            self._run_git("-C", str(source), "add", ".", cwd=root)
            self._run_git(
                "-C",
                str(source),
                "commit",
                "-m",
                "version 1",
                cwd=root,
            )
            self._run_git("clone", "--bare", str(source), str(remote), cwd=root)
            self._run_git(
                "-C",
                str(source),
                "remote",
                "add",
                "origin",
                str(remote),
                cwd=root,
            )

            script = codex_block.group(1).replace(
                "https://github.com/wallmage/repo-scout.git",
                str(remote),
            )
            stale_checkout = install_cwd / "repo-scout"
            self._run_git("clone", str(remote), str(stale_checkout), cwd=root)
            (
                stale_checkout
                / "repo-scout"
                / "obsolete-from-checkout.txt"
            ).write_text("must never be installed\n")
            shell_environment = {
                "HOME": str(fake_home),
                "PATH": os.environ["PATH"],
            }

            first_install = subprocess.run(
                ["/bin/sh", "-c", f"{script}\nfalse\necho survived\n"],
                cwd=install_cwd,
                env=shell_environment,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("survived", first_install.stdout)
            installed_skill = (
                fake_home / ".agents" / "skills" / "repo-scout" / "SKILL.md"
            )
            self.assertEqual("version 1\n", installed_skill.read_text())
            installed_root = installed_skill.parent
            legacy_nested_skill = installed_root / "repo-scout" / "SKILL.md"
            legacy_nested_skill.parent.mkdir()
            legacy_nested_skill.write_text("legacy nested version\n")
            (installed_root / "obsolete.txt").write_text("must be removed\n")

            source_skill.write_text("version 2\n")
            self._run_git("-C", str(source), "add", ".", cwd=root)
            self._run_git(
                "-C",
                str(source),
                "commit",
                "-m",
                "version 2",
                cwd=root,
            )
            self._run_git(
                "-C",
                str(source),
                "push",
                "origin",
                "main",
                cwd=root,
            )

            subprocess.run(
                ["/bin/sh", "-c", script],
                cwd=install_cwd,
                env=shell_environment,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual("version 2\n", installed_skill.read_text())
            self.assertEqual(
                [installed_skill],
                list((fake_home / ".agents" / "skills").rglob("SKILL.md")),
            )
            checkout_root = source / "repo-scout"
            installed_entries = {
                path.relative_to(installed_root)
                for path in installed_root.rglob("*")
            }
            checkout_entries = {
                path.relative_to(checkout_root)
                for path in checkout_root.rglob("*")
            }
            self.assertEqual(checkout_entries, installed_entries)

    @staticmethod
    def _run_git(*arguments, cwd):
        subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_install_verification_respects_malice_only_reporting(self):
        install = (ROOT / "INSTALL.md").read_text()

        self.assertNotIn("installation permissions, safety evidence", install)
        self.assertIn("deliberate malice", install)

    def test_shipped_instructions_have_no_reduced_audit_modes(self):
        instructions = self.skill.lower()
        for phrase in (
            "quick scout",
            "quick-scout",
            "quick audit",
            "quick-audit",
            "quick inspection",
            "quick-inspection",
            "casual",
            "casual review",
            "casual-review",
            "reduced audit",
            "reduced-audit",
            "reduced inspection",
            "reduced-inspection",
            "mode-dependent inspection",
            "mode-dependent-inspection",
        ):
            self.assertNotIn(phrase, instructions)
        for pattern in (
            r"\b(?:quick|casual|reduced)[ -](?:scout|audit|inspection|review)\b",
            r"\bmode[ -]dependent[ -](?:scout|audit|inspection|review)\b",
        ):
            self.assertIsNone(re.search(pattern, instructions), pattern)

    def test_inspection_and_installation_are_separate_phases(self):
        self.assertIn("During inspection, never install or execute target code", self.skill)
        self.assertIn("resume the user's authorized installation workflow", self.skill)
        self.assertRegex(
            self.skill,
            r"(?s)🟢 \*\*INSTALL\*\*.*resume the user's authorized installation "
            r"workflow for that chosen scope",
        )
        self.assertNotIn("Never install the skill, never register it", self.skill)

    def test_audit_questions_never_authorize_installation(self):
        self.assertIn(
            '"is this worth installing?" and "is this worth adopting?" are '
            "audit-only questions",
            self.skill,
        )
        self.assertIn(
            "Only an imperative request to install, set up, or adopt the target "
            "authorizes changing the user's machine",
            self.skill,
        )
        self.assertNotIn("asked to install or adopt the target", self.skill)
        self.assertIn(
            "If the user gave an imperative install, setup, or adoption request",
            self.report,
        )
        self.assertNotIn(
            "If the user already asked to install",
            self.report,
        )

    def test_verdict_is_binary_install_or_skip(self):
        shipped = [
            path
            for path in SKILL_DIR.rglob("*")
            if path.is_file() and path.suffix.lower() in {".md", ".py", ".yaml"}
        ]
        for path in shipped:
            self.assertNotIn(
                "CHERRY-PICK",
                path.read_text(),
                f"CHERRY-PICK found in {path.relative_to(SKILL_DIR)}",
            )
        # Binary verdict named across the shipped instructions.
        self.assertIn("🟢 INSTALL or 🔴 SKIP", self.skill)
        self.assertIn("Never return a middle verdict", self.skill)
        self.assertIn("🟢 INSTALL or 🔴 SKIP, never a middle option", self.rubric)
        self.assertIn("**Verdict: 🟢 INSTALL | 🔴 SKIP**", self.report)
        # Partial-value cases get a chosen-scope sentence the skill decides itself.
        self.assertIn("what part is being set up and what is left out", self.report)
        self.assertIn("never present the reader a menu", self.skill)
        # No-hedging rule and tiebreaker are present on the verdict line.
        self.assertIn(
            'Hedging on the verdict line ("probably", "it depends") is prohibited',
            self.skill,
        )
        self.assertIn(
            "would a busy non-technical user be glad the recommended scope got installed",
            self.skill,
        )

    def test_skip_fires_only_on_the_seven_closed_triggers(self):
        for source_name, source in (("SKILL.md", self.skill), ("rubric", self.rubric)):
            for trigger in (
                "Fake",
                "Malicious or suspicious",
                "Hazardous to the user",
                "Broken as shipped",
                "Abandoned and obsolete",
                "Unusable for this user",
                "Superseded",
            ):
                self.assertIn(trigger, source, f"{trigger} missing from {source_name}")
        # The SKIP list is closed to exactly those seven triggers.
        self.assertIn(
            "fires only when at least one of these seven is evidenced", self.skill
        )
        self.assertIn("nothing else ever produces a red", self.skill)
        self.assertIn("fired only by one of the seven triggers", self.skill)
        self.assertRegex(
            self.rubric,
            r"(?s)🔴 \*\*SKIP:\*\* Fires only when at least one of these seven is evidenced",
        )
        # Abandoned verdict must say the author abandoned it; superseded names the successor.
        self.assertIn(
            "say plainly that the author has abandoned the project", self.skill
        )
        self.assertIn("the successor named as the alternative", self.skill)
        self.assertIn("the author has abandoned the project", self.rubric)
        # A broken individual path is never a SKIP.
        self.assertIn(
            "A lagging or broken *individual* install path is never a SKIP", self.skill
        )
        # Default-green posture: no "green, but…" hedging.
        self.assertIn('no "green, but…" framing', self.skill)
        self.assertIn("never red on an unverified prior", self.rubric)
        # Popularity principle intact both directions.
        self.assertIn("Popularity proves nothing either way", self.skill)
        self.assertIn("still goes red if a tripwire fires", self.skill)

    def test_freshness_is_category_aware_with_prior_plus_confirmation(self):
        # Category thresholds: AI 3mo/6mo and self-contained never-by-date-alone.
        for phrase in ("> 3 months", "> 6 months", "never by date alone"):
            self.assertIn(phrase, self.skill, f"{phrase} missing from SKILL.md")
            self.assertIn(phrase, self.rubric, f"{phrase} missing from rubric")
        # Prior-plus-confirmation: calendar alone never reds; needs a confirming signal.
        self.assertIn(
            "requires *both* a category threshold exceeded *and* at least one "
            "confirming signal",
            self.skill,
        )
        self.assertIn(
            "requires both the threshold exceeded and at least one confirming signal",
            self.rubric,
        )
        self.assertIn('"no longer maintained; works today"', self.skill)
        self.assertIn("never red on an unverified prior", self.skill)
        # AI-coupled example named in the README freshness bullet, both languages.
        readme = (ROOT / "README.md").read_text()
        self.assertIn("presumed dead", readme)
        self.assertIn("已废弃", readme)

    def test_subagents_have_no_model_tier_requirement(self):
        self.assertIn(
            "10 or more skills or a Medium/Large-tier repository", self.skill
        )
        self.assertIn("use parallel subagents actively", self.skill)
        self.assertIn("using the same model as the main conversation is fine", self.skill)
        for phrase in ("N−1", "N-1", "lower tier", "lower-tier"):
            self.assertNotIn(phrase, self.skill)

    def test_local_snapshot_identity_and_self_audit_are_defined(self):
        self.assertIn("whether the worktree is dirty", self.skill)
        self.assertIn("content hash", self.skill)
        self.assertIn("previously trusted copy of the scanner", self.skill)
        self.assertIn("manual inventory fallback", self.skill)

    def test_installation_is_bound_to_the_audited_snapshot(self):
        for phrase in (
            "Install only the exact snapshot that produced the verdict",
            "Every Git source",
            "recorded commit SHA is source identity, not the installation payload",
            "content-addressed snapshot made from the exact source bytes before "
            "inspection",
            "clean or dirty",
            "never substitute HEAD or a recorded commit SHA for the frozen bytes",
            "execute the saved bytes whose content hash was audited",
            "never re-fetch and execute a moving branch, tag, package label, or URL",
            "stop installation and audit the changed content before proceeding",
        ):
            self.assertIn(phrase, self.skill)
        self.assertRegex(
            self.skill,
            r"(?s)Mode 1 — run the documented commands.*exact audited snapshot",
        )

    def test_workflow_focuses_on_mechanism_and_merit(self):
        for phrase in (
            "every SKILL.md",
            "core mechanism",
            "commit SHA",
            "dependencies",
            "license",
            "compatibility",
            "installation permissions",
        ):
            self.assertIn(phrase, self.skill)
        self.assertNotIn("coverage ledger", self.skill.lower())
        self.assertNotIn("appendix", self.skill.lower())

    def test_report_is_merit_focused_with_malice_only_tripwire(self):
        self.assertIn("no security commentary", self.report)
        self.assertIn("deliberate malice", self.report)
        self.assertNotIn("## Safety", self.report)
        self.assertNotIn("coverage-ledger", self.report)
        self.assertNotIn("if clean", self.report.lower())
        self.assertNotIn("— clean", self.report)
        self.assertIn("Never report unintended flaws", self.skill)
        self.assertIn("never reported", self.rubric)
        self.assertIn("The user can override any verdict", self.rubric)

    def test_report_is_plain_language_for_nontechnical_readers(self):
        # The visible report answers five plain questions in four sections.
        for heading in (
            "## What it is",
            "## Why you'd want it",
            "## Watch out for",
            "## On your machine",
        ):
            self.assertIn(heading, self.report)
        # Audit bookkeeping and developer tables are gone from the visible report.
        for heading in (
            "## Source and audit coverage",
            "## Compatibility and ownership",
            "## How it works — the mechanism",
            "## The active ingredients",
            "## The filler",
            "## Best fit",
            "## 10-minute reading map",
            "## Worth stealing",
            "## Bottom line",
        ):
            self.assertNotIn(heading, self.report)
        # Half the old length, verdict as a short plain block, few shortcomings.
        self.assertIn("half a page", self.report)
        self.assertIn("three to five short sentences", self.report)
        self.assertIn("At most two bullets", self.report)
        self.assertIn("experience standpoint", self.report)
        # Rubric scores never reach the user.
        self.assertIn("No numeric scores and no rubric axis names", self.report)
        self.assertIn("internal reasoning only", self.rubric)
        self.assertIn("Write for moms and dads", self.skill)
        self.assertIn(
            "translate everything, including the verdict words", self.skill
        )

    def test_deep_dive_material_is_hidden_until_asked(self):
        self.assertIn("## The deep dive", self.report)
        self.assertIn('"deep dive"', self.report)
        self.assertIn("advanced info", self.report)
        self.assertIn("deeper info", self.report)
        # The developer material is still researched, just not volunteered.
        self.assertIn("10-minute reading map", self.report)
        self.assertIn("Worth stealing", self.report)
        self.assertIn("Never advertise that this level exists", self.report)
        self.assertIn("never advertise that it exists", self.skill)
        self.assertIn("deep-dive notes", self.skill)

    def test_recommendation_is_gui_first_single_path(self):
        self.assertIn("experience rule", self.skill)
        self.assertIn("effort rule", self.skill)
        self.assertIn(
            "a terminal-only variant is recommended only when nothing graphical exists",
            self.skill,
        )
        self.assertIn("fewest steps and decisions", self.skill)
        self.assertIn(
            "never justifies a cut-down version of the product", self.skill
        )
        for surface in (self.skill, self.report):
            self.assertNotIn("fewest new installs", surface)
            self.assertNotIn("neutral peers", surface)
        self.assertIn("one recommended way — never a menu", self.report)
        self.assertIn("you don't need them", self.report)

    def test_assisted_install_matches_report_and_verifies_like_a_user(self):
        self.assertIn(
            "uses exactly the path named in **On your machine**", self.skill
        )
        self.assertIn("never switch silently", self.skill)
        self.assertIn(
            "never leave the user with terminal windows to keep open", self.skill
        )
        self.assertIn("Verify like the user would", self.skill)
        self.assertIn("never just a command echoing a version", self.skill)
        self.assertIn(
            "leading with the one thing the user should do", self.skill
        )
        self.assertIn(
            "never vague verbs like \"patching things up\"", self.skill
        )

    def test_environment_detection_probes_read_only(self):
        self.assertIn("Detect the environment (read-only)", self.skill)
        self.assertIn("Probe read-only, and probe only what matters", self.skill)
        self.assertIn(
            "never install, never mutate, never start a daemon, service, or network call while probing",
            self.skill,
        )
        self.assertIn("`command -v x` / `x --version`-style checks only", self.skill)
        self.assertIn("present the documented paths un-tailored", self.skill)

    def test_install_offer_reuses_existing_approval(self):
        self.assertIn("Offer assisted installation", self.skill)
        self.assertIn("This extends the pre-install gate", self.skill)
        for surface in (self.skill, self.report):
            self.assertIn("audit only", surface)
            self.assertIn("do not ask again", surface)
        self.assertIn(
            "If the user gave an imperative install, setup, or adoption request",
            self.skill,
        )
        self.assertIn(
            "that original instruction is the per-session approval",
            self.skill,
        )
        self.assertIn(
            "Approval for this session is either the user's original explicit "
            "install request or the single yes to that post-audit offer",
            self.skill,
        )
        self.assertIn("On the approval defined above", self.skill)
        self.assertIn(
            "The approval defined above is required and is per-session",
            self.skill,
        )
        self.assertNotIn("On the user's yes", self.skill)
        self.assertNotIn("the user's explicit yes is required", self.skill)
        self.assertIn("make no offer after an unapproved", self.skill)

    def test_assisted_install_never_handles_secrets(self):
        self.assertIn(
            "never types, pastes, invents, or requests credentials, API keys, "
            "or payment details into anything",
            self.skill,
        )
        self.assertIn("explains what the user must enter and where, then waits", self.skill)
        self.assertIn(
            "Account creation, purchases, and terms acceptance are always the "
            "user's own steps",
            self.skill,
        )

    def test_assisted_install_has_three_mode_fallback_chain(self):
        self.assertIn("Mode 1 — run the documented commands", self.skill)
        self.assertIn("Mode 2 — computer use for manual steps", self.skill)
        self.assertIn("Mode 3 — printed manual", self.skill)
        self.assertRegex(
            self.skill,
            r"(?s)Mode 2 — computer use.*harness exposes desktop or browser control",
        )
        self.assertRegex(
            self.skill,
            r"(?s)Mode 3 — printed manual.*universal fallback and is always possible",
        )
        self.assertIn(
            "No computer use for a manual step:", self.skill
        )
        self.assertIn(
            "No shell for environment detection:", self.skill
        )

    def test_rubric_covers_installability_and_audit_completeness(self):
        for phrase in (
            "Compatibility & dependencies",
            "License",
            "Installation permissions",
            "Audit completeness",
        ):
            self.assertIn(phrase, self.rubric)

    def test_openai_interface_metadata_exists(self):
        metadata = SKILL_DIR / "agents" / "openai.yaml"
        self.assertTrue(metadata.is_file())
        text = metadata.read_text()
        self.assertIn('display_name: "Repo Scout"', text)
        self.assertIn("$repo-scout", text)

    def test_standalone_skill_includes_the_repository_license(self):
        self.assertEqual(
            (ROOT / "LICENSE").read_text(),
            (SKILL_DIR / "LICENSE").read_text(),
        )

    def test_shipped_skill_content_remains_english(self):
        for path in SKILL_DIR.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".md", ".py", ".yaml"}:
                self.assertIsNone(
                    re.search(r"[\u4e00-\u9fff]", path.read_text()),
                    f"Chinese text found in {path.relative_to(SKILL_DIR)}",
                )


if __name__ == "__main__":
    unittest.main()
