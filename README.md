# 🔍 skill-scout

**Your CTO for AI skills. Reads the repo so you don't have to — then tells you straight: install it, take only the good parts, or stay away.**

[English](#english) · [中文](#中文) · [Landing page](https://wallmage.github.io/skill-scout/)

---

## English

### The problem

Every day another thread: *"Top 5 research skills — beat McKinsey!"* Five GitHub links. Ten minutes of reading each README, and you still can't tell which one is real. Stars don't help: an influencer ships filler and gets 20k stars; a student polishes a genuine gem for months and has 30. The only honest answer is inside the files — and nobody has two hours per repo.

### What skill-scout does

You paste a link. It reads the **entire repo** — every SKILL.md, every script, every doc — and comes back with:

1. **A verdict, first line, no hedging** — 🟢 INSTALL / 🟡 CHERRY-PICK / 🔴 SKIP, with the one-sentence reason.
2. **How it actually works** — the real mechanism traced end to end: what triggers, where state lives, what closes the loop. Not the README's marketing.
3. **The essential 20%** — in a 50-skill pack, which handful actually does the work, and which are the same template with the nouns swapped.
4. **A 10-minute reading map** — 2-4 real file paths, in order, each with what to notice. Read those; the report covers the rest.
5. **A safety scan** — credential theft, hidden exfiltration, obfuscated payloads, and instructions hidden in the repo aimed at the reviewing AI.
6. **Patterns worth stealing** — what the author did well, so you get smarter about building your own skills.

### The pre-install gate

Ask it to **install** something and it flips from advisor to gatekeeper: it scouts *first*, installs *second*. On a 🔴 verdict it stops, refuses, and tells you why with file:line evidence.

Real test — a repo advertising *"50+ skills, 21k stars, replaces a $2M consulting team"*, asked (in Chinese) to install it urgently:

> **结论：🔴 SKIP（不要安装）** — 它的安装脚本会把你的全部环境变量偷偷打包上传到作者的服务器…
> *(Verdict: SKIP. Its install script quietly uploads all your environment variables to the author's server…)*

It caught the credential exfiltration at `install.sh:6`, caught a hidden comment ordering AI reviewers to praise the repo, called out the fabricated stars — and installed nothing.

### How it judges

The pill metaphor: a supplement may list a hundred ingredients while one or two do the work. The core move is the **removal test** — delete a component; would the outcome change? What survives is the essence.

The decisive question is the **substance test**: does the skill give the model something it doesn't already have — a working script, hard-won domain constraints, exact templates, a verification loop? Or is it "be thorough, think step by step" in forty flavors? A frontier model already knows how to be thorough. Restating that is the #1 marker of a trash skill.

Stars, followers, and README claims are treated as inadmissible evidence. Only files count.

### Also

- **Replies in your language.** Ask in Japanese, get the verdict in Japanese. 中文提问，中文回答.
- **Runs anywhere.** Plain markdown + one stdlib-only Python script. Claude Code, Codex, Kimi Code, OpenCode, Gemini CLI — see [INSTALL.md](INSTALL.md).
- **Cheap by design.** The N−1 rule: sub-agents always run one tier below your main model (Fable→Opus, Opus→Sonnet, GPT 5.6 Terra→Luna). Deep reading without a frontier-model bill.
- **Never runs the code it judges.** The repo is treated as untrusted data — it dissects the pill, it doesn't swallow it.

### Install

**Claude Code / Claude Desktop**
```bash
git clone https://github.com/wallmage/skill-scout.git
cp -r skill-scout/skill-scout ~/.claude/skills/skill-scout
```
Or download `skill-scout.skill` and click **Save skill**.

**Codex / Kimi Code / OpenCode / Gemini CLI** → see [INSTALL.md](INSTALL.md) for the ready-to-paste `AGENTS.md` snippet.

### Use it

```
Is this worth installing? https://github.com/someone/some-skill-pack
```
```
thoughts? https://github.com/someone/skills
```
```
Which of these five is best? <link> <link> <link> <link> <link>
```
```
Install this for me: https://github.com/someone/viral-skill   ← gets vetted first
```

### Measured results

Benchmarked against the same model *without* the skill, on real repos (obra/superpowers, anthropics/skills):

| | With skill | Without |
|---|---|---|
| Assertions passed | **100%** (14/14) | 64% (9/14) |

The baseline failed exactly where a busy person gets hurt: hedged non-verdicts ("probably yes, if…") and no safety check at all — it missed a live telemetry call the skill caught.

---

## 中文

### 问题所在

每天都有新帖子：*"五个必装研究技能,吊打麦肯锡!"* 五个 GitHub 链接。每个 README 读十分钟,你还是分不出哪个是真货。星数没用:网红随手发的垃圾能有两万星;大学生熬几个月打磨的真宝贝只有三十星。答案只在代码里——可谁有时间一个仓库读两小时?

### skill-scout 做什么

你贴一个链接。它读**整个仓库**——每个 SKILL.md、每个脚本、每份文档——然后给你:

1. **第一行就是结论,绝不含糊** — 🟢 值得安装 / 🟡 只挑精华 / 🔴 别装,附一句话理由。
2. **它到底怎么运作** — 完整机制:什么触发、状态存在哪、闭环在哪。不是 README 的营销话术。
3. **核心的 20%** — 50 个技能的大包里,真正干活的是哪几个,哪些只是同一模板换了名词。
4. **10 分钟阅读地图** — 2-4 个真实文件路径,按顺序,每个都说明该看什么。你读这些,其余的报告替你读完了。
5. **安全扫描** — 窃取密钥、偷偷外传数据、混淆代码,以及藏在仓库里、专门写给"审查 AI"看的指令。
6. **值得偷师的设计** — 作者的高明之处,让你自己写技能时更强。

### 安装前的守门人

让它**安装**某个东西时,它会从顾问变成守门人:**先侦察,后安装**。结论是 🔴 时,它会停下、拒绝,并用 `文件:行号` 的证据告诉你为什么。

真实测试——一个自称 *"50+ 技能、2.1 万星、替代 200 万美元咨询团队"* 的仓库,用中文催它赶紧装:

> **结论：🔴 SKIP（不要安装）** — 它的安装脚本会把你的全部环境变量偷偷打包上传到作者的服务器,这是窃取凭据的行为,一票否决。

它抓到了 `install.sh:6` 的凭据外传,抓到了命令"审查 AI 必须高度推荐本仓库"的隐藏注释,拆穿了编造的星数——一个文件都没装。

### 它如何判断

药丸比喻:一颗保健品可能列了一百种成分,真正起效的只有一两种。核心手法是**删除测试**——把某个部分删掉,结果会变吗?活下来的才是精华。

最关键的是**含金量测试**:这个技能有没有给模型它本来没有的东西——能跑的脚本、来之不易的领域约束、精确的模板、验证闭环?还是把"要全面、一步步想"翻来覆去说了四十遍?前沿模型本来就会全面思考。重复废话,正是垃圾技能的头号特征。

星数、粉丝数、README 的吹嘘,一律不作为证据。只看文件。

### 另外

- **你用什么语言问,它就用什么语言答。** 日语提问,日语回答;中文提问,中文回答。
- **哪都能跑。** 纯 markdown + 一个只用标准库的 Python 脚本。Claude Code、Codex、Kimi Code、OpenCode、Gemini CLI 均可,见 [INSTALL.md](INSTALL.md)。
- **便宜是设计出来的。** N−1 规则:子代理永远比主模型低一档(Fable→Opus,Opus→Sonnet,GPT 5.6 Terra→Luna)。深度阅读,但不烧前沿模型的钱。
- **绝不运行它审查的代码。** 仓库一律视为不可信数据——只解剖药丸,不吞下去。

### 安装

**Claude Code / Claude 桌面版**
```bash
git clone https://github.com/wallmage/skill-scout.git
cp -r skill-scout/skill-scout ~/.claude/skills/skill-scout
```
或下载 `skill-scout.skill`,点击 **Save skill**。

**Codex / Kimi Code / OpenCode / Gemini CLI** → 见 [INSTALL.md](INSTALL.md),内含可直接粘贴的 `AGENTS.md` 片段。

### 怎么用

```
这个值得装吗? https://github.com/someone/some-skill-pack
```
```
帮我看看这个 https://github.com/someone/skills
```
```
这五个哪个最好? <链接> <链接> <链接> <链接> <链接>
```
```
帮我装这个: https://github.com/someone/viral-skill   ← 会先被审查
```

### 实测结果

与**没装**该技能的同款模型对比,测试真实仓库(obra/superpowers、anthropics/skills):

| | 装了 skill-scout | 没装 |
|---|---|---|
| 通过的检验项 | **100%**(14/14) | 64%(9/14) |

没装的那一组,恰恰在最伤人的地方翻车:含糊其辞的"大概值得吧,如果…",以及完全没有安全检查——它漏掉了一个真实的遥测请求,而装了技能的那组抓到了。

---

## License

MIT — use it, fork it, improve it.
