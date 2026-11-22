# Headroom: off by default, NOT VERIFIED

Headroom (headroomlabs-ai/headroom) is a local proxy that compresses prompts
before they reach the model provider. The kit pins it in `upstream.lock`,
vendors only its LICENSE and NOTICE, and does not install it.

`bin/headroom-guard` in the kit checkout can start an already-installed
`headroom` proxy in the foreground with the kit's safety settings. It refuses
to run unless you pass `--enable-unverified`.

## Which harnesses

Claude Code and Codex only. Kiro CLI, Kiro IDE and Kiro Crew call the Kiro
service with their own protocol and have no model base-URL setting, so they
cannot route through any proxy. Cursor calls its model from Cursor's servers,
which cannot reach 127.0.0.1.

## What headroom-guard enforces

- `--host 127.0.0.1`, passed explicitly. Every `HEADROOM_*` variable from the
  caller's environment is dropped, including `HEADROOM_HOST`,
  `HEADROOM_LICENSE`, `HEADROOM_API_KEY`, `HEADROOM_HF_PIN` and
  `HEADROOM_ALLOW_UNAUTHENTICATED_BIND`.
- `HEADROOM_PROXY_TOKEN` of 32+ characters must be set.
- Bedrock only: `--backend bedrock` with an explicit region. No region, no
  start. `BEDROCK_TARGET_API_URL` is removed, and every non-Bedrock
  `*_TARGET_API_URL` points at `http://127.0.0.1:9`, where nothing listens.
- `HEADROOM_OFFLINE=1`, `DO_NOT_TRACK=1`, `HEADROOM_BEACON=off`,
  `HEADROOM_TELEMETRY=off`, `HEADROOM_UPDATE_CHECK=off`,
  `HEADROOM_PROXY_METRICS_REQUIRE_LOOPBACK=true`.
- `--no-telemetry --no-ccr --stateless`: no originals store, no memory, no
  learn, no files written. It never runs `headroom wrap`, `init`, `install` or
  `learn`.
- AWS endpoint overrides (`AWS_ENDPOINT_URL*`, `AWS_BEDROCK_RUNTIME_ENDPOINT`,
  `AWS_CONFIG_FILE`), `LITELLM_*`, `PYTHON*`, `WSS_PROXY` and CA-bundle
  variables are dropped, `AWS_IGNORE_CONFIGURED_ENDPOINT_URLS=true` is set,
  and the region must match `^[a-z]{2}(-gov)?-[a-z]+-\d{1,2}$`.
- You own the Headroom install. The guard runs the first `headroom` on PATH
  and does not check it against the pinned commit or any hash.
- `[ml]` (the Kompress model) is not offered: it needs a one-time model
  download from Hugging Face that the user must approve first.

## Why it stays off

1. The Bedrock route has not been run end to end. In Claude Code,
   `CLAUDE_CODE_USE_BEDROCK=1` bypasses the proxy, so Claude Code must switch
   to Anthropic mode against the proxy while the proxy signs Bedrock calls
   with your AWS credentials. Which Claude Code and Codex request routes the
   Bedrock backend covers is NOT VERIFIED.
2. At the pinned commit the proxy exempts loopback callers from the token
   (`headroom/proxy/models.py`: "Loopback callers are exempt"). Any process on
   the same host can reach 127.0.0.1 and spend the credentials the proxy
   holds. Use a profile limited to `bedrock:InvokeModel*` if you enable it.

## What would let it turn on

A sandbox run that proves Claude Code or Codex traffic reaches only Bedrock
through the guard, and either an upstream option that enforces the token for
loopback callers or a Unix-socket listener the clients can use.
