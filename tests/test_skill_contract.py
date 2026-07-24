from pathlib import Path
import re
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
            r"(?s)CHERRY-PICK.*ask the user to approve the reduced installation scope",
        )
        self.assertNotIn("Never install the skill, never register it", self.skill)

    def test_subagents_have_no_model_tier_requirement(self):
        self.assertIn(
            "10 or more skills or a Medium/Large-tier repository", self.skill
        )
        self.assertIn("use parallel subagents actively", self.skill)
        self.assertIn("using the same model as the main conversation is fine", self.skill)
        for phrase in ("N−1", "N-1", "lower tier", "lower-tier"):
            self.assertNotIn(phrase, self.skill)

    def test_local_snapshot_identity_and_self_audit_are_defined(self):
        self.assertIn("record whether the worktree is dirty", self.skill)
        self.assertIn("content hash", self.skill)
        self.assertIn("previously trusted copy of the scanner", self.skill)
        self.assertIn("manual inventory fallback", self.skill)

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
        self.assertIn("## Source and audit coverage", self.report)
        self.assertIn("## Compatibility and ownership", self.report)
        self.assertIn("no security commentary", self.report)
        self.assertIn("deliberate malice", self.report)
        self.assertNotIn("## Safety", self.report)
        self.assertNotIn("coverage-ledger", self.report)
        self.assertNotIn("if clean", self.report.lower())
        self.assertNotIn("— clean", self.report)
        self.assertIn("Never report unintended flaws", self.skill)
        self.assertIn("never reported", self.rubric)
        self.assertIn("The user can override any verdict", self.rubric)

    def test_environment_detection_probes_read_only(self):
        self.assertIn("Detect the environment (read-only)", self.skill)
        self.assertIn("Probe read-only, and probe only what matters", self.skill)
        self.assertIn(
            "never install, never mutate, never start a daemon, service, or network call while probing",
            self.skill,
        )
        self.assertIn("`command -v x` / `x --version`-style checks only", self.skill)
        self.assertIn("present the documented paths un-tailored", self.skill)

    def test_install_offer_is_ask_once_and_per_session(self):
        self.assertIn("Offer assisted installation", self.skill)
        self.assertIn("This extends the pre-install gate", self.skill)
        self.assertIn("end the report with one question", self.skill)
        self.assertIn("make no offer after an unapproved", self.skill)
        self.assertIn(
            "the user's explicit yes is required and is per-session", self.skill
        )

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
