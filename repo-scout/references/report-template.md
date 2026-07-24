# Scout Report Template

Use this structure. Keep the whole report near half a page for a single target and under one page for a very large repository. Cut detail before cutting clarity: every dropped sentence should be one the reader would have skimmed anyway.

Write for a reader with no technical background — someone's mom or dad, busy, deciding whether this thing is worth their time. Every sentence must make sense to that reader on first pass. Write in the user's language and translate everything, including the verdict words; only the 🟢/🔴 icons, web links, and file paths stay as they are.

Plain-words rules for the whole report:

- No unexplained technical terms. When a real name is unavoidable (a program they must have, an account they must create), say what it is in everyday words in the same sentence.
- Describe benefits and drawbacks from the experience standpoint, never the technology standpoint: not "a self-hosted web service with persistent state" but "it runs on your own computer, remembers your past work, and your data never leaves your machine."
- No audit bookkeeping ever appears in the report: no commit hashes, resolution chains, snapshot or worktree state, symlink notes, file or line counts, and no lists of what was or wasn't read. All of that goes to the deep-dive notes.
- No numeric scores and no rubric axis names — the rubric is reasoning, never output.

The report contains no security commentary. The single exception is clear evidence of deliberate malice, which becomes the verdict's decisive reason on line one.

---

# Scout Report: <name>

**Verdict: 🟢 INSTALL | 🔴 SKIP** — <one sentence naming the decisive reason>

The verdict block is three to five short sentences in total, plain enough to read aloud. After the first line, cover: what this thing is in everyday words; the single biggest thing the user gets out of it (or, on 🔴, why it is not worth their time and what to use instead); whether it runs on their machine; and, when only part of it is worth having, one sentence saying what part is being set up and what is left out — a decision already made, never a question.

Verdict-line examples: `🟢 INSTALL — it really does what it promises, and it runs on your Mac.` · `🔴 SKIP — the author has abandoned this (no real updates in 8 months, and it depends on a service that no longer exists); use <alternative> instead.`

## What it is

Two or three sentences: what it does in everyday words, anchored to something familiar when that helps ("like the research mode in ChatGPT, but it runs on your own computer and shows its sources"). Then how it works at a high level in at most two plain sentences, hiding the machinery ("you type a question; it goes off and reads the web for a while, then hands you a written report"). No component names, no data-flow chains, no diagrams.

## Why you'd want it

Two to four short bullets: what gets easier, faster, better, or cheaper, and what makes this one special against the obvious alternative. Experience first, always — "you can close the laptop and it keeps working; the answer is waiting when you come back," never "asynchronous task persistence."

## Watch out for

At most two bullets, and only things that would genuinely change the user's week: real money it costs, accounts they must create, heavy upkeep, a rough or confusing experience, a core feature that doesn't match the marketing. Cosmetic issues, minor documentation mistakes, and normal signs of an actively developed project are never worth the reader's time. When nothing meets that bar, omit the section.

## On your machine

Answer "will this run for me, and how?" with one recommended way — never a menu.

- Whether it runs on this computer: what is already in place, what is missing, and the one-line command or step to get each missing piece with the user's package manager. If probing was impossible (no shell), say so plainly and keep the recommendation generic.
- Recommend exactly one way to run it, chosen by the experience rule and the effort rule (SKILL §Detect the environment): the full point-and-click experience whenever one exists, reached in the fewest user steps. When nothing graphical exists, say plainly: "there is no app window — you use this by typing commands."
- If running it takes several parts working at once, that is plumbing the user should never see: the plan is one start command or start-on-login, ending with one address to open or one icon to click — never terminal windows to keep open.
- Other documented setups get at most one sentence — "there are other ways to install it meant for developers; you don't need them" — with no list.
- What you must have first: accounts or keys in plain words, and what they cost when the project says.
- End with what success looks like: "when it's ready, a page opens in your browser at <address> and you'll see <what>."

Derive everything from the project's own install docs and files; describe, never execute during the audit. If the project's own instructions are unclear or wrong, say so in plain words — that is honest, report-worthy evidence.

Close the report with one line, `Source: <link>`, then follow the existing approval state (SKILL §Offer assisted installation). If the user's request was an audit only, add the single assisted-install offer, naming the one recommended way. If the user gave an imperative install, setup, or adoption request, do not ask again; continue with the approved installation after the report. No offer after an unapproved 🔴.

## The deep dive — researched, never volunteered

The sections above are the entire visible report. The audit still produces the developer-level material; keep it ready and print none of it. When the user says **"deep dive"** — or "advanced info", "deeper info", or otherwise clearly asks for developer-level detail — reply with it in full:

- The mechanism traced properly: one concrete run from trigger to output — state, handoffs, verification, completion.
- The active ingredients and the filler: which components survive the removal test, which are decoration.
- A 10-minute reading map: 2–4 real file paths in reading order, each with what to notice.
- Worth stealing: 2–4 reusable design patterns.
- Compatibility and ownership detail: platform constraints, dependencies, license, install footprint, maintenance evidence, context cost.
- Audit bookkeeping: exact revision, the resolution chain, worktree or content-hash state, and what was left unread or sampled.

Never advertise that this level exists; the reader who needs it knows the words.
