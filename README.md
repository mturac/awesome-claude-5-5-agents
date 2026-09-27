# Awesome Claude 5.5 Agents [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)

![Terracotta starburst and a network of agent nodes on a cream field.](assets/claude55-hero.png)

Website: https://mturac.github.io/awesome-claude-5-5-agents/

> Developer setup for the Claude 5.5 family: skills, subagents, plugins, instruction files, hooks, migration tools, and eval harnesses.

Anthropic's launch post on 22 September 2026 introduces Claude Opus 5.5 as the first model in the 5.5 family and says Claude Sonnet 5.5 and Claude Haiku 5.5 will follow in the coming weeks. This list tracks setup that is specific to 5.5, or that has been checked against it. Videos, games, demos, and showcase apps are out of scope.

Star counts, SPDX license ids, and last-commit dates were read from the GitHub API on 2026-09-27. Commit dates are UTC. "No license" means the API returned no SPDX id.

## Contents

- [Migrating to 5.5](#migrating-to-55)
- [Official guides](#official-guides)
- [Migration tools](#migration-tools)
- [Skills](#skills)
- [Instruction files](#instruction-files)
- [Plugins and hooks](#plugins-and-hooks)
- [Evals](#evals)
- [Video & Creative](#video--creative)

## Migrating to 5.5

Claude Opus 5.5 uses the fixed model id `claude-opus-5-5`. The migration guide listed below says the API returns HTTP 400 for `thinking` values `{"type": "disabled"}` and `{"type": "enabled", "budget_tokens": N}`. Adaptive thinking is always on: omit `thinking`, or send `{"type": "adaptive"}`. The same page says `tool_choice` types `any` and `tool` return 400, including on the token-counting endpoint. `{"type": "auto"}` and `{"type": "none"}` are the accepted forms. Setting `temperature`, `top_p`, or `top_k` to any non-default value returns 400; the guide's path is to omit them. An assistant prefill at the end of `messages` is rejected.

On the Claude API and Google Cloud, a computer-use tool of type `computer_20251124` returns 400. The replacement is `computer_toolset_20260801`, with no computer-use beta header and no `name` or display size on the tool entry. On Amazon Bedrock, `computer_20251124` still works on Opus 5.5. The computer use tool entry below is the page that guide cites for the agent-loop changes.

Effort is the only request parameter that controls thinking depth. The guide lists five levels (`low`, `medium`, `high`, `xhigh`, `max`) and says the default is `medium`, where Claude Opus 5's default is `high`. The 1M-token context window is the default, and a context-window beta header for older models has no effect. Responses can begin with `thinking` blocks, so callers select blocks by `type`. In a tool-use loop, those blocks go back unmodified; edited, reordered, or partly dropped thinking blocks return 400. Thinking text is omitted by default (`thinking.display` defaults to `"omitted"`).

Thinking blocks are tied to the model and the conversation. The guide says that on the Claude API, Claude Fable 5.1 and Claude Mythos 5.1 read Opus 5.5 thinking blocks, and no other model does. Opus 5.5 reads thinking blocks from Claude Opus 5 and earlier Opus, Sonnet, and Haiku models, and does not read them from Claude Fable or Claude Mythos models. For accounts created on or after 31 August 2026, 00:00 UTC, replaying a thinking block after an edit to the system prompt, the tools, or earlier messages returns 400 by default.

The same guide documents `/claude-api migrate this project to claude-opus-5-5` for the bundled Claude API skill. The skill entry below records what the docs say and what the public skill tree still contains.

Getting the most out of Opus 5.5 (Addy Osmani, 22 September 2026, listed below) is about behavior in Claude and Claude Code, separate from those HTTP 400s. It says Opus 5.5 thinks before every reply, so lines such as "think carefully" can come out of prompts and saved instructions, and that effort is how you change thinking depth in Claude Code. It also shows a CLAUDE.md rule for when to continue and when to stop, splitting a large audit across subagents, and keeping the task list in a file so it survives context compaction.

## Official guides

- [Claude API skill](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/claude-api-skill) - Docs for the skill bundled with Claude Code. They say `/claude-api migrate this project to claude-opus-5-5` applies the model-id swap and breaking-parameter changes, asks for a scope before editing, and leaves a manual checklist. In [anthropics/skills](https://github.com/anthropics/skills) `skills/claude-api` (178585 stars, Apache-2.0 in that folder, no repository SPDX id, last commit 2026-09-24) the checked-in migration guide still targets `claude-opus-5` and does not mention Opus 5.5.
- [Computer use tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool#migrate-from-computer-20251124) - Tool reference linked from the migration guide. On the Claude API and Google Cloud, Opus 5.5 rejects `computer_20251124` and expects `computer_toolset_20260801`. Amazon Bedrock still accepts the older tool.
- [Effort parameter](https://platform.claude.com/docs/en/build-with-claude/effort#recommended-effort-levels-for-claude-opus-5-5) - Official control for thinking depth. Opus 5.5 supports `low`, `medium`, `high`, `xhigh`, and `max`, and defaults to `medium`.
- [Getting the most out of Opus 5.5](https://claude.dev/blog/getting-the-most-out-of-opus-5-5/) - Addy Osmani, 22 September 2026, on prompting, stop rules in CLAUDE.md, subagents, and a task file. Published on claude.dev.
- [Introducing Claude Opus 5.5](https://www.anthropic.com/claude-opus-5-5) - Launch post, 22 September 2026. Names Opus 5.5 as the first 5.5 model and says Sonnet 5.5 and Haiku 5.5 will follow in the coming weeks.
- [Migrating to Claude Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/migration-guide) - Request settings that return 400, thinking blocks on every response, and a checklist for each starting model.
- [Prompting Claude Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5) - Official prompting page. The migration guide sends readers here for prompts written when thinking could be turned off.
- [Spending your effort](https://claude.dev/blog/spending-your-effort/) - Thariq Shihipar, 25 September 2026, on picking an effort level in Claude Code. Examples cover Opus 5.5 and Fable 5.1; the level rules are the author's.
- [What's new in Claude Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/whats-new-opus-5-5) - Page the migration guide cites for feature support and for an explanation of each breaking change.

## Migration tools

- [model-bump](https://github.com/qiwei66/model-bump) - Local scan, plus a fake Opus 5.5 endpoint, for disabled thinking, forced tool choice, sampling parameters, and `computer_20251124`. No API key. The README says the recorded 400s come from the migration guide applied to captured framework payloads, not from the live API. 0 stars, MIT, last commit 2026-09-24.
- [prompt-fossils](https://github.com/stas4000/prompt-fossils) - Finds lines in CLAUDE.md, AGENTS.md, and skills that the author treats as harmful on current Claude models, including Opus 5.5. Default mode sends flagged lines to Jev; `--no-jev` stays on the machine. 2 stars, MIT, last commit 2026-09-23.

## Skills

- [opus-5-5-dev](https://github.com/ToroFelipe/opus-5-5-dev) - Claude Code skill for the long-run habits in the Opus 5.5 usage guide: a definition of done, TASKS.md, subagent audits, and a fixed end report. Copy it into `~/.claude/skills/`. English and Spanish. 1 star, MIT, last commit 2026-09-23.

## Instruction files

- [CLAUDE.md for Opus 5.5](https://github.com/amarakramali/CLAUDE.md-Opus-5.5) - Compact project CLAUDE.md for Claude Code, plus example task prompts. The author reports no measured gain. Documents `claude --model claude-opus-5-5 --effort medium` on Claude Code 2.1.280 or later. 1 star, MIT, last commit 2026-09-23.
- [lobotomized-claude-code](https://github.com/skrabe/lobotomized-claude-code) - System prompts rewritten against the Opus 5.5 and Fable 5.1 cards, then spliced into an installed Claude Code with a third-party tool. One prompt set is shared by every model. 121 stars, no license, last commit 2026-09-25.
- [Opus 5.5 developer guide](https://github.com/e1daru/opus-5-5-dev-guide) - Unofficial Claude Code walkthrough: setup, a prompt shape, a practice project, and starter CLAUDE.md files. Claims inside the guide are the author's, with links back to Anthropic docs. 0 stars, MIT, last commit 2026-09-26.

## Plugins and hooks

- [fable5-opus5.5-orchestrator](https://github.com/Rylaa/fable5-opus5.5-orchestrator) - Claude Code plugin that keeps Fable 5 in the chair and sends hard slices to Opus 5.5 at `high` or `xhigh`, never `max`. A hook flags when the chair does the work itself. The README CI badge points at `Rylaa/fable5-orchestrator`. 78 stars, MIT, last commit 2026-09-22.
- [opus55-longrun](https://github.com/smvlx/opus55-longrun) - Claude Code plugin that turns the official long-run guide into skills (`delegate`, `fleet-audit`, `merge-blockers`, and others) and two hooks. The destructive-command hook matches its phrases anywhere in the command text. 0 stars, MIT, last commit 2026-09-23.

## Evals

- [livenerf](https://github.com/ninjahawk/livenerf) - Daily drift check for Opus 5.5 after the 2026-09-22 launch, run through headless Claude Code. The README says the first results row comes after day 20 of the series. 45 stars, no license, last commit 2026-09-26.
- [vulcanbench-opus55-traces](https://github.com/morganlinton/vulcanbench-opus55-traces) - 115 redacted Claude Code traces from an Opus 5.5 sweep of VulcanBench Frontier v4 at five effort levels (22–24 September 2026). Task text, code, and assistant prose are withheld. Sweep code is the general [VulcanBench](https://github.com/morganlinton/VulcanBench) harness (86 stars, Apache-2.0, last commit 2026-09-26). 0 stars, no license, last commit 2026-09-26.

## Video & Creative

Star counts are cumulative repository totals, not Opus 5.5 adoption, and Higgsfield-style generative clips are not Claude-rendered.

- [brag](https://github.com/latent-spaces/brag) - Claude Code skill and plugin that turns a project or URL into a short launch video; its `/brag-slim` path is explicitly adapted for Claude Opus 5.5, while the classic path uses HyperFrames. 10154 stars, MIT, last commit 2026-09-24.
- [Claude Animation Skill](https://github.com/buildwithhanif/claude-animation-skill) - Claude plugin for hand-drawn 2D animation written as code, with Node canvas, frame-exact rendering, synthesized sound, and FFmpeg output. 14 stars, MIT, last commit 2026-09-23.
- [Claude Remotion Skill](https://github.com/haidrrrry/claude-remotion-skill) - Claude agent skill for creating and editing Remotion motion graphics with captions, B-roll, sound design, and a render-inspect-fix loop; it is model-agnostic rather than Opus-5.5-specific. 206 stars, MIT, last commit 2026-08-12.
- [Claude Video / Watch](https://github.com/bradautomates/claude-video) - Claude plugin and `/watch` skill that supplies timestamped frames and transcripts so an agent can inspect video; it is an input and analysis utility, not a renderer. 17713 stars, MIT, last commit 2026-09-25.
- [Flick](https://github.com/Creatorberry/flick) - Claude Code plugin that turns a video, link, or transcript into approved scene-by-scene Remotion animations and lets the agent revise individual scenes. 263 stars, MIT, last commit 2026-08-26.
- [HyperFrames](https://github.com/heygen-com/hyperframes) - Agent-friendly HTML, CSS, and JavaScript framework whose skills plan, lint, preview, and deterministically render MP4 video through headless Chrome and FFmpeg; the repository lists Claude Code among supported agents. 53434 stars, Apache-2.0, last commit 2026-09-27.
- [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar) - Claude Code plugin and style kit with 39 code-drawn film styles and sample films that the repository says were made with Claude Opus 5.5; treat its sample films as author claims and note that the API returned no SPDX license. 210 stars, no license, last commit 2026-09-27.
- [Manim Skill (4-role pipeline)](https://github.com/vumichien/manim-skill) - Claude Code plugin that uses researcher, planner, implementer, and main roles to turn ideas, papers, or mathematics into rendered Manim videos with narration and captions. 6 stars, Apache-2.0, last commit 2026-05-19.
- [Manim Skill (plan, code, render)](https://github.com/Yusuke710/manim-skill) - Claude Code plugin that plans, codes, renders, and iterates Manim videos. 157 stars, MIT, last commit 2026-01-26.
- [Manim Skills (best practices)](https://github.com/adithya-s-k/manim_skill) - Agent skills for Manim Community Edition and ManimGL that provide tested animation guidance and examples; the repository documents installation for Claude and other coding agents, but has no Opus-5.5-specific evidence. 1122 stars, MIT, last commit 2026-01-23.
- [Papermotion](https://github.com/francozanardi/papermotion) - Experimental paper-cutout animation engine and agent skill with deterministic offline Chromium/FFmpeg rendering and self-checks; its README identifies several example films as made with Claude Opus 5.5. 1 star, MIT, last commit 2026-09-26.
- [Remotion](https://github.com/remotion-dev/remotion) - React-based video framework with an agent-era workflow and official Claude-facing skills; its repository points to a separate special Remotion license, while the GitHub API returned no SPDX id. 60657 stars, no license, last commit 2026-09-27.
- [Remotion Agent Skills](https://github.com/remotion-dev/skills) - Official Remotion Agent Skills for Claude Code and other coding agents, including skills for creating, rendering, captions, maps, and multimedia. 4730 stars, no license, last commit 2026-09-25.
- [Remotion Claude Code plugin](https://github.com/remotion-dev/claude-code-plugin) - Official Remotion Agent Skills plugin for Claude Code; the repository describes it as an internal package with no documentation, so use the documented skills repository for general installation guidance. 21 stars, no license, last commit 2026-09-25.
- [Riso Windowseat](https://github.com/sevenevesai/riso-windowseat) - Claude Code skill kit for deterministic single-HTML Canvas/Web Audio films, with craft docs, a render harness, frame inspection, and reusable procedural animation workflows. 231 stars, MIT, last commit 2026-09-25.
- [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft) - Agent skill that turns Claude Code or Codex into a Remotion motion-design studio with shot recipes, product-video templates, sound design, and a browser workbench; no Opus-5.5-specific user output was found. 9660 stars, Apache-2.0, last commit 2026-09-27.
- [video-use](https://github.com/browser-use/video-use) - Claude Code skill for editing supplied footage with transcript-driven cuts, captions, overlays, and self-evaluation; the latest commit is co-authored by Claude Opus 5.5, but the pixels are edits of user footage rather than model-generated video. 27348 stars, MIT, last commit 2026-09-24.

## Related Lists

Creative indexes, not developer setup. Linked so this list does not pretend they are absent.

- [Awesome Claude Opus 5.5 Videos](https://github.com/athemeroy/awesome-opus-5-5-videos) - Source-linked index of videos made with Opus 5.5. 197 stars, CC-BY-4.0, last commit 2026-09-27.
- [Awesome Claude Video](https://github.com/opusvideo/awesome-claude-video) - Curated collection of Claude Opus 5.5 videos and animations, with prompts and workflows. 90 stars, no license, last commit 2026-09-26.
- [awesome-opus-video-skills](https://github.com/ismoshushi/awesome-opus-video-skills) - Installable video-production skills. The maintainer marks some entries as naming Opus 5.5 and treats the rest as generic Claude skills. 1 star, MIT, last commit 2026-09-26.

## Contributing

Additions need a working link and a reason the item is specific to Claude 5.5, or a check that shows it runs on 5.5. See [CONTRIBUTING.md](CONTRIBUTING.md).

[![CC0](https://licensebuttons.net/p/zero/1.0/88x31.png)](https://creativecommons.org/publicdomain/zero/1.0/)

To the extent possible under law, mehmet turac has waived all copyright and related or neighboring rights to this work. The text is in [LICENSE](LICENSE).
