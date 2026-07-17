# Chinese Public Copy Rewild Design

## Goal

Rewrite the Chinese copy in `README.md` and `docs/index.html` so it reads like original Chinese written by a frank technical reviewer. Preserve the product's skeptical, direct personality without turning it into a personal blog or adding invented experiences.

## Scope

- Rewrite only the Chinese README section and Chinese landing-page strings.
- Keep all English prose unchanged, except the two public N−1 sentences in `README.md` and `docs/index.html`, which may be minimally revised to state `When a subagent is needed`.
- Keep links, commands, code, paths, product names, verdict icons, model examples, repository names, and measured numbers unchanged.
- Do not change skill behavior, installation instructions, or technical claims.

## Voice

The copy should sound confident because it names concrete evidence, not because it uses slogans. Favor ordinary verbs, varied sentence length, and occasional conversational turns. Keep the sharper phrases that fit the product, but remove translation-shaped wording, mechanical symmetry, and advertising filler. Do not add first-person anecdotes or sprinkle sentence particles where the technical context does not call for them.

## Rewild targets

Apply the Rewild-ZH checks with special attention to:

- C3: replace translated or nominalized phrasing with direct Chinese verbs.
- C5: remove unnecessary connective phrases and let adjacent sentences carry the logic.
- C6 and pattern 14: replace slogans and promotional abstractions with verifiable behavior.
- C9: use Chinese punctuation in Chinese prose while preserving code and URLs.
- Patterns 25, 27, and 29: vary sentence rhythm, reduce over-neat parallel lists, and avoid repetitive summary endings.

## Content treatment

The README remains the detailed source. It should explain the problem, deliverables, install gate, evaluation method, model-cost rule, safety boundary, installation, prompts, and benchmark. The landing page should express the same facts more tightly; it should not copy every README sentence verbatim.

Core terms stay consistent across both surfaces:

- 🟢 `值得安装`, 🟡 `只挑精华`, and 🔴 `别装`
- `删除测试` and `含金量测试`
- `N−1` as a dynamic one-tier reduction, with model names explicitly treated as examples
- `整个仓库`, `hooks`, `commands`, and `agents`, so the review scope stays explicit
- static review limits and the promise never to execute target code during inspection

## Fact boundaries

Both surfaces must retain the existing example and benchmark facts: `50+`, `2.1 万`, `200 万美元`, `install.sh:6`, `14/14`, `9/14`, `100%`, `64%`, `obra/superpowers`, and `anthropics/skills`. The rewrite may change surrounding syntax but may not strengthen those claims.

## Verification

- Add public-copy tests that extract the two Chinese surfaces, check protected facts and core terms, and reject common AI-writing phrases or half-width punctuation in Chinese prose outside code and URLs.
- Inspect the final diff to confirm English prose apart from those two N−1 sentences, plus links, commands, numbers, and product names, did not change.
- Run the full unit test suite and validate the HTML structure before committing.
