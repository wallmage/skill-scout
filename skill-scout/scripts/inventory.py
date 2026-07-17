#!/usr/bin/env python3
"""Inventory an untrusted skill repository without executing its code.

Usage: python inventory.py <path-to-repository>

The scanner is read-only. It refuses symbolic links, bounds every file read,
and reports files it could not inspect.
"""

import ast
from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import stat
import sys
from typing import List, Optional, Pattern, Tuple


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
            kind = "skill" if is_skill else "script" if is_script else "document" if is_document else "text"
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
            if is_document or is_script:
                result.findings.extend(_scan_findings(record, text))

    for collection in (
        result.scanned_files,
        result.skills,
        result.scripts,
        result.executables,
        result.documents,
        result.skipped,
        result.findings,
    ):
        collection.sort(key=lambda item: (item.path, getattr(item, "line", 0)))
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
            f"Text files inspected: {len(result.scanned_files)}",
            f"Skipped paths: {len(result.skipped)}",
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
