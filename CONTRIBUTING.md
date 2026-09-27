# Contributing

This list is developer setup for the Claude 5.5 family (Opus 5.5 now; Sonnet 5.5 and Haiku 5.5 when they ship). mehmet turac maintains it.

## What belongs here

- Skills, subagents, plugins, MCP servers, hooks, CLAUDE.md or AGENTS.md patterns, migration tools, and eval harnesses.
- The item is specific to Claude 5.5, or you checked that it runs on 5.5 and you say how.
- Official Anthropic docs when they document 5.5 behavior.

## What stays out

- Videos, games, demos, and showcase apps. Those already have their own lists.
- Generic Claude skills, MCP servers, or benchmarks that only mention 5.5 in passing.
- Leaked system prompts and session dumps.
- Items whose link does not return HTTP 200.
- Hype, and numbers that are not in the upstream README or the GitHub API.

## Entry format

One bullet, alphabetical within its section:

```text
- [Name](https://example.com) - What it is, and the caveat that matters. 12 stars, MIT, last commit 2026-09-27.
```

For a GitHub repository, read stars, the SPDX license id, and the latest commit date from the API on the day you open the pull request. Use "no license" when the API returns none. Commit dates are UTC. Official docs do not get star counts.

The description starts with a capital letter, ends with a period, and says what the thing does. If a claim is the author's measurement, say so.

## Pull requests

- Search the list first so you do not add a duplicate.
- Keep the new bullet in alphabetical order by the link text.
- Run `python3 scripts/link-check.py` and `npx --yes awesome-lint`.
- Refresh the star, license, and date fields on any GitHub entry you touch.
