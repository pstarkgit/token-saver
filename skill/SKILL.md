---
name: token-saver
description: >
  Spend fewer tokens without losing accuracy. Use when running shell commands
  (route them through rtk), when the user asks for shorter answers ("caveman",
  "be brief", "terse", "fewer tokens") or for smaller code changes ("ponytail",
  "simplest solution", "yagni", "over-engineered"), or when the user asks to
  change or turn off a token-saver level.
---

# token-saver

This kit bundles four token-saving tools. Each one works on a different layer,
and only one tool runs on each layer.

| Layer | Tool | What it saves |
|---|---|---|
| Shell output the agent reads | RTK (`rtk`) | Input tokens from git, grep, ls, logs and test output |
| Model API traffic | Headroom | Off by default. Claude Code and Codex only. See "Headroom" below. |
| The agent's own replies | Caveman | Output tokens, through shorter prose |
| The agent's code changes | Ponytail | Output tokens and review effort, through smaller diffs |

## Precedence

Harness and user rules win. If a system prompt, steering file, project rule or
the user asks for something different from this skill, follow them, not this
skill. Caveman and Ponytail never override an explicit user requirement, a
security check, input validation, error handling that prevents data loss, or
required tests.

## 1. RTK: shell output

Run supported shell commands through `rtk` so their output reaches you
compressed:

- `rtk git status`, `rtk git diff`, `rtk git log`, `rtk ls`, `rtk grep`,
  `rtk find`, `rtk read <file>`. Run `rtk --help` for the full list.
- For an unfamiliar command, `rtk rewrite '<command>'` prints the RTK
  equivalent if one exists. Run that equivalent as a separate command.
- Use `rtk proxy <command>` when you need the exact original bytes, when the
  output is parsed by another program, or when the condensed output is empty,
  garbled or contradicts the exit status.
- If `rtk` is not on PATH, run commands normally and tell the user once.
- Treat condensed output as the complete result. Upstream's note on this is at
  `references/upstream/rtk/hooks/rtk-awareness.md`.

Do not run `rtk init`, `rtk-proxy`, `rtk claude`, or any RTK installer. The kit
does not install or replace the RTK binary.

## 2. Caveman: shorter replies

Levels: `off`, `lite`, `full`, `ultra`. The installed always-on rule names the
current level for this harness. The user can change it for the session by
saying, for example, "caveman full" or "stop caveman".

- `lite`: answer first. Skip greetings, restating the question, recaps,
  closing offers and filler words. Keep complete, readable sentences with
  explicit subjects. This is the kit default outside Kiro Crew.
- `full`: follow `references/upstream/caveman/skills/caveman/SKILL.upstream.md`.
- `ultra`: follow `references/upstream/caveman/skills/ultracave/SKILL.upstream.md`.
- The upstream `megacave` / `wenyan` mode is not shipped. Do not use it.

Always write in full, normal prose, at every level:

- `work_report` summaries, status reports and board text
- CR, PR and commit descriptions, code review comments
- Slack messages, email, tickets, and anything sent to another person
- Security warnings, irreversible-action confirmations, and questions or
  options you put to the user
- Code, comments, commands, paths, numbers and error text stay exact

The upstream text mentions hooks, slash commands, a status line, a CLI and
telemetry. None of those are part of this kit. Ignore those parts and use only
the writing rules.

## 3. Ponytail: smaller code changes

Levels: `off`, `lite`, `full`, `ultra`. The user can change the level by saying
"ponytail full" or "stop ponytail".

- `lite`: build what was asked. When a clearly smaller option exists, name it
  in one line and let the user pick.
- `full`: follow `references/upstream/ponytail/skills/ponytail/SKILL.upstream.md`.
- `ultra`: the same file, at its `ultra` level, which also questions parts of
  the request the need does not justify.

When the user asks you to review code for bloat, use the read-only prompts at
`references/upstream/ponytail/skills/ponytail-review/SKILL.upstream.md` and
`references/upstream/ponytail/skills/ponytail-audit/SKILL.upstream.md`.

At `full` and `ultra`, end the reply with Ponytail's closing line: what you
skipped or did not check, and any risk. Keep that line even when Caveman's
pre-send check trims recaps.

Ponytail is off by default in Kiro Crew, because Kiro Crew worker prompts
already carry the same "smallest complete change" rules. Do not apply both.

Ignore the upstream references to `/ponytail` sub-commands, band data, hooks or
plugins. They are not part of this kit.

## 4. Headroom

Headroom (a local prompt-compression proxy) is off by default and its Bedrock
route is NOT VERIFIED. Only the user starts it, with `bin/headroom-guard
--enable-unverified` from the kit checkout. Kiro harnesses cannot use it. If
the user asks about it, point them to `references/headroom.md`. Do not
install, start or configure Headroom yourself, and never run `headroom wrap`,
`init`, `install` or `learn`.

## Turning things off

- For this session: say "stop caveman", "stop ponytail", or run commands
  without `rtk`.
- For good: run `./install install --harness <name> --caveman off --ponytail off --apply`
  from the kit checkout, or `./install uninstall --harness <name> --apply`.
