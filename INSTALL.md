# Installing skill-scout

skill-scout vets any agent-skill repo before you install it: verdict first (🟢 INSTALL / 🟡 CHERRY-PICK / 🔴 SKIP), mechanism explanation, the essential 20%, a 10-minute reading map, and a safety scan. It replies in whatever language you ask in.

The package is deliberately portable: plain markdown + one stdlib-only Python script. Only soft dependencies are `git` (or any way to download a repo) and `python3` (optional — the skill can inventory by hand without it).

---

## Claude Code / Claude Desktop (native skills)

Copy the folder into your personal skills directory:

```bash
cp -r skill-scout ~/.claude/skills/skill-scout
```

Done. It triggers automatically when you paste a skill-repo URL with "is this worth installing?", "thoughts?", or ask to install any skill/plugin — including as a pre-install gate. (Project-local alternative: `<your-project>/.claude/skills/skill-scout`. If you received a `skill-scout.skill` file instead, open it in Claude and click "Save skill".)

## OpenAI Codex CLI

Codex reads `AGENTS.md` for standing instructions. Put the folder somewhere stable, e.g. `~/agent-skills/skill-scout`, then add to `~/.codex/AGENTS.md` (global) or your project's `AGENTS.md`:

```markdown
## skill-scout — vet skill repos before installing
Whenever I paste a link to an agent-skill/plugin/prompt-pack repo and ask whether
it's worth installing (or ask you to install one), first read and follow
~/agent-skills/skill-scout/SKILL.md end to end, including its referenced files.
Never install before the verdict.
```

Optional: also save the SKILL.md body as a custom prompt (`~/.codex/prompts/skill-scout.md`) so you can invoke it explicitly with `/skill-scout <url>`.

## Kimi Code / OpenCode / Gemini CLI / other agent CLIs

Same pattern — these tools all read a standing-instructions markdown file (`AGENTS.md`, `GEMINI.md`, or equivalent context file):

1. Copy `skill-scout/` somewhere stable, e.g. `~/agent-skills/skill-scout`.
2. Add the same snippet as the Codex section above to the tool's instructions file, pointing at the SKILL.md path.

## Any chat-based LLM (no filesystem)

Paste the contents of `SKILL.md`, `references/rubric.md`, and `references/report-template.md` into the conversation (or a custom-instructions/system-prompt slot), then paste the repo URL. Without shell access the model can't clone, so also paste the repo's key files — or use a tool-enabled mode.

---

## Verifying it works

Paste a skill repo URL and ask "is this worth installing?" — you should get a report that *opens* with 🟢/🟡/🔴 and includes a "10-minute reading map" section with real file paths. If you ask in another language, the whole report should come back in that language.

## What it will never do

Run code from the repo it's judging, install anything before the verdict, or proceed with an install after a 🔴 safety finding. It treats the target repo strictly as data — including ignoring any instructions inside the repo aimed at the reviewing AI.
