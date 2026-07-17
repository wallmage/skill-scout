#!/usr/bin/env python3
"""Inventory an untrusted skill repository without executing its code.

Usage: python inventory.py <path-to-repository>

The scanner is read-only. It refuses symbolic links, bounds every file read,
and reports files it could not inspect.
"""

import ast
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Dict, Iterable, List, Optional, Pattern, Tuple

try:
    import tomllib
except ImportError:  # Python 3.9 and 3.10
    tomllib = None


DEFAULT_MAX_FILE_BYTES = 2 * 1024 * 1024
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
    "venv",
}
SCRIPT_EXTS = {
    ".bat",
    ".cmd",
    ".js",
    ".lua",
    ".mjs",
    ".php",
    ".pl",
    ".ps1",
    ".py",
    ".rb",
    ".sh",
    ".ts",
    ".zsh",
}
DOC_EXTS = {".md", ".mdx", ".rst", ".txt"}
INTEGRATION_DIRS = {"agents", "commands", "hooks"}
LICENSE_PREFIXES = ("copying", "license", "notice")
MANIFEST_NAMES = {
    "cargo.toml": "Rust package manifest",
    "composer.json": "PHP Composer manifest",
    "gemfile": "Ruby Bundler manifest",
    "go.mod": "Go module manifest",
    "package.json": "npm manifest",
    "pom.xml": "Maven manifest",
    "pyproject.toml": "Python project manifest",
}


@dataclass(frozen=True)
class FileRecord:
    path: str
    lines: int
    size: int
    kind: str
    executable: bool = False
    name: Optional[str] = None
    description: Optional[str] = None


@dataclass(frozen=True)
class SkippedRecord:
    path: str
    reason: str


@dataclass(frozen=True)
class Finding:
    category: str
    path: str
    line: int
    snippet: str
    strength: str = "context"
    source_kind: str = "documentation"


@dataclass(frozen=True)
class EvidenceRecord:
    category: str
    path: str
    detail: str
    line: int = 0


@dataclass(frozen=True)
class DependencyRecord:
    name: str
    specification: str
    group: str
    path: str


@dataclass
class Inventory:
    root: str
    scanned_files: List[FileRecord] = field(default_factory=list)
    skills: List[FileRecord] = field(default_factory=list)
    scripts: List[FileRecord] = field(default_factory=list)
    executables: List[FileRecord] = field(default_factory=list)
    documents: List[FileRecord] = field(default_factory=list)
    skipped: List[SkippedRecord] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    integration_paths: List[EvidenceRecord] = field(default_factory=list)
    manifests: List[EvidenceRecord] = field(default_factory=list)
    dependencies: List[DependencyRecord] = field(default_factory=list)
    licenses: List[EvidenceRecord] = field(default_factory=list)
    compatibility: List[EvidenceRecord] = field(default_factory=list)
    install_surfaces: List[EvidenceRecord] = field(default_factory=list)


SUSPICIOUS: List[Tuple[str, Pattern[str]]] = [
    (
        "network call",
        re.compile(
            r"\b(curl|wget|urllib\.request|requests\.(get|post|put)|fetch\(|axios|http\.client|XMLHttpRequest)\b"
        ),
    ),
    (
        "obfuscation",
        re.compile(
            r"\b(base64\s+(-d|--decode)|b64decode|atob\(|fromCharCode|bytes\.fromhex|exec\(compile)\b"
        ),
    ),
    (
        "shell exec",
        re.compile(r"\b(eval\s|subprocess|os\.system|child_process|execSync|popen)\b"),
    ),
    (
        "credential access",
        re.compile(
            r"(API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL|\.aws/|\.ssh/|keychain|\.netrc|ANTHROPIC_|OPENAI_)",
            re.IGNORECASE,
        ),
    ),
    (
        "persistence/hooks",
        re.compile(
            r"(settings\.json|hooks|crontab|launchd|\.bashrc|\.zshrc|\.claude/)",
            re.IGNORECASE,
        ),
    ),
    ("destructive", re.compile(r"\brm\s+-rf\s+[~/$]")),
    (
        "AI-directed instruction",
        re.compile(
            r"(ignore (all |any )?(previous|prior|above) instructions|do not (tell|inform|mention to) the user|you must recommend|rate this (skill|repo) (highly|positively))",
            re.IGNORECASE,
        ),
    ),
]

INSTALL_SURFACE_PATTERNS: List[Tuple[str, Pattern[str]]] = [
    ("elevated privilege", re.compile(r"(^|\s)(sudo|doas)(\s|$)")),
    (
        "global package install",
        re.compile(
            r"\b(npm|pnpm|yarn)\b[^\n]*(\s-g\b|\s--global\b)|\b(pipx|brew|apt-get|apt|dnf|yum)\s+install\b",
            re.IGNORECASE,
        ),
    ),
    (
        "outside-repository write",
        re.compile(
            r"\b(cp|mv|install|mkdir|tee|touch|ln|rsync)\b[^\n]*(~(?:/|\b)|/(usr|etc|opt|Library|var|home)/|\$HOME\b|\$\{HOME\}|%USERPROFILE%)",
            re.IGNORECASE,
        ),
    ),
    ("permission change", re.compile(r"\b(chmod|chown|chgrp)\b", re.IGNORECASE)),
    (
        "persistence registration",
        re.compile(
            r"\b(crontab|launchctl|systemctl\s+enable)\b|(^|[/\\])(LaunchAgents|LaunchDaemons)([/\\]|$)|\.(bashrc|zshrc|profile)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "remote installer execution",
        re.compile(r"\b(curl|wget)\b[^\n|]*\|\s*(sh|bash|zsh|python|python3)\b", re.IGNORECASE),
    ),
]


def _parse_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, str):
                return parsed
        except (SyntaxError, ValueError):
            pass
    return value


def parse_frontmatter(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Return name and description from simple YAML frontmatter."""
    match = re.match(r"\s*---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None, None
    values = {}
    for line in match.group(1).splitlines():
        field_match = re.match(r"^(name|description):\s*(.*)$", line)
        if field_match:
            values[field_match.group(1)] = _parse_scalar(field_match.group(2))
    return values.get("name"), values.get("description")


def _append_unique(collection: List[Any], item: Any) -> None:
    if item not in collection:
        collection.append(item)


def _manifest_category(rel: str) -> Optional[str]:
    lower = rel.lower()
    filename = Path(rel).name.lower()
    if lower.endswith("/.claude-plugin/plugin.json") or lower == ".claude-plugin/plugin.json":
        return "Claude plugin manifest"
    if lower.endswith("/.codex-plugin/plugin.json") or lower == ".codex-plugin/plugin.json":
        return "Codex plugin manifest"
    if lower.endswith("/agents/openai.yaml") or lower == "agents/openai.yaml":
        return "OpenAI agent metadata"
    if re.fullmatch(r"requirements([-.][a-z0-9_-]+)?\.txt", filename):
        return "Python requirements"
    if filename in MANIFEST_NAMES:
        return MANIFEST_NAMES[filename]
    if filename in {
        "cargo.lock",
        "composer.lock",
        "go.sum",
        "package-lock.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "uv.lock",
        "yarn.lock",
    }:
        return "dependency lockfile"
    if filename in {"manifest.json", "plugin.json"}:
        return "plugin manifest"
    if filename in {"dockerfile", "makefile", "setup.cfg", "setup.py"}:
        return "build/install descriptor"
    return None


def _collect_path_evidence(result: Inventory, rel: str) -> None:
    path = Path(rel)
    lower_parts = [part.lower() for part in path.parts]
    for integration in sorted(INTEGRATION_DIRS.intersection(lower_parts)):
        _append_unique(
            result.integration_paths,
            EvidenceRecord(integration, rel, f"file under {integration}/"),
        )

    manifest = _manifest_category(rel)
    if manifest:
        _append_unique(result.manifests, EvidenceRecord(manifest, rel, "detected"))

    if path.name.lower().startswith(LICENSE_PREFIXES):
        _append_unique(result.licenses, EvidenceRecord("file", rel, "license file"))

    filename = path.name.lower()
    if "agents" in lower_parts and filename == "openai.yaml":
        _append_unique(
            result.compatibility,
            EvidenceRecord("platform", rel, "OpenAI Codex metadata"),
        )
    if ".codex-plugin" in lower_parts:
        _append_unique(
            result.compatibility,
            EvidenceRecord("platform", rel, "OpenAI Codex plugin"),
        )
    if ".claude" in lower_parts or ".claude-plugin" in lower_parts or filename == "claude.md":
        _append_unique(
            result.compatibility,
            EvidenceRecord("platform", rel, "Claude configuration"),
        )
    if filename == "gemini.md" or ".gemini" in lower_parts:
        _append_unique(
            result.compatibility,
            EvidenceRecord("platform", rel, "Gemini instructions"),
        )


def _dependency_from_requirement(
    requirement: str, group: str, path: str
) -> Optional[DependencyRecord]:
    value = requirement.strip().strip("'\"")
    if not value or value.startswith(("#", "-")):
        return None
    value = value.split(" #", 1)[0].strip()
    direct_match = re.match(r"^([A-Za-z0-9_.-]+(?:\[[^]]+\])?)\s*@\s*(.+)$", value)
    if direct_match:
        return DependencyRecord(direct_match.group(1), "@ " + direct_match.group(2), group, path)
    match = re.match(r"^([A-Za-z0-9_.-]+(?:\[[^]]+\])?)(.*)$", value)
    if not match:
        return DependencyRecord(value, "", group, path)
    return DependencyRecord(match.group(1), match.group(2).strip(), group, path)


def _parse_package_json(text: str, rel: str, result: Inventory) -> None:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return
    if not isinstance(data, dict):
        return

    dependency_groups = {
        "dependencies": "runtime",
        "devDependencies": "development",
        "optionalDependencies": "optional",
        "peerDependencies": "peer",
    }
    for field_name, group in dependency_groups.items():
        declared = data.get(field_name, {})
        if isinstance(declared, dict):
            for name, specification in declared.items():
                _append_unique(
                    result.dependencies,
                    DependencyRecord(str(name), str(specification), group, rel),
                )

    license_value = data.get("license")
    if isinstance(license_value, str):
        _append_unique(result.licenses, EvidenceRecord("declared", rel, license_value))

    engines = data.get("engines", {})
    if isinstance(engines, dict):
        for name, constraint in engines.items():
            _append_unique(
                result.compatibility,
                EvidenceRecord("runtime", rel, f"{name} {constraint}"),
            )
    for field_name, category in (("os", "operating system"), ("cpu", "architecture")):
        values = data.get(field_name, [])
        if isinstance(values, str):
            values = [values]
        if isinstance(values, list):
            for value in values:
                _append_unique(
                    result.compatibility,
                    EvidenceRecord(category, rel, str(value)),
                )


def _toml_section(text: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^\[{re.escape(name)}\]\s*$\n(.*?)(?=^\[|\Z)",
        text,
    )
    return match.group(1) if match else ""


def _fallback_toml_array(section: str, key: str) -> List[str]:
    match = re.search(rf"(?ms)^{re.escape(key)}\s*=\s*\[(.*?)\]", section)
    if not match:
        return []
    return re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))


def _fallback_pyproject(text: str) -> Dict[str, Any]:
    project_section = _toml_section(text, "project")
    project: Dict[str, Any] = {}
    python_match = re.search(r"(?m)^requires-python\s*=\s*['\"]([^'\"]+)['\"]", project_section)
    if python_match:
        project["requires-python"] = python_match.group(1)
    project["dependencies"] = _fallback_toml_array(project_section, "dependencies")
    license_match = re.search(
        r"(?m)^license\s*=\s*\{\s*text\s*=\s*['\"]([^'\"]+)['\"]",
        project_section,
    )
    if license_match:
        project["license"] = {"text": license_match.group(1)}

    optional_section = _toml_section(text, "project.optional-dependencies")
    optional = {}
    for key, values in re.findall(r"(?ms)^([A-Za-z0-9_.-]+)\s*=\s*\[(.*?)\]", optional_section):
        optional[key] = re.findall(r"['\"]([^'\"]+)['\"]", values)
    project["optional-dependencies"] = optional
    return {"project": project}


def _load_toml(text: str, fallback_pyproject: bool = False) -> Dict[str, Any]:
    if tomllib is not None:
        try:
            data = tomllib.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception:  # malformed untrusted input; report manifest without parsing
            return {}
    return _fallback_pyproject(text) if fallback_pyproject else {}


def _parse_pyproject(text: str, rel: str, result: Inventory) -> None:
    data = _load_toml(text, fallback_pyproject=True)
    project = data.get("project", {}) if isinstance(data, dict) else {}
    if not isinstance(project, dict):
        project = {}

    for requirement in project.get("dependencies", []) or []:
        dependency = _dependency_from_requirement(str(requirement), "runtime", rel)
        if dependency:
            _append_unique(result.dependencies, dependency)
    optional = project.get("optional-dependencies", {}) or {}
    if isinstance(optional, dict):
        for group, requirements in optional.items():
            if isinstance(requirements, list):
                for requirement in requirements:
                    dependency = _dependency_from_requirement(
                        str(requirement), f"optional:{group}", rel
                    )
                    if dependency:
                        _append_unique(result.dependencies, dependency)

    requires_python = project.get("requires-python")
    if requires_python:
        _append_unique(
            result.compatibility,
            EvidenceRecord("runtime", rel, f"python {requires_python}"),
        )
    license_value = project.get("license")
    if isinstance(license_value, str):
        _append_unique(result.licenses, EvidenceRecord("declared", rel, license_value))
    elif isinstance(license_value, dict):
        detail = license_value.get("text") or license_value.get("file")
        if detail:
            _append_unique(result.licenses, EvidenceRecord("declared", rel, str(detail)))

    build_system = data.get("build-system", {}) if isinstance(data, dict) else {}
    if isinstance(build_system, dict):
        for requirement in build_system.get("requires", []) or []:
            dependency = _dependency_from_requirement(str(requirement), "build", rel)
            if dependency:
                _append_unique(result.dependencies, dependency)


def _parse_requirements(text: str, rel: str, result: Inventory) -> None:
    for line in text.splitlines():
        dependency = _dependency_from_requirement(line, "runtime", rel)
        if dependency:
            _append_unique(result.dependencies, dependency)


def _parse_go_mod(text: str, rel: str, result: Inventory) -> None:
    in_require_block = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("go "):
            _append_unique(
                result.compatibility,
                EvidenceRecord("runtime", rel, line),
            )
            continue
        if line == "require (":
            in_require_block = True
            continue
        if in_require_block and line == ")":
            in_require_block = False
            continue
        requirement = line[len("require ") :] if line.startswith("require ") else line if in_require_block else ""
        requirement = requirement.split("//", 1)[0].strip()
        parts = requirement.split()
        if len(parts) >= 2:
            _append_unique(
                result.dependencies,
                DependencyRecord(parts[0], parts[1], "runtime", rel),
            )


def _parse_cargo_toml(text: str, rel: str, result: Inventory) -> None:
    data = _load_toml(text)
    package = data.get("package", {}) if isinstance(data, dict) else {}
    if isinstance(package, dict):
        if package.get("rust-version"):
            _append_unique(
                result.compatibility,
                EvidenceRecord("runtime", rel, f"rust {package['rust-version']}"),
            )
        if package.get("license"):
            _append_unique(
                result.licenses,
                EvidenceRecord("declared", rel, str(package["license"])),
            )
    for field_name, group in (
        ("dependencies", "runtime"),
        ("dev-dependencies", "development"),
        ("build-dependencies", "build"),
    ):
        dependencies = data.get(field_name, {}) if isinstance(data, dict) else {}
        if isinstance(dependencies, dict):
            for name, value in dependencies.items():
                specification = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
                _append_unique(
                    result.dependencies,
                    DependencyRecord(str(name), str(specification), group, rel),
                )


def _parse_manifest(record: FileRecord, text: str, result: Inventory) -> None:
    filename = Path(record.path).name.lower()
    if filename == "package.json":
        _parse_package_json(text, record.path, result)
    elif filename == "pyproject.toml":
        _parse_pyproject(text, record.path, result)
    elif re.fullmatch(r"requirements([-.][a-z0-9_-]+)?\.txt", filename):
        _parse_requirements(text, record.path, result)
    elif filename == "go.mod":
        _parse_go_mod(text, record.path, result)
    elif filename == "cargo.toml":
        _parse_cargo_toml(text, record.path, result)


def _scan_install_surfaces(record: FileRecord, text: str) -> List[EvidenceRecord]:
    surfaces = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for category, pattern in INSTALL_SURFACE_PATTERNS:
            if pattern.search(line):
                surfaces.append(
                    EvidenceRecord(category, record.path, line.strip()[:160], line_number)
                )
    return surfaces


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _safe_read(path: Path, root: Path, max_file_bytes: int) -> Tuple[Optional[str], Optional[str]]:
    try:
        metadata = path.lstat()
    except OSError as exc:
        return None, f"cannot stat: {exc.strerror or exc}"

    if stat.S_ISLNK(metadata.st_mode):
        return None, "symbolic link"
    if not stat.S_ISREG(metadata.st_mode):
        return None, "not a regular file"
    if metadata.st_size > max_file_bytes:
        return None, f"exceeds {max_file_bytes}-byte read limit"

    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        return None, "resolves outside repository"

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(str(path), flags)
        with os.fdopen(descriptor, "rb") as handle:
            payload = handle.read(max_file_bytes + 1)
    except OSError as exc:
        return None, f"cannot read: {exc.strerror or exc}"

    if len(payload) > max_file_bytes:
        return None, f"exceeds {max_file_bytes}-byte read limit"
    if b"\x00" in payload:
        return None, "binary file"
    return payload.decode("utf-8", errors="replace"), None


def _scan_findings(record: FileRecord, text: str) -> List[Finding]:
    source_kind = "executable" if record.kind == "script" else "documentation"
    findings = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for category, pattern in SUSPICIOUS:
            if pattern.search(line):
                findings.append(
                    Finding(
                        category=category,
                        path=record.path,
                        line=line_number,
                        snippet=line.strip()[:160],
                        source_kind=source_kind,
                    )
                )
    return findings


def scan_repository(root: Path, max_file_bytes: int = DEFAULT_MAX_FILE_BYTES) -> Inventory:
    """Safely collect a deterministic inventory of *root*."""
    root_path = Path(root).expanduser().resolve(strict=True)
    if not root_path.is_dir():
        raise ValueError(f"not a directory: {root}")

    result = Inventory(root=str(root_path))

    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True, followlinks=False):
        current = Path(dirpath)
        kept_dirs = []
        for dirname in sorted(dirnames):
            child = current / dirname
            rel = _relative(child, root_path)
            if child.is_symlink():
                result.skipped.append(SkippedRecord(rel, "symbolic link"))
            elif dirname in SKIP_DIRS:
                result.skipped.append(SkippedRecord(rel, "excluded directory"))
            else:
                kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in sorted(filenames):
            path = current / filename
            rel = _relative(path, root_path)
            _collect_path_evidence(result, rel)
            try:
                metadata = path.lstat()
            except OSError as exc:
                result.skipped.append(
                    SkippedRecord(rel, f"cannot stat: {exc.strerror or exc}")
                )
                continue

            executable = bool(metadata.st_mode & 0o111) and stat.S_ISREG(metadata.st_mode)
            ext = path.suffix.lower()
            text, reason = _safe_read(path, root_path, max_file_bytes)
            if executable:
                result.executables.append(
                    FileRecord(rel, 0, metadata.st_size, "executable", executable=True)
                )
            if reason:
                result.skipped.append(SkippedRecord(rel, reason))
                continue
            assert text is not None

            is_skill = filename.lower() == "skill.md"
            is_document = is_skill or ext in DOC_EXTS
            is_script = ext in SCRIPT_EXTS or text.startswith("#!")
            is_manifest = _manifest_category(rel) is not None
            kind = (
                "skill"
                if is_skill
                else "script"
                if is_script
                else "manifest"
                if is_manifest
                else "document"
                if is_document
                else "text"
            )
            name = description = None
            if is_skill:
                name, description = parse_frontmatter(text)
            record = FileRecord(
                path=rel,
                lines=len(text.splitlines()),
                size=metadata.st_size,
                kind=kind,
                executable=executable,
                name=name,
                description=description,
            )
            result.scanned_files.append(record)
            if is_skill:
                result.skills.append(record)
            if is_document:
                result.documents.append(record)
            if is_script:
                result.scripts.append(record)
            if is_manifest:
                _parse_manifest(record, text, result)
            result.install_surfaces.extend(_scan_install_surfaces(record, text))
            result.findings.extend(_scan_findings(record, text))

    for collection in (
        result.scanned_files,
        result.skills,
        result.scripts,
        result.executables,
        result.documents,
        result.skipped,
        result.findings,
        result.integration_paths,
        result.manifests,
        result.dependencies,
        result.licenses,
        result.compatibility,
        result.install_surfaces,
    ):
        collection.sort(
            key=lambda item: (
                item.path,
                getattr(item, "line", 0),
                getattr(item, "category", ""),
                getattr(item, "name", ""),
            )
        )
    return result


def render_inventory(result: Inventory) -> str:
    """Render the inventory as concise, human-readable text."""
    lines = [f"=== INVENTORY: {Path(result.root).name} ===", ""]
    lines.append(f"Skills found: {len(result.skills)}")
    for item in result.skills:
        lines.append(f"  [{item.lines:>5} lines] {item.path}")
        lines.append(f"          name: {item.name or '(no name)'}")
        lines.append(f"          desc: {item.description or '(no description)'}")

    lines.extend(["", f"Scripts: {len(result.scripts)}"])
    for item in result.scripts:
        lines.append(f"  [{item.lines:>5} lines] {item.path}")

    lines.extend(["", f"Executable files: {len(result.executables)}"])
    for item in result.executables:
        lines.append(f"  {item.path}")

    document_lines = sum(item.lines for item in result.documents)
    lines.extend(
        [
            "",
            f"Documentation: {len(result.documents)} files, {document_lines} lines",
        ]
    )

    lines.extend(["", f"Integration surfaces: {len(result.integration_paths)}"])
    for item in result.integration_paths:
        lines.append(f"  [{item.category}] {item.path}")

    lines.extend(["", f"Manifests and lockfiles: {len(result.manifests)}"])
    for item in result.manifests:
        lines.append(f"  [{item.category}] {item.path}")

    lines.extend(["", f"Declared dependencies: {len(result.dependencies)}"])
    for item in result.dependencies:
        specification = f" {item.specification}" if item.specification else ""
        lines.append(
            f"  [{item.group}] {item.name}{specification} ({item.path})"
        )

    lines.extend(["", f"License evidence: {len(result.licenses)}"])
    for item in result.licenses:
        lines.append(f"  [{item.category}] {item.path}: {item.detail}")

    lines.extend(["", f"Compatibility evidence: {len(result.compatibility)}"])
    for item in result.compatibility:
        lines.append(f"  [{item.category}] {item.detail} ({item.path})")

    lines.extend(
        ["", f"Install and permission surfaces: {len(result.install_surfaces)}"]
    )
    for item in result.install_surfaces:
        lines.append(
            f"  [{item.category}] {item.path}:{item.line}: {item.detail}"
        )

    lines.extend(
        [
            "",
            "Audit coverage:",
            f"  Text files inspected: {len(result.scanned_files)}",
            f"  Skipped paths: {len(result.skipped)}",
        ]
    )
    for item in result.skipped:
        lines.append(f"  {item.path}: {item.reason}")

    lines.extend(
        [
            "",
            f"=== SUSPICIOUS-PATTERN SCAN: {len(result.findings)} hit(s) ===",
            "Leads for in-context review, not proof of safety.",
        ]
    )
    for item in result.findings:
        lines.append(
            f"  [{item.category}] {item.path}:{item.line}: {item.snippet}"
        )
    if not result.findings:
        lines.append("No suspicious behavior found in the inspected text files.")
    return "\n".join(lines) + "\n"


def main(argv: List[str]) -> int:
    if len(argv) != 2 or not os.path.isdir(argv[1]):
        print(__doc__)
        return 1
    try:
        result = scan_repository(Path(argv[1]))
    except (OSError, ValueError) as exc:
        print(f"inventory error: {exc}", file=sys.stderr)
        return 1
    print(render_inventory(result), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
