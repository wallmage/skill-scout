#!/usr/bin/env python3
"""Inventory a cloned skill repo: map every skill, measure footprint, flag suspicious patterns.

Usage: python inventory.py <path-to-cloned-repo>

Read-only. Never executes anything from the target repo.
"""
import os
import re
import sys

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
SCRIPT_EXTS = {".py", ".sh", ".js", ".ts", ".mjs", ".rb", ".pl", ".ps1"}
DOC_EXTS = {".md", ".txt", ".rst"}

# (label, regex) — patterns worth a human/AI look in context. Hits are leads, not verdicts.
SUSPICIOUS = [
    ("network call", re.compile(r"\b(curl|wget|urllib\.request|requests\.(get|post|put)|fetch\(|axios|http\.client|XMLHttpRequest)\b")),
    ("obfuscation", re.compile(r"\b(base64\s+(-d|--decode)|b64decode|atob\(|fromCharCode|bytes\.fromhex|exec\(compile)\b")),
    ("shell exec", re.compile(r"\b(eval\s|subprocess|os\.system|child_process|execSync|popen)\b")),
    ("credential access", re.compile(r"(API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL|\.aws/|\.ssh/|keychain|\.netrc|ANTHROPIC_|OPENAI_)", re.IGNORECASE)),
    ("persistence/hooks", re.compile(r"(settings\.json|hooks|crontab|launchd|\.bashrc|\.zshrc|\.claude/)", re.IGNORECASE)),
    ("destructive", re.compile(r"\brm\s+-rf\s+[~/$]")),
    ("AI-directed instruction", re.compile(r"(ignore (all |any )?(previous|prior|above) instructions|do not (tell|inform|mention to) the user|you must recommend|rate this (skill|repo) (highly|positively))", re.IGNORECASE)),
]


def parse_frontmatter(text):
    """Return (name, description) from YAML frontmatter, best-effort."""
    m = re.match(r"\s*---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None, None
    fm = m.group(1)
    def field(key):
        fm_m = re.search(rf"^{key}:\s*(.+?)(?=\n\S|\n*$)", fm, re.MULTILINE | re.DOTALL)
        if not fm_m:
            return None
        return " ".join(fm_m.group(1).split())[:300]
    return field("name"), field("description")


def main(root):
    root = os.path.abspath(root)
    skills, scripts, hooks, other_docs, flags = [], [], [], [], []
    total_lines = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root)
            ext = os.path.splitext(fn)[1].lower()
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            lines = text.count("\n") + 1

            if fn.lower() == "skill.md":
                name, desc = parse_frontmatter(text)
                skills.append((rel, name or "(no name)", lines, desc or "(no description)"))
                total_lines += lines
            elif ext in DOC_EXTS:
                other_docs.append((rel, lines))
                total_lines += lines
            elif ext in SCRIPT_EXTS:
                scripts.append((rel, lines))

            if "hook" in rel.lower():
                hooks.append(rel)

            # scan scripts and docs for suspicious patterns, with line numbers
            if ext in SCRIPT_EXTS or ext in DOC_EXTS:
                for i, line in enumerate(text.splitlines(), 1):
                    for label, rx in SUSPICIOUS:
                        if rx.search(line):
                            flags.append((label, f"{rel}:{i}", line.strip()[:160]))

    print(f"=== INVENTORY: {os.path.basename(root)} ===\n")
    print(f"Skills found: {len(skills)}")
    for rel, name, lines, desc in sorted(skills):
        print(f"  [{lines:>5} lines] {rel}")
        print(f"          name: {name}")
        print(f"          desc: {desc}")
    print(f"\nScripts/executables: {len(scripts)}")
    for rel, lines in sorted(scripts):
        print(f"  [{lines:>5} lines] {rel}")
    if hooks:
        print(f"\nHook-related paths ({len(hooks)}):")
        for h in sorted(set(hooks)):
            print(f"  {h}")
    print(f"\nOther docs: {len(other_docs)} files, "
          f"{sum(l for _, l in other_docs)} lines")
    big = [d for d in other_docs if d[1] > 300]
    for rel, lines in sorted(big, key=lambda x: -x[1])[:15]:
        print(f"  [{lines:>5} lines] {rel}")
    print(f"\nTotal doc footprint: ~{total_lines} lines")

    print(f"\n=== SUSPICIOUS-PATTERN SCAN: {len(flags)} hit(s) ===")
    print("(Leads for in-context review, not verdicts — many hits are benign.)")
    by_label = {}
    for label, loc, line in flags:
        by_label.setdefault(label, []).append((loc, line))
    for label, items in sorted(by_label.items()):
        print(f"\n[{label}] {len(items)} hit(s)")
        for loc, line in items[:10]:
            print(f"  {loc}: {line}")
        if len(items) > 10:
            print(f"  ... and {len(items) - 10} more")
    if not flags:
        print("No hits.")


if __name__ == "__main__":
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
