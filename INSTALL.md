# Installing Repo Scout

`repo-scout` is an Agent Skill: English instructions, two reference files, OpenAI interface metadata, and one Python standard-library scanner. Python is optional because an agent can reproduce the inventory manually; Git or another source-download method is optional for the same reason.

Clone or download this repository first, then copy the inner `repo-scout/` directory to the location your agent discovers.

## Claude Code / Claude Desktop

Personal skill, available across projects:

```bash
mkdir -p ~/.claude/skills
cp -R repo-scout ~/.claude/skills/repo-scout
```

Project-only alternative:

```text
<project>/.claude/skills/repo-scout/SKILL.md
```

Claude Code detects changes inside an existing skills directory. Restart it if the top-level directory did not exist when the session began. If you received `repo-scout.skill`, open it in a supported Claude desktop surface and choose **Save skill**.

## OpenAI Codex

Personal skill, available across repositories:

```bash
mkdir -p ~/.agents/skills
cp -R repo-scout ~/.agents/skills/repo-scout
```

Project-only alternative:

```text
<project>/.agents/skills/repo-scout/SKILL.md
```

Invoke it explicitly with `$repo-scout`, or let Codex select it from the description. Codex normally detects skill changes automatically; restart if it does not appear. `agents/openai.yaml` supplies desktop UI metadata.

## Gemini CLI

Gemini CLI supports project Agent Skills under `.agents/skills/`:

```bash
mkdir -p <project>/.agents/skills
cp -R repo-scout <project>/.agents/skills/repo-scout
```

Start Gemini CLI from that project and ask it to use `repo-scout` on a repository URL.

## Other Agent Skills-compatible tools

Copy the directory to the tool's documented personal or project Agent Skills location. Discovery paths differ by product and version; prefer native `SKILL.md` discovery over an `AGENTS.md`, `GEMINI.md`, or custom-prompt shim. If the tool has no Agent Skills support, use the fallback below.

## Chat or agent without filesystem skill discovery

Attach or paste:

1. `repo-scout/SKILL.md`
2. `repo-scout/references/rubric.md`
3. `repo-scout/references/report-template.md`

Without filesystem and source-access tools, also provide the target repository files. Missing install-relevant files must cap the verdict at 🔴 SKIP FOR NOW.

## Verify the installation

Ask:

```text
Use repo-scout to audit https://github.com/example/example-skill before I install it.
```

The response should:

- Open with 🟢 INSTALL or 🔴 SKIP and a verdict block of three to five plain sentences; when value is partial, name the chosen scope and what is excluded.
- Answer, in plain language, what the target does, why you'd want it, at most two watch-outs, and the one recommended way to run it on your machine.
- Keep developer detail (the mechanism trace, reading map, revision bookkeeping) out of the reply until you ask for the "deep dive". Mention safety only if clear evidence of deliberate malice determines the verdict.
- Use the language of your request.

## Inspection boundary

During inspection, the skill never executes or installs target code, follows target symlinks, initializes submodules, or trusts repository instructions. After a 🟢 verdict it installs the scope it chose and returns to the installation workflow the user already authorized. After 🔴 it stops.
