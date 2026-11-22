# token-saver

One skill and one installer that bring four token-saving tools into the agent
harnesses you use: RTK, Headroom, Caveman and Ponytail. "token-saver" is a
working name; it is set once in `kit.conf`.

| Tool | Layer | What it does | Default |
|---|---|---|---|
| [RTK](https://github.com/rtk-ai/rtk) | Shell output | Condenses git, grep, ls, tree and log output before the agent reads it | On wherever `rtk` is on PATH |
| [Headroom](https://github.com/headroomlabs-ai/headroom) | Model API traffic | Local proxy that compresses prompts | Off. Bedrock route NOT VERIFIED |
| [Caveman](https://github.com/JuliusBrussee/caveman) | Agent replies | Shorter prose, same facts | Lite (off in Kiro Crew) |
| [Ponytail](https://github.com/DietrichGebert/ponytail) | Code changes | Smallest complete change: reuse, stdlib, no unrequested layers | Lite (off in Kiro Crew) |

One tool runs per layer. The kit never installs Caveman's CLI, proxy or hooks,
RTK's `rtk-proxy`, or any upstream installer, and it fetches nothing at
install time.

## Install

The installer needs Python 3.8+ and nothing else. Every command is a dry run
that prints a diff until you add `--apply`.

```sh
./install install --harness kiro-cli            # show what would change
./install install --harness kiro-cli --apply    # write it
./install status                                # what is installed, any drift
./install doctor                                # rtk binary, telemetry, duplicates
./install uninstall --harness kiro-cli --apply  # remove it again
```

One command per harness (add `--apply` to write):

| Harness | Command |
|---|---|
| Kiro CLI | `./install install --harness kiro-cli` |
| Kiro IDE | `./install install --harness kiro-ide` |
| Kiro Crew | `./install install --harness kiro-crew` |
| Claude Code | `./install install --harness claude-code` |
| Codex CLI | `./install install --harness codex` |
| Cursor | `./install install --harness cursor` |
| All six | `./install install --harness all` |

Kiro IDE and Cursor usually run on a laptop; run the installer there.

## Updating

`./install update` fetches the kit's own git clone and reports how far it is
behind its upstream branch. With `--apply` it fast-forwards and re-applies
every installed harness at its recorded levels, running the freshly pulled
installer for the re-apply. It refuses to touch a clone with local changes
and never merges a diverged clone (`--ff-only`).

```sh
./install update                       # dry run: how far behind, what would change
./install update --apply               # pull and re-apply
./install update --schedule --apply    # run Mondays at 10:17 local time
./install update --unschedule --apply  # remove the weekly job
```

The weekly job uses launchd on macOS or cron elsewhere. It logs to
`~/.local/share/token-saver/update.log` and is removed when you uninstall the
last harness. After updating to this version, rerun
`./install update --schedule --apply` to replace an existing daily job.
Scheduled updates follow the clone’s configured upstream branch (normally
`origin/main`), so treat a push to that branch as a release.

## What each harness gets

| Harness | Skill folder (symlink) | Always-on rule | RTK | Caveman | Ponytail | Headroom |
|---|---|---|---|---|---|---|
| Kiro CLI | `~/.kiro/skills/token-saver` | `~/.kiro/steering/token-saver.md` | yes | lite | lite | no: no base-URL setting |
| Kiro IDE | `~/.kiro/skills/token-saver` | `~/.kiro/steering/token-saver.md` | yes | lite | lite | no: no base-URL setting |
| Kiro Crew | `~/.kiro/crew/skills/token-saver`, or none when Kiro CLI or IDE already links `~/.kiro/skills` | `~/.kiro/steering/token-saver.md` | yes | off, opt in | off, opt in | no: drives Kiro CLI |
| Claude Code | `~/.claude/skills/token-saver` | `~/.claude/rules/token-saver.md` | yes | lite | lite | opt-in, NOT VERIFIED |
| Codex CLI | `~/.agents/skills/token-saver` | block in `$CODEX_HOME/AGENTS.md` (default `~/.codex`) | yes | lite | lite | opt-in, NOT VERIFIED |
| Cursor | `~/.cursor/skills/token-saver` | none: Cursor user rules live in its settings UI; the installer prints the text to paste | yes | lite | lite | no: Cursor calls models from its servers |

Each skill folder is a symlink to one installed copy at
`~/.local/share/token-saver/skill`. Kiro Crew sessions see both
`~/.kiro/skills` and `~/.kiro/crew/skills`, so when Kiro CLI or Kiro IDE is
installed the kiro-crew adapter adds no second link.

Kiro CLI, Kiro IDE and Kiro Crew all load `~/.kiro/steering`, so they share
one steering file. On a host that runs Kiro Crew (one with `~/.kiro/crew`),
that file always carries "Kiro Crew sessions" lines (off unless you installed
the kiro-crew adapter with other levels), and the Kiro CLI and IDE lines are
labelled "sessions that Kiro Crew did not start". Installing only kiro-cli
on such a host therefore leaves Caveman and Ponytail off in Crew sessions. If
Kiro Crew is installed later, `status` shows the steering file as DRIFT and
re-running install adds the Crew lines. The
paths come from each harness's documentation: Kiro
[skills](https://kiro.dev/docs/skills/) and
[steering](https://kiro.dev/docs/steering/), Kiro Crew `docs/skills.md`
(`~/.kiro/crew/skills`, steering shared with Kiro CLI),
Claude Code [skills](https://code.claude.com/docs/en/skills) and
[rules](https://code.claude.com/docs/en/memory),
Codex [skills](https://learn.chatgpt.com/docs/build-skills) (`$HOME/.agents/skills`),
and Cursor [skills](https://cursor.com/docs/skills).

Every install writes `~/.local/share/token-saver/env.sh`, which exports
`RTK_TELEMETRY_DISABLED=1`, `DO_NOT_TRACK=1`, `CAVEMAN_TELEMETRY=0` and the
Headroom telemetry switches. The installer does not touch shell startup files
unless you add `--shell-env`. With it, the installer adds a three-line block
that sources `env.sh` to `~/.zshenv` (zsh reads it for every shell, including
the non-interactive ones harnesses start) and to `~/.bashrc` when bash is in
use. Non-interactive `bash -c` does not read `~/.bashrc`, so for bash set
`BASH_ENV` to `~/.local/share/token-saver/env.sh` yourself. `--no-shell-env`
removes the block again. RTK v1.2.1 has telemetry off by default
(`rtk telemetry status`), so the variable is a second guard.

## Levels

```sh
./install install --harness codex --caveman full --ponytail off --apply
```

| Level | Caveman (replies) | Ponytail (code) |
|---|---|---|
| `off` | normal replies | normal coding |
| `lite` | Answer first, no filler or recaps, complete sentences | Build what was asked; name a smaller option in one line |
| `full` | Upstream `caveman` rules | Upstream `ponytail` rules |
| `ultra` | Upstream `ultracave` rules | Ponytail ultra: also questions unneeded parts of the request |

Lite is the default because the harness rules here ask for complete, readable
sentences. Upstream's `megacave` / `wenyan` mode is not shipped. At every
level, work reports, CR and PR text, commit messages, Slack, email, tickets
and anything sent to another person stay in full prose, and code, commands,
paths and errors are never shortened. Harness and user rules always win.
In a session you can also just say "caveman full", "stop caveman", "ponytail
lite" or "stop ponytail".

Upstream Caveman measures `/caveman` at about 3% shorter than plain "be
concise" and `/ultracave` at about 35% shorter, and its rules cost roughly
1,160 input tokens when loaded. The kit keeps the always-on rule near 300
tokens and loads the long text only through the skill. Savings in your
harness are not measured yet.

## Turning a tool off

| Tool | Off for good | Off for one session |
|---|---|---|
| RTK | take `rtk` off PATH (the skill then runs commands normally), or uninstall the kit | run commands without `rtk` |
| Caveman | `--caveman off` | "stop caveman" |
| Ponytail | `--ponytail off` | "stop ponytail" |
| Headroom | it is off; do not run `bin/headroom-guard` | Ctrl-C the guard |
| Everything | `./install uninstall --harness all --apply` | |

## Headroom

`bin/headroom-guard --enable-unverified` starts an already-installed
`headroom` proxy in the foreground on 127.0.0.1 with a required token, a
Bedrock-only upstream, every other upstream pointed at a dead loopback port,
and telemetry, update checks, model downloads and on-disk stores off. Without
the flag it refuses to start. It stays off by default because the Bedrock
route has not been proven end to end, and because at the pinned commit the
proxy does not check the token for loopback callers. The guard also drops AWS
endpoint, LiteLLM, Python and CA-bundle overrides and accepts only AWS-style
region names. You own the Headroom install: the guard runs the first
`headroom` on PATH and does not check it against the pinned commit or any
hash. Details: `skill/references/headroom.md`.

## Safety notes

- Dry run by default. `--apply` writes only the paths in the table above and
  the kit's own data folder, plus the shell startup block if you asked for
  `--shell-env`.
- `HOME` must be an existing absolute directory, and `CODEX_HOME`, when set,
  must be absolute. Otherwise the installer stops before writing.
- Existing files are never overwritten. If a path the kit wants already
  exists and the kit does not own it, the installer stops and writes nothing.
- Before writing, the installer checks that every target folder is writable
  and resolves inside `HOME` (or `$CODEX_HOME`). A folder that is read-only, or
  a symlink that points outside `HOME` (for example `~/.claude/skills` linked
  to a shared repo), stops the run before anything is written.
- The manifest is saved after every step. If a write still fails partway, the
  installer prints an error, the manifest lists what was written, and running
  the same command again or `uninstall` cleans up.
- An existing file the kit edits (`~/.codex/AGENTS.md`, `~/.zshenv`,
  `~/.bashrc`) is backed up first. Uninstall restores the original bytes and
  deletes the backup. If you edited the file after install, uninstall removes
  only the kit's block, keeps your edits and keeps the backup.
- The manifest at `~/.local/share/token-saver/manifest.json` lists every path
  the kit owns. Uninstall removes only those paths and the empty folders it
  created. The kit stores no prompt data.
- Existing RTK rules (`~/.kiro/steering/rtk.md`, `~/.codex/RTK.md`, an RTK
  line in `~/.claude/CLAUDE.md`) are adopted: the kit points to them and does
  not write a second RTK rule.
- `doctor` checks that `rtk` on PATH is a pinned v1.2.1 binary: the rtk-oss
  release builds (linux x86_64, macOS arm64) or the homebrew-core 1.2.1
  bottle. rtk-oss is the Apache-2.0 edition without the BUSL-licensed engine;
  never use the `rtk` or `rtk-proxy` editions. The kit never installs or
  replaces the binary.
- Cursor: keep "Sync Skills for Cloud Agents" off, so the skill stays on your
  machine. Cursor also reads `~/.claude/skills` and `~/.agents/skills`, so it
  may list the skill more than once.
- Kiro Crew sessions see `~/.kiro/skills` as well as `~/.kiro/crew/skills`.

## Upstream and licences

Selected upstream text is pinned by commit and file hash in `upstream.lock`
and copied byte for byte into `vendor/`. See
[third-party notices](THIRD_PARTY_NOTICES.md) for attribution and license details. When installed, four vendored files are copied with
small edits (a first-line notice says so): the RTK escape command is changed
to `rtk proxy` to match the pinned binary, and hook, slash-command and alias
lines are replaced in the Caveman and Ponytail text.

| Project | Repo | Pinned commit | Licence |
|---|---|---|---|
| RTK | rtk-ai/rtk | `b8cb15167268` (text); binary v1.2.1 (rtk-oss) | Apache-2.0 |
| Headroom | headroomlabs-ai/headroom | `ce0460cfa859` | Apache-2.0 |
| Caveman | JuliusBrussee/caveman | `a192894723a8` | Apache-2.0 (earlier parts MIT) |
| Ponytail | DietrichGebert/ponytail | `ebd8654c2c62` | MIT |

Caveman is a trademark of its author; see `vendor/caveman/TRADEMARKS.md`. This
kit is not affiliated with any of the four projects.

To refresh the vendored files from a new audited pins file:
`python3 scripts/vendor.py PINS.json` (run inside a throwaway temp workspace).

## Tests

```sh
python3 tests/test_repo.py      # vendored sha256, lock, skill, Headroom guard
python3 tests/sandbox_test.py   # every adapter in a throwaway HOME
```

`sandbox_test.py` refuses to run unless `MANAGED_TMP_DIR` or `SANDBOX_DIR`
names a throwaway directory. For each harness, and for all six together, it
checks that a dry run writes nothing, install writes, status is clean, a
second install changes nothing, and uninstall restores the HOME tree byte for
byte.

## Renaming

Change `NAME` in `kit.conf` and the `name:` line in `skill/SKILL.md`, after
running `./install uninstall --harness all --apply` with the old name.
