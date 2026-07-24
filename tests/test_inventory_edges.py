import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "repo-scout"
    / "scripts"
    / "inventory.py"
)
SPEC = importlib.util.spec_from_file_location("repo_scout_inventory_edges", MODULE_PATH)
inventory = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(inventory)


class MetadataParserTests(unittest.TestCase):
    def test_manifest_parser_failures_do_not_abort_the_repository_scan(self):
        cases = {
            "package.json": (
                "_parse_package_json",
                ValueError("invalid number"),
                "ValueError",
            ),
            "Cargo.toml": (
                "_parse_cargo_toml",
                TypeError("unsupported TOML value"),
                "TypeError",
            ),
            "pyproject.toml": (
                "_parse_pyproject",
                RuntimeError("unexpected parser failure"),
                "RuntimeError",
            ),
            "requirements.txt": (
                "_parse_requirements",
                UnicodeError("unexpected requirement failure"),
                "UnicodeError",
            ),
        }

        for manifest_name, (
            parser_name,
            parser_error,
            exception_name,
        ) in cases.items():
            with self.subTest(manifest=manifest_name), tempfile.TemporaryDirectory() as root_dir:
                root = Path(root_dir)
                (root / "README.md").write_text("# Still inspected\n")
                (root / manifest_name).write_text("{}\n")

                with mock.patch.object(
                    inventory,
                    parser_name,
                    side_effect=parser_error,
                ):
                    result = inventory.scan_repository(root)

                self.assertIn(
                    "README.md",
                    {record.path for record in result.scanned_files},
                )
                self.assertIn(
                    (
                        manifest_name,
                        f"manifest metadata parse failed: {exception_name}",
                    ),
                    {(record.path, record.reason) for record in result.skipped},
                )

    def test_real_manifest_value_edge_cases_do_not_abort_the_scan(self):
        if inventory.tomllib is None:
            self.skipTest("tomllib edge cases require Python 3.11+")

        cases = {
            "Cargo.toml": (
                "[dependencies]\n"
                "demo = { version = 2026-07-24 }\n",
                "TypeError",
            ),
            "pyproject.toml": (
                "[build-system]\n"
                "requires = 2026-07-24\n",
                "TypeError",
            ),
        }

        for manifest_name, (content, exception_name) in cases.items():
            with self.subTest(manifest=manifest_name), tempfile.TemporaryDirectory() as root_dir:
                root = Path(root_dir)
                (root / "README.md").write_text("# Still inspected\n")
                (root / manifest_name).write_text(content)

                result = inventory.scan_repository(root)

                self.assertIn(
                    "README.md",
                    {record.path for record in result.scanned_files},
                )
                self.assertIn(
                    (
                        manifest_name,
                        f"manifest metadata parse failed: {exception_name}",
                    ),
                    {(record.path, record.reason) for record in result.skipped},
                )

    def test_malformed_manifest_metadata_is_disclosed(self):
        cases = {
            "package.json": ("not JSON", "invalid JSON object"),
            "manifest.json": ("[", "invalid JSON object"),
        }
        if inventory.tomllib is not None:
            cases.update(
                {
                    "Cargo.toml": ("[package", "invalid TOML"),
                    "pyproject.toml": ("[project", "invalid TOML"),
                }
            )

        for manifest_name, (content, reason) in cases.items():
            with self.subTest(manifest=manifest_name), tempfile.TemporaryDirectory() as root_dir:
                root = Path(root_dir)
                (root / manifest_name).write_text(content)

                result = inventory.scan_repository(root)

                self.assertIn(
                    (
                        manifest_name,
                        f"manifest metadata parse failed: {reason}",
                    ),
                    {(record.path, record.reason) for record in result.skipped},
                )

    def test_frontmatter_parser_handles_absent_valid_and_invalid_scalars(self):
        self.assertEqual((None, None), inventory.parse_frontmatter("# No metadata\n"))
        self.assertEqual("quoted", inventory._parse_scalar('"quoted"'))
        self.assertEqual("'unterminated", inventory._parse_scalar("'unterminated"))
        self.assertEqual(r"'bad\xZZ'", inventory._parse_scalar(r"'bad\xZZ'"))
        self.assertEqual(
            ("demo", "Use when a repository needs review."),
            inventory.parse_frontmatter(
                "---\n"
                "ignored: value\n"
                "name: demo\n"
                'description: "Use when a repository needs review."\n'
                "---\n"
            ),
        )

    def test_link_helpers_cover_windows_reparse_metadata(self):
        metadata = mock.Mock()
        metadata.st_mode = stat.S_IFREG
        metadata.st_file_attributes = inventory.REPARSE_POINT_ATTRIBUTE

        self.assertTrue(inventory._is_link_like(metadata))
        self.assertEqual("Windows reparse point", inventory._link_like_reason(metadata))
        self.assertEqual(
            "inspected",
            inventory._path_evidence_detail("", "inspected"),
        )

    def test_manifest_categories_cover_supported_descriptors(self):
        cases = {
            ".claude-plugin/plugin.json": "Claude plugin manifest",
            ".codex-plugin/plugin.json": "Codex plugin manifest",
            "agents/openai.yaml": "OpenAI agent metadata",
            "requirements-dev.txt": "Python requirements",
            "Cargo.lock": "dependency lockfile",
            "plugin.json": "plugin manifest",
            "Dockerfile": "build/install descriptor",
            "notes.yaml": None,
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(expected, inventory._manifest_category(path))

    def test_path_evidence_covers_integrations_platforms_and_licenses(self):
        result = inventory.Inventory(root="/tmp/demo")

        for path in (
            "hooks/run",
            "commands/check.md",
            "agents/openai.yaml",
            ".codex-plugin/plugin.json",
            ".claude/settings.json",
            ".gemini/config.json",
            "LICENSE.txt",
        ):
            inventory._collect_path_evidence(result, path, "inspected")

        self.assertEqual(
            {"agents", "commands", "hooks"},
            {item.category for item in result.integration_paths},
        )
        details = {(item.category, item.detail) for item in result.compatibility}
        self.assertIn(("platform", "OpenAI Codex metadata; inspected"), details)
        self.assertIn(("platform", "OpenAI Codex plugin; inspected"), details)
        self.assertIn(("platform", "Claude configuration; inspected"), details)
        self.assertIn(("platform", "Gemini instructions; inspected"), details)
        self.assertEqual(
            [("LICENSE.txt", "license file; inspected")],
            [(item.path, item.detail) for item in result.licenses],
        )

    def test_requirement_parser_handles_ignored_direct_and_local_values(self):
        self.assertIsNone(inventory._dependency_from_requirement("", "runtime", "req.txt"))
        self.assertIsNone(
            inventory._dependency_from_requirement("-r base.txt", "runtime", "req.txt")
        )
        direct = inventory._dependency_from_requirement(
            "demo[cli] @ https://example.invalid/demo.whl # note",
            "runtime",
            "req.txt",
        )
        self.assertEqual(
            inventory.DependencyRecord(
                "demo[cli]", "@ https://example.invalid/demo.whl", "runtime", "req.txt"
            ),
            direct,
        )
        local = inventory._dependency_from_requirement("./vendor/demo", "runtime", "req.txt")
        self.assertEqual("./vendor/demo", local.name)
        self.assertEqual("", local.specification)
        vcs = inventory._dependency_from_requirement(
            "git+https://example.invalid/demo.git",
            "runtime",
            "req.txt",
        )
        self.assertEqual("git+https://example.invalid/demo.git", vcs.name)
        self.assertEqual("", vcs.specification)
        vcs_extra = inventory._dependency_from_requirement(
            "git+https://example.invalid/demo.git#egg=demo&subdirectory=python",
            "runtime",
            "req.txt",
        )
        self.assertEqual("demo", vcs_extra.name)
        self.assertEqual(
            "@ git+https://example.invalid/demo.git#subdirectory=python",
            vcs_extra.specification,
        )

    def test_package_json_parser_handles_optional_shapes_and_entry_points(self):
        result = inventory.Inventory(root="/tmp/demo")
        inventory._parse_package_json("not json", "package.json", result)
        inventory._parse_package_json("[]", "package.json", result)
        inventory._parse_package_json(
            json.dumps(
                {
                    "license": "MIT",
                    "dependencies": ["wrong shape"],
                    "engines": {"node": ">=20", "vscode": "^1.90"},
                    "os": "darwin",
                    "cpu": "arm64",
                    "bin": "cli.js",
                    "contributes": {},
                    "scripts": {"test": "node test.js"},
                }
            ),
            "package.json",
            result,
        )

        self.assertEqual([], result.dependencies)
        self.assertIn(
            inventory.EvidenceRecord("declared", "package.json", "MIT"),
            result.licenses,
        )
        self.assertIn(
            inventory.EvidenceRecord("operating system", "package.json", "darwin"),
            result.compatibility,
        )
        self.assertIn(
            inventory.EvidenceRecord("architecture", "package.json", "arm64"),
            result.compatibility,
        )
        hints = {(item.signal, item.detail) for item in result.archetype_hints}
        self.assertIn(("package entry point", "bin declared"), hints)
        self.assertIn(("extension manifest", "VS Code extension package.json"), hints)

    def test_pyproject_parser_covers_build_license_and_malformed_shapes(self):
        result = inventory.Inventory(root="/tmp/demo")
        inventory._parse_pyproject(
            "[project]\n"
            'license = "MIT"\n'
            'dependencies = ["runtime>=1"]\n'
            "[build-system]\n"
            'requires = ["builder>=2"]\n'
            "[project.optional-dependencies]\n"
            'docs = ["sphinx>=7"]\n',
            "pyproject.toml",
            result,
        )
        dependencies = {
            (item.name, item.specification, item.group)
            for item in result.dependencies
        }
        self.assertIn(("runtime", ">=1", "runtime"), dependencies)
        self.assertIn(("builder", ">=2", "build"), dependencies)
        self.assertIn(("sphinx", ">=7", "optional:docs"), dependencies)
        self.assertIn(
            inventory.EvidenceRecord("declared", "pyproject.toml", "MIT"),
            result.licenses,
        )

        malformed = inventory.Inventory(root="/tmp/demo")
        inventory._parse_pyproject("[project]\ndependencies = ???", "bad.toml", malformed)
        self.assertEqual([], malformed.dependencies)

        unusual = inventory.Inventory(root="/tmp/demo")
        with mock.patch.object(
            inventory,
            "_load_toml",
            return_value={
                "project": {
                    "dependencies": [],
                    "optional-dependencies": {"bad": "not a list"},
                    "license": {"file": "COPYING"},
                },
                "build-system": "not a table",
            },
        ):
            inventory._parse_pyproject("", "pyproject.toml", unusual)
        self.assertIn(
            inventory.EvidenceRecord("declared", "pyproject.toml", "COPYING"),
            unusual.licenses,
        )

        not_a_project = inventory.Inventory(root="/tmp/demo")
        with mock.patch.object(
            inventory,
            "_load_toml",
            return_value={"project": "wrong shape"},
        ):
            inventory._parse_pyproject("", "pyproject.toml", not_a_project)
        self.assertEqual([], not_a_project.dependencies)

    def test_fallback_pyproject_and_toml_helpers_cover_empty_sections(self):
        self.assertEqual("", inventory._toml_section("[other]\nx = 1\n", "project"))
        self.assertEqual([], inventory._fallback_toml_array("", "dependencies"))
        parsed = inventory._fallback_pyproject(
            "[project]\n"
            'dependencies = ["demo>=1"]\n'
            "[project.optional-dependencies]\n"
            'test = ["pytest>=8"]\n'
        )
        self.assertEqual(["demo>=1"], parsed["project"]["dependencies"])
        self.assertEqual(
            ["pytest>=8"],
            parsed["project"]["optional-dependencies"]["test"],
        )
        with mock.patch.object(inventory, "tomllib", None):
            self.assertEqual({}, inventory._load_toml("[package]\nname='x'\n"))

    def test_go_cargo_and_web_manifests_are_parsed(self):
        result = inventory.Inventory(root="/tmp/demo")
        inventory._parse_go_mod(
            "module example/demo\n"
            "// comment\n"
            "go 1.22\n"
            "require (\n"
            " example/one v1.0.0\n"
            " example/two v2.0.0 // indirect\n"
            ")\n",
            "go.mod",
            result,
        )
        inventory._parse_cargo_toml(
            "[package]\n"
            'name = "demo"\n'
            'rust-version = "1.75"\n'
            'license = "Apache-2.0"\n'
            "[dependencies]\n"
            'serde = "1"\n'
            'reqwest = { version = "0.12", features = ["json"] }\n'
            "[dev-dependencies]\n"
            'tempfile = "3"\n'
            "[build-dependencies]\n"
            'cc = "1"\n',
            "Cargo.toml",
            result,
        )
        inventory._parse_web_manifest(
            '{"manifest_version":3,"name":"demo"}',
            "manifest.json",
            result,
        )
        inventory._parse_web_manifest("not json", "manifest.json", result)
        inventory._parse_web_manifest("[]", "manifest.json", result)

        dependencies = {(item.name, item.group) for item in result.dependencies}
        self.assertTrue(
            {
                ("example/one", "runtime"),
                ("example/two", "runtime"),
                ("serde", "runtime"),
                ("reqwest", "runtime"),
                ("tempfile", "development"),
                ("cc", "build"),
            }.issubset(dependencies)
        )
        self.assertIn(
            inventory.EvidenceRecord("runtime", "Cargo.toml", "rust 1.75"),
            result.compatibility,
        )
        self.assertIn(
            inventory.EvidenceRecord("declared", "Cargo.toml", "Apache-2.0"),
            result.licenses,
        )
        self.assertIn(
            inventory.ArchetypeHint(
                "extension manifest", "browser WebExtension manifest", "manifest.json"
            ),
            result.archetype_hints,
        )

    def test_scan_dispatches_cargo_manifest_parser(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "Cargo.toml").write_text(
                "[package]\n"
                'name = "demo"\n'
                'rust-version = "1.75"\n'
            )

            result = inventory.scan_repository(root)

            self.assertIn(
                inventory.EvidenceRecord("runtime", "Cargo.toml", "rust 1.75"),
                result.compatibility,
            )


class ReadBoundaryTests(unittest.TestCase):
    def test_path_open_helpers_reject_invalid_paths(self):
        with self.assertRaisesRegex(ValueError, "repository-relative"):
            inventory._open_relative_file(0, Path("../outside"))
        with self.assertRaisesRegex(ValueError, "absolute"):
            inventory._open_absolute_directory(Path("relative"))
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            with self.assertRaisesRegex(ValueError, "repository-relative"):
                inventory._snapshot_components(root, root)

    def test_strict_read_rejects_outside_path_and_changed_file(self):
        if not inventory.SECURE_RELATIVE_OPEN_SUPPORTED:
            self.skipTest("strict descriptor-relative reads are unavailable")
        with tempfile.TemporaryDirectory() as root_dir, tempfile.TemporaryDirectory() as other_dir:
            root = Path(root_dir)
            inside = root / "inside.txt"
            inside.write_text("inside")
            other = Path(other_dir) / "other.txt"
            other.write_text("other!")
            root_fd = inventory._open_absolute_directory(root.resolve())
            try:
                text, reason = inventory._safe_read_strict(
                    other, root, root_fd, 100
                )
                self.assertIsNone(text)
                self.assertIn("cannot read securely", reason)

                text, reason = inventory._safe_read_strict(
                    inside,
                    root,
                    root_fd,
                    100,
                    expected_metadata=other.stat(),
                )
                self.assertIsNone(text)
                self.assertEqual("path changed while it was being opened", reason)
            finally:
                os.close(root_fd)

    def test_fallback_read_rejects_nonregular_and_open_errors(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            child = root / "directory"
            child.mkdir()
            text, reason = inventory._safe_read_fallback(child, root, 100)
            self.assertIsNone(text)
            self.assertEqual("not a regular file", reason)

            regular = root / "value.txt"
            regular.write_text("value")
            with mock.patch.object(
                inventory.os,
                "open",
                side_effect=PermissionError(13, "denied"),
            ):
                text, reason = inventory._safe_read_fallback(regular, root, 100)
            self.assertIsNone(text)
            self.assertIn("cannot read securely: denied", reason)

    def test_fallback_read_rejects_opened_reparse_and_changed_metadata(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            regular = root / "value.txt"
            regular.write_text("value")

            reparse_metadata = mock.Mock()
            reparse_metadata.st_mode = stat.S_IFREG
            reparse_metadata.st_file_attributes = inventory.REPARSE_POINT_ATTRIBUTE
            with mock.patch.object(inventory.os, "fstat", return_value=reparse_metadata):
                text, reason = inventory._safe_read_fallback(regular, root, 100)
            self.assertIsNone(text)
            self.assertEqual("Windows reparse point", reason)

            other = root / "other.txt"
            other.write_text("other")
            text, reason = inventory._safe_read_fallback(
                regular,
                root,
                100,
                expected_metadata=other.stat(),
            )
            self.assertIsNone(text)
            self.assertEqual("path changed while it was being opened", reason)

            self.assertFalse(inventory._snapshots_match([], regular, root))

    def test_descriptor_reader_handles_text_binary_size_and_read_errors(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            text_path = root / "value.txt"
            text_path.write_text("hello")
            descriptor = os.open(text_path, os.O_RDONLY)
            try:
                self.assertEqual(
                    ("hello", None),
                    inventory._read_bounded_descriptor(descriptor, 10),
                )
            finally:
                os.close(descriptor)

            directory_descriptor = os.open(root, os.O_RDONLY)
            try:
                self.assertEqual(
                    (None, "not a regular file"),
                    inventory._read_bounded_descriptor(directory_descriptor, 10),
                )
            finally:
                os.close(directory_descriptor)

            binary_path = root / "binary"
            binary_path.write_bytes(b"a\x00b")
            descriptor = os.open(binary_path, os.O_RDONLY)
            try:
                self.assertEqual(
                    (None, "binary file"),
                    inventory._read_bounded_descriptor(descriptor, 10),
                )
            finally:
                os.close(descriptor)

            descriptor = os.open(text_path, os.O_RDONLY)
            try:
                self.assertEqual(
                    (None, "exceeds 2-byte read limit"),
                    inventory._read_bounded_descriptor(descriptor, 2),
                )
            finally:
                os.close(descriptor)

            empty_path = root / "empty"
            empty_path.write_bytes(b"")
            descriptor = os.open(empty_path, os.O_RDONLY)
            try:
                with mock.patch.object(
                    inventory.os,
                    "read",
                    side_effect=OSError(5, "read failed"),
                ):
                    text, reason = inventory._read_bounded_descriptor(descriptor, 10)
                self.assertIsNone(text)
                self.assertIn("cannot read securely: read failed", reason)
            finally:
                os.close(descriptor)

    def test_descriptor_reader_detects_growth_past_limit(self):
        with tempfile.TemporaryDirectory() as root_dir:
            path = Path(root_dir) / "empty"
            path.write_bytes(b"")
            descriptor = os.open(path, os.O_RDONLY)
            try:
                with mock.patch.object(inventory.os, "read", return_value=b"xx"):
                    self.assertEqual(
                        (None, "exceeds 1-byte read limit"),
                        inventory._read_bounded_descriptor(descriptor, 1),
                    )
            finally:
                os.close(descriptor)


class RepositoryEdgeTests(unittest.TestCase):
    def test_scan_rejects_missing_file_and_negative_limit(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            file_path = root / "file.txt"
            file_path.write_text("value")
            with self.assertRaisesRegex(ValueError, "not a directory"):
                inventory.scan_repository(file_path)
            with self.assertRaisesRegex(ValueError, "read limit"):
                inventory.scan_repository(root, max_file_bytes=-1)
        with self.assertRaisesRegex(ValueError, "cannot inspect repository root"):
            inventory.scan_repository(Path("/definitely/missing/repo-scout"))

    def test_scan_rejects_root_descriptor_for_a_different_directory(self):
        if not inventory.SECURE_RELATIVE_OPEN_SUPPORTED:
            self.skipTest("strict descriptor-relative reads are unavailable")
        with tempfile.TemporaryDirectory() as root_dir, tempfile.TemporaryDirectory() as other_dir:
            other_fd = os.open(other_dir, os.O_RDONLY)
            with mock.patch.object(
                inventory,
                "_open_absolute_directory",
                return_value=other_fd,
            ):
                with self.assertRaisesRegex(ValueError, "root changed.*opened"):
                    inventory.scan_repository(Path(root_dir))

    def test_scan_discloses_excluded_directories_and_nonregular_files(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "node_modules").mkdir()
            (root / "node_modules" / "hidden.js").write_text("fetch('/hidden')")
            fifo = root / "named-pipe"
            if hasattr(os, "mkfifo"):
                os.mkfifo(fifo)

            result = inventory.scan_repository(root)

            skipped = {(item.path, item.reason) for item in result.skipped}
            self.assertIn(("node_modules", "excluded directory"), skipped)
            if hasattr(os, "mkfifo"):
                self.assertIn(("named-pipe", "not a regular file"), skipped)
            self.assertFalse(any("hidden" in item.snippet for item in result.findings))

    def test_archetype_hints_cover_kubernetes_procfile_and_vscode(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "k8s").mkdir()
            (root / "k8s" / "app.yaml").write_text("kind: Deployment\n")
            (root / "Procfile").write_text("web: server\n")
            (root / "package.json").write_text(
                json.dumps({"engines": {"vscode": "^1.90"}})
            )

            result = inventory.scan_repository(root)

            hints = {(item.signal, item.detail) for item in result.archetype_hints}
            self.assertIn(("deployment file", "Kubernetes manifest"), hints)
            self.assertIn(("deployment file", "Procfile"), hints)
            self.assertIn(("extension manifest", "VS Code extension package.json"), hints)


class RenderingAndCliTests(unittest.TestCase):
    def test_render_includes_all_sections_and_truncates_context_groups(self):
        result = inventory.Inventory(root="/tmp/demo", read_mode="fallback")
        result.scale = inventory.RepositoryScale(
            total_files=1,
            total_text_lines=2,
            top_extensions=[(".py", 2, 1)],
            tier="Small",
        )
        record = inventory.FileRecord(
            "SKILL.md", 2, 20, "skill", name="demo", description="Use when testing."
        )
        result.skills.append(record)
        result.scripts.append(inventory.FileRecord("run.py", 2, 20, "script"))
        result.executables.append(
            inventory.FileRecord("run.py", 2, 20, "script", executable=True)
        )
        result.documents.append(record)
        result.integration_paths.append(
            inventory.EvidenceRecord("hooks", "hooks/run", "inspected")
        )
        result.manifests.append(
            inventory.EvidenceRecord("npm manifest", "package.json", "detected")
        )
        result.dependencies.append(
            inventory.DependencyRecord("demo", "", "runtime", "package.json")
        )
        result.licenses.append(
            inventory.EvidenceRecord("declared", "package.json", "MIT")
        )
        result.compatibility.append(
            inventory.EvidenceRecord("runtime", "package.json", "node >=20")
        )
        result.install_surfaces.append(
            inventory.EvidenceRecord(
                "elevated privilege",
                "install.sh",
                "sudo install demo /usr/bin/demo",
                2,
                "behavior",
                "executable",
            )
        )
        result.skipped.append(
            inventory.SkippedRecord("linked", "symbolic link", "../outside")
        )
        result.archetype_hints.append(
            inventory.ArchetypeHint("server entry", "server.py", "server.py")
        )
        result.findings.append(
            inventory.Finding(
                "network call",
                "run.py",
                1,
                "fetch('/api')",
                "behavior",
                "source",
            )
        )
        for index in range(6):
            result.findings.append(
                inventory.Finding(
                    "network mention",
                    f"doc-{index}.md",
                    1,
                    "network",
                    "context",
                    "documentation",
                    lossy_decode=index == 0,
                )
            )

        rendered = inventory.render_inventory(result)

        for expected in (
            "Fallback mode is guarded",
            "Skills found: 1",
            "Integration surfaces: 1",
            "Declared dependencies: 1",
            "License evidence: 1",
            "Compatibility evidence: 1",
            "Install and permission surfaces: 1",
            "linked: symbolic link -> ../outside",
            "[network call; source]",
            "[lossy decode] doc-0.md:1",
            "... and 1 more",
        ):
            self.assertIn(expected, rendered)

    def test_safe_display_escapes_astral_format_characters(self):
        self.assertEqual(r"\U000e0001", inventory._safe_display("\U000e0001"))

    def test_cli_usage_success_and_scan_error(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(1, inventory.main(["inventory.py"]))
        self.assertIn("Usage:", stdout.getvalue())

        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as root_dir, mock.patch.object(
            inventory,
            "scan_repository",
            side_effect=ValueError("changed\x1b[2J\u202e"),
        ), contextlib.redirect_stderr(stderr):
            self.assertEqual(1, inventory.main(["inventory.py", root_dir]))
        error_output = stderr.getvalue()
        self.assertIn(r"inventory error: changed\x1b[2J\u202e", error_output)
        self.assertNotIn("\x1b", error_output)
        self.assertNotIn("\u202e", error_output)

        with tempfile.TemporaryDirectory() as root_dir:
            Path(root_dir, "README.md").write_text("hello\n")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(0, inventory.main(["inventory.py", root_dir]))
            self.assertIn("=== INVENTORY:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
