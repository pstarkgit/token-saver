#!/usr/bin/env python3
"""End-to-end installer test in a throwaway HOME.

Run it through a managed temp workspace, never against a real HOME:

    managed-tmp-run --prefix tsbuild -- python3 tests/sandbox_test.py

(Elsewhere, any empty directory works: SANDBOX_DIR=/some/empty/dir.)
For each harness, and for all of them together, it proves: a dry run writes
nothing; install writes; status is OK; a second install changes nothing;
uninstall restores the HOME tree byte for byte (files, modes, symlinks, dirs).
"""
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get("MANAGED_TMP_DIR") or os.environ.get("SANDBOX_DIR") or
            sys.exit("run under managed-tmp-run (or set SANDBOX_DIR to an empty dir)"))
REAL_HOME = os.path.expanduser("~")
HARNESSES = ["kiro-cli", "kiro-ide", "kiro-crew", "claude-code", "codex", "cursor"]
results = []


def snapshot(home):
    snap = {}
    for dirpath, dirnames, filenames in os.walk(home):
        for n in dirnames + filenames:
            p = Path(dirpath) / n
            rel = str(p.relative_to(home))
            st = p.lstat()
            if p.is_symlink():
                snap[rel] = ("link", os.readlink(p))
            elif p.is_dir():
                snap[rel] = ("dir", oct(st.st_mode))
            else:
                snap[rel] = ("file", oct(st.st_mode), hashlib.sha256(p.read_bytes()).hexdigest())
    return snap


def run(home, *args, extra=None, cwd=None):
    env = {"HOME": str(home), "PATH": os.environ["PATH"], "SHELL": "/bin/zsh", "LANG": "C.UTF-8"}
    env.update(extra or {})
    env = {k: v for k, v in env.items() if v is not None}
    r = subprocess.run([sys.executable, str(KIT / "install"), *args], env=env, capture_output=True, text=True,
                       cwd=cwd)
    return r.returncode, r.stdout + r.stderr


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f"  [{detail}]" if detail and not ok else ""))


def diff(a, b):
    keys = sorted(set(a) | set(b))
    return [k for k in keys if a.get(k) != b.get(k)][:8]


def make_home(label, seeded, crew=False):
    home = ROOT / f"home-{label}"
    shutil.rmtree(home, ignore_errors=True)
    home.mkdir()
    assert str(home) != REAL_HOME and str(home).startswith(str(ROOT))
    if seeded:
        # Pre-existing files a real user has: the kit must adopt or restore them.
        (home / ".codex").mkdir()
        (home / ".codex" / "AGENTS.md").write_text("# My Codex rules\n\nUse tabs.\n@~/.codex/RTK.md")
        (home / ".codex" / "RTK.md").write_text("Run `rtk git status` instead of `git status`.\n")
        (home / ".kiro" / "steering").mkdir(parents=True)
        (home / ".kiro" / "steering" / "rtk.md").write_text("---\ninclusion: always\n---\nUse `rtk grep`.\n")
        (home / ".kiro" / "skills").mkdir()
        (home / ".claude" / "rules").mkdir(parents=True)
        (home / ".claude" / "CLAUDE.md").write_text("Be kind.\n")
        (home / ".zshenv").write_text("export EDITOR=vi\n")
        (home / ".zshenv").chmod(0o640)
        (home / ".bashrc").write_text("alias ll='ls -l'\n")
    if crew:
        (home / ".kiro" / "crew").mkdir(parents=True)
    return home


def lifecycle(label, harness_args, seeded, crew=False, install_extra=()):
    home = make_home(label, seeded, crew)
    s0 = snapshot(home)
    rc, out = run(home, "install", *harness_args, *install_extra)
    check(f"{label}: dry-run install writes nothing", rc == 0 and "DRY RUN" in out and snapshot(home) == s0, out[-300:])
    rc, out = run(home, "install", *harness_args, *install_extra, "--apply")
    s1 = snapshot(home)
    check(f"{label}: install --apply", rc == 0 and s1 != s0, out[-300:])
    rc, out = run(home, "status", *harness_args)
    check(f"{label}: status OK", rc == 0 and "DRIFT" not in out and "not installed" not in out, out[-400:])
    rc, out = run(home, "install", *harness_args, "--apply")
    check(f"{label}: re-install is a no-op", rc == 0 and "No changes." in out and snapshot(home) == s1,
          out[-300:])
    rc, out = run(home, "doctor")
    check(f"{label}: doctor OK", rc == 0 and "doctor: OK" in out, out[-300:])
    rc, out = run(home, "uninstall", *harness_args)
    check(f"{label}: dry-run uninstall writes nothing", rc == 0 and snapshot(home) == s1, out[-300:])
    rc, out = run(home, "uninstall", *harness_args, "--apply")
    s2 = snapshot(home)
    check(f"{label}: uninstall restores HOME byte for byte", rc == 0 and s2 == s0, f"{diff(s0, s2)} {out[-200:]}")
    return home


def main():
    for h in HARNESSES:
        lifecycle(f"{h}-seeded", ["--harness", h], True)
        lifecycle(f"{h}-empty", ["--harness", h], False)
    lifecycle("all-seeded", ["--harness", "all"], True)
    lifecycle("all-empty", ["--harness", "all"], False)
    lifecycle("all-seeded-shellenv", ["--harness", "all"], True, install_extra=["--shell-env"])
    lifecycle("all-empty-shellenv", ["--harness", "all"], False, install_extra=["--shell-env"])
    lifecycle("kiro-cli-crew-host", ["--harness", "kiro-cli"], True, crew=True)

    # B1: kiro-cli alone on a Kiro Crew host must not turn levels on for Crew sessions.
    home = make_home("b1", True, crew=True)
    run(home, "install", "--harness", "kiro-cli", "--apply")
    steer = (home / ".kiro/steering/token-saver.md").read_text()
    check("B1: crew host, kiro-cli only: Crew lines say off",
          "Kiro Crew sessions: Caveman (reply length) is off" in steer
          and "Kiro Crew sessions: Ponytail (code size) is off" in steer, steer)
    check("B1: crew host, kiro-cli only: lite line excludes Crew-run sessions",
          "Kiro CLI sessions that Kiro Crew did not start: Caveman (reply length) is lite" in steer
          and "\n- Caveman (reply length) is lite" not in steer and "only the Kiro Crew lines below apply" in steer,
          steer)
    home = make_home("b1-nocrew", True)
    run(home, "install", "--harness", "kiro-cli", "--apply")
    steer = (home / ".kiro/steering/token-saver.md").read_text()
    check("B1: no crew on host: single unlabelled lite line", "\n- Caveman (reply length) is lite" in steer
          and "Kiro Crew" not in steer, steer)

    # M1: an unwritable target folder is caught before anything is written.
    home = make_home("m1-readonly", True)
    (home / ".cursor").mkdir()
    (home / ".cursor").chmod(0o555)
    s0 = snapshot(home)
    rc, out = run(home, "install", "--harness", "all", "--apply")
    check("M1: read-only ~/.cursor refused before any write", rc == 2 and "not writable" in out and snapshot(home) == s0,
          out[-400:])
    (home / ".cursor").chmod(0o755)
    # M1: a failure partway still leaves a manifest that uninstall can use.
    home = make_home("m1-midfail", True)
    s0 = snapshot(home)
    rc, out = run(home, "install", "--harness", "all", "--shell-env", "--apply",
                  extra={"TOKEN_SAVER_TEST_FAIL_AFTER": "4"})
    man = home / ".local/share/token-saver/manifest.json"
    check("M1: failure partway reports an error and keeps a manifest", rc == 1 and "ERROR" in out and man.is_file()
          and "Traceback" not in out, out[-400:])
    rc, out = run(home, "uninstall", "--harness", "all", "--apply")
    check("M1: uninstall after a partial apply restores HOME", rc == 0 and snapshot(home) == s0,
          f"{diff(s0, snapshot(home))} {out[-200:]}")

    # m1: HOME must be an existing absolute directory.
    cwd = ROOT / "m1-cwd"
    cwd.mkdir(exist_ok=True)
    for bad in ("", None, "relative/home", str(ROOT / "missing")):
        rc, out = run(ROOT, "install", "--harness", "kiro-cli", "--apply", extra={"HOME": bad}, cwd=cwd)
        check(f"m1: HOME={bad!r} refused cleanly", rc != 0 and "HOME must be" in out and "Traceback" not in out
              and not any(cwd.iterdir()), out[-200:])

    # m2: a HOME containing $ and spaces still sources env.sh.
    home = make_home("m2 $HOME dollar", False)
    run(home, "install", "--harness", "codex", "--shell-env", "--apply")
    zr = subprocess.run(["zsh", "-c", "echo $DO_NOT_TRACK"], env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
                        capture_output=True, text=True) if shutil.which("zsh") else None
    check("m2: rc line is shell-quoted", zr is None or zr.stdout.strip() == "1", zr and (zr.stdout + zr.stderr))
    run(home, "uninstall", "--harness", "all", "--apply")

    # m3: without --shell-env no shell startup file is touched.
    home = make_home("m3", True)
    before = (home / ".zshenv").read_bytes(), (home / ".bashrc").read_bytes()
    run(home, "install", "--harness", "all", "--apply")
    check("m3: shell rc files untouched by default",
          ((home / ".zshenv").read_bytes(), (home / ".bashrc").read_bytes()) == before)

    # m5: a target folder that resolves outside HOME is refused.
    home = make_home("m5", True)
    outside = ROOT / "m5-outside-skills"
    outside.mkdir(exist_ok=True)
    (home / ".claude/skills").symlink_to(outside)
    s0 = snapshot(home)
    rc, out = run(home, "install", "--harness", "claude-code", "--apply")
    check("m5: parent resolving outside HOME refused", rc == 2 and "outside HOME" in out and snapshot(home) == s0
          and not any(outside.iterdir()), out[-300:])

    # m7: status reports a conflicting path that contains spaces.
    home = make_home("m7 with spaces", True)
    run(home, "install", "--harness", "claude-code", "--apply")
    mp = home / ".local/share/token-saver/manifest.json"
    man = __import__("json").loads(mp.read_text())
    rule = str(home / ".claude/rules/token-saver.md")
    del man["owned"][rule]
    mp.write_text(__import__("json").dumps(man))
    rc, out = run(home, "status", "--harness", "claude-code")
    check("m7: status flags the exact path with spaces", rc == 1 and f"DRIFT {rule}" in out, out)

    # m9: CODEX_HOME is honoured.
    home = make_home("m9", True)
    alt = home / "alt-codex"
    alt.mkdir()
    (alt / "AGENTS.md").write_text("alt rules\n")
    s0 = snapshot(home)
    rc, _ = run(home, "install", "--harness", "codex", "--apply", extra={"CODEX_HOME": str(alt)})
    check("m9: block goes to $CODEX_HOME/AGENTS.md", rc == 0 and "token-saver:begin" in (alt / "AGENTS.md").read_text()
          and "token-saver" not in (home / ".codex/AGENTS.md").read_text())
    rc, _ = run(home, "uninstall", "--harness", "codex", "--apply", extra={"CODEX_HOME": str(alt)})
    check("m9: uninstall with CODEX_HOME restores HOME", rc == 0 and snapshot(home) == s0)

    # Installed file contents.
    home = make_home("content", True)
    run(home, "install", "--harness", "all", "--shell-env", "--apply")
    steer = (home / ".kiro/steering/token-saver.md").read_text()
    check("content: Kiro steering gives Kiro Crew caveman off and ponytail off",
          "Kiro Crew sessions: Caveman (reply length) is off" in steer
          and "Kiro Crew sessions: Ponytail (code size) is off" in steer, steer)
    check("content: Kiro steering gives Kiro CLI and IDE lite, outside Crew",
          "Kiro CLI and Kiro IDE sessions that Kiro Crew did not start: Caveman (reply length) is lite" in steer, steer)
    check("content: existing RTK rules adopted, not duplicated",
          "follow the existing RTK rule" in steer and
          "follow the existing RTK rule" in (home / ".codex/AGENTS.md").read_text())
    check("content: precedence line present", "Harness and user rules win" in steer)
    skill = home / ".kiro/skills/token-saver"
    check("content: skill links resolve to one installed copy",
          all((home / p / "token-saver" / "SKILL.md").is_file() for p in
              (".kiro/skills", ".claude/skills", ".agents/skills", ".cursor/skills"))
          and skill.is_symlink())
    check("m4: kiro-crew skips its own link when ~/.kiro/skills has one",
          not (home / ".kiro/crew/skills/token-saver").exists() and not (home / ".kiro/crew/skills/token-saver").is_symlink())
    nested = [p for p in skill.resolve().rglob("SKILL.md") if p != skill.resolve() / "SKILL.md"]
    check("content: no nested SKILL.md in the installed skill", not nested, str(nested))
    aw = (skill / "references/upstream/rtk/hooks/rtk-awareness.md").read_text()
    check("content: RTK escape command matches pinned binary", "`rtk proxy <cmd>`" in aw and "bypass" not in aw)
    cav = (skill / "references/upstream/caveman/skills/caveman/SKILL.upstream.md").read_text()
    check("content: caveman hook and alias lines neutralised",
          "Relay the hook" not in cav and "/caveman wenyan" not in cav and "Modified by token-saver" in cav)
    env = (home / ".local/share/token-saver/env.sh").read_text()
    check("content: telemetry env exported",
          all(s in env for s in ("RTK_TELEMETRY_DISABLED=1", "DO_NOT_TRACK=1", "CAVEMAN_TELEMETRY=0",
                                 "HEADROOM_BEACON=off", "HEADROOM_OFFLINE=1")))
    zr = subprocess.run(["zsh", "-c", "echo $RTK_TELEMETRY_DISABLED"], env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
                        capture_output=True, text=True) if shutil.which("zsh") else None
    check("content: a non-interactive zsh picks up the env", zr is None or zr.stdout.strip() == "1",
          zr and zr.stdout)

    # Level change rewrites the block, and uninstall still restores the original.
    rc, _ = run(home, "install", "--harness", "codex", "--caveman", "full", "--apply")
    agents = (home / ".codex/AGENTS.md").read_text()
    check("levels: codex caveman full", rc == 0 and "Caveman (reply length) is full" in agents)
    run(home, "uninstall", "--harness", "all", "--apply")
    check("levels: original AGENTS.md restored after level change",
          (home / ".codex/AGENTS.md").read_text() == "# My Codex rules\n\nUse tabs.\n@~/.codex/RTK.md")

    # A file the kit does not own is never overwritten.
    home = make_home("conflict", True)
    (home / ".claude/rules/token-saver.md").write_text("mine\n")
    s0 = snapshot(home)
    rc, out = run(home, "install", "--harness", "claude-code", "--apply")
    check("conflict: refuses to overwrite a file it does not own", rc == 2 and snapshot(home) == s0, out)

    # A user edit after install survives uninstall; the block goes, the backup stays.
    home = make_home("user-edit", True)
    run(home, "install", "--harness", "codex", "--apply")
    with open(home / ".codex/AGENTS.md", "a") as f:
        f.write("\nNew rule.\n")
    rc, out = run(home, "uninstall", "--harness", "codex", "--apply")
    text = (home / ".codex/AGENTS.md").read_text()
    check("user-edit: block removed, user line kept, warning shown",
          rc == 0 and "token-saver:begin" not in text and "New rule." in text and "WARNING" in out, out)

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
