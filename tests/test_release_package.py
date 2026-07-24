from pathlib import Path
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "repo-scout.skill"
EXPECTED = {
    "repo-scout/LICENSE",
    "repo-scout/SKILL.md",
    "repo-scout/agents/openai.yaml",
    "repo-scout/references/report-template.md",
    "repo-scout/references/rubric.md",
    "repo-scout/scripts/inventory.py",
}


class ReleasePackageTests(unittest.TestCase):
    def test_archive_contains_only_the_shipped_skill_files(self):
        with zipfile.ZipFile(ARCHIVE) as archive:
            files = {name for name in archive.namelist() if not name.endswith("/")}
        self.assertEqual(EXPECTED, files)

    def test_archive_bytes_match_the_source_tree(self):
        with zipfile.ZipFile(ARCHIVE) as archive:
            for archived_path in EXPECTED:
                source = ROOT / archived_path
                self.assertEqual(
                    source.read_bytes(),
                    archive.read(archived_path),
                    archived_path,
                )


if __name__ == "__main__":
    unittest.main()
