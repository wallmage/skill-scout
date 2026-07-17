# Chinese Public Copy Rewild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the public Chinese copy so it sounds native, direct, and human while preserving every technical fact and all English content.

**Architecture:** Treat `README.md` as the detailed source and `docs/index.html` as the shorter landing-page adaptation. A focused contract test extracts both Chinese surfaces, protects facts and terminology, and rejects common AI-writing phrases and half-width punctuation in Chinese prose.

**Tech Stack:** Markdown, static HTML, Python 3.9+ standard-library `unittest`.

## Global Constraints

- Modify only Chinese public copy plus its tests and design/plan documentation, except for the two public N−1 sentences in `README.md` and `docs/index.html`.
- Preserve all other English prose, links, commands, code, paths, product names, verdict icons, model examples, repository names, and measured numbers. The two N−1 sentences may only gain `When a subagent is needed` to match the skill's rule.
- Preserve `50+`, `2.1 万`, `200 万美元`, `install.sh:6`, `14/14`, `9/14`, `100%`, `64%`, `obra/superpowers`, and `anthropics/skills` on both Chinese surfaces.
- Keep 🟢 `值得安装`, 🟡 `只挑精华`, 🔴 `别装`, `删除测试`, `含金量测试`, `N−1`, `整个仓库`, `hooks`, `commands`, and `agents` consistent.
- Do not add anecdotes, statistics, capabilities, or safety guarantees.

---

### Task 1: Add Chinese public-copy contracts

**Files:**
- Create: `tests/test_public_copy.py`

**Interfaces:**
- Consumes: Chinese sections from `README.md` and `docs/index.html`.
- Produces: `README_CHINESE` and `LANDING_CHINESE` strings plus reusable prose-cleaning helpers inside the test module.

- [ ] **Step 1: Write the failing contract tests**

Create tests that:

```python
PROTECTED_FACTS = (
    "50+", "2.1 万", "200 万美元", "install.sh:6",
    "14/14", "9/14", "100%", "64%",
    "obra/superpowers", "anthropics/skills",
)
CORE_TERMS = (
    "值得安装", "只挑精华", "别装", "删除测试", "含金量测试", "N−1",
    "整个仓库", "hooks", "commands", "agents",
)
AI_PHRASES = (
    "值得注意的是", "综上所述", "总而言之", "此外",
    "在此基础上", "必须强调的是", "赋能", "深刻变革",
)
```

Extract the README text from `## 中文` to `## License`. Extract all Chinese `data-lang="zh"` content from the landing page, including header, main, and footer nodes without double-counting nested content. Remove fenced/preformatted code, inline code, URLs, Markdown/HTML tags, and HTML entities before checking prose punctuation. Assert that every protected fact and core term appears in both raw surfaces, every AI phrase is absent, and `[,;:?]` never touches a CJK character in cleaned prose.

- [ ] **Step 2: Run the tests to verify the current copy fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_public_copy -v
```

Expected: FAIL on half-width punctuation adjacent to Chinese text.

- [ ] **Step 3: Commit the contract tests**

```bash
git add tests/test_public_copy.py
git commit -m "test: define Chinese public copy contract"
```

### Task 2: Rewild the Chinese README

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the approved voice and fact boundaries in the design spec.
- Produces: the detailed Chinese public narrative used as the factual source for the landing page.

- [ ] **Step 1: Rewrite the Chinese README section**

Rewrite every prose paragraph, heading, list item, verdict description, prompt label, and benchmark explanation from `## 中文` to `## License`. Apply Rewild-ZH C3, C5, C6, C9, and rhythm checks. Keep code fences, URLs, exact names, numbers, and verdict meanings unchanged.

- [ ] **Step 2: Run the copy contract**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_public_copy -v
```

Expected: the README-specific fact and terminology assertions pass; any remaining failure points only to landing-page copy.

- [ ] **Step 3: Compare English and protected content with the baseline**

Run:

```bash
git diff 075a320 -- README.md
```

Expected: changes begin at `## 中文`, except for the English N−1 sentence; fenced commands, URLs, repository names, model examples, and benchmark numbers are unchanged.

### Task 3: Rewild the Chinese landing page

**Files:**
- Modify: `docs/index.html`

**Interfaces:**
- Consumes: the rewritten README's terminology and facts.
- Produces: a shorter Chinese landing-page adaptation with the same verdicts and claims.

- [ ] **Step 1: Rewrite Chinese header and main-page strings**

Rewrite the `data-lang="zh"` header copy, Chinese `<main>`, Chinese call-to-action labels, and Chinese footer. Keep HTML structure, classes, English nodes, code blocks, links, names, and numbers unchanged. Avoid copying long README sentences when the page can say the same thing more directly.

- [ ] **Step 2: Run the copy contract and parse the HTML**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_public_copy -v
python3 -c 'from html.parser import HTMLParser; from pathlib import Path; parser=HTMLParser(); parser.feed(Path("docs/index.html").read_text()); parser.close(); print("HTML parse OK")'
```

Expected: all public-copy tests pass and the parser prints `HTML parse OK`.

- [ ] **Step 3: Compare English and protected content with the baseline**

Run:

```bash
git diff 075a320 -- docs/index.html
```

Expected: only Chinese text nodes change, except for the English N−1 sentence; styles, scripts, links, HTML structure, product names, and measured facts remain unchanged.

### Task 4: Review, verify, and publish

**Files:**
- Modify if review requires it: `README.md`, `docs/index.html`

**Interfaces:**
- Consumes: completed copy and passing contracts.
- Produces: reviewed copy committed on `main` and pushed to `origin/main`.

- [ ] **Step 1: Run a Rewild-ZH review**

Scan both Chinese surfaces for C1–C7, punctuation, sentence-length monotony, excessive symmetry, promotional abstractions, and unsupported changes. Revise only identified problems.

- [ ] **Step 2: Run complete verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
unzip -t skill-scout.skill
git diff --check
git status --short
```

Expected: all tests pass, archive integrity passes, no whitespace errors appear, and status lists only the planned copy/test/plan changes.

- [ ] **Step 3: Commit the implementation**

```bash
git add README.md docs/index.html tests/test_public_copy.py docs/superpowers/specs/2026-07-17-chinese-copy-rewild-design.md docs/superpowers/plans/2026-07-17-chinese-copy-rewild.md
git commit -m "docs: make Chinese public copy sound natural"
```

- [ ] **Step 4: Fast-forward local main and push**

Fast-forward `/Users/wallny/Developer/skill-scout` from the verified worktree branch, rerun the full tests there, and push `main` to `origin`.
