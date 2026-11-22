#!/usr/bin/env python3
"""Refresh vendor/ and upstream.lock from an audited pins.json.

Build-time only; the installer never fetches anything. Run it through the
managed temp runner so the clones live in a private workspace that is
cleaned up afterwards:

    managed-tmp-run --prefix tsvendor -- python3 scripts/vendor.py PINS.json

It fetches each repo at the pinned SHA, copies only the cleared files, checks
each sha256 against pins.json, and fails without writing if any differ.
A file named SKILL.md is stored as SKILL.upstream.md, so harnesses that scan
skill folders recursively never load upstream text as a separate skill.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent


def local_name(path):
    p = Path(path)
    return str(p.with_name("SKILL.upstream.md")) if p.name == "SKILL.md" else path


def main(pins_path):
    pins = json.loads(Path(pins_path).read_text())
    work = Path(os.environ.get("MANAGED_TMP_DIR") or sys.exit("run under managed-tmp-run"))
    staged, lock = {}, {"schema": 1, "source": "pins.json from the token-saver audit",
                        "pins_generated_utc": pins.get("generated_utc"), "repos": {}}
    for name, r in sorted(pins["repos"].items()):
        clone = work / name
        subprocess.run(["git", "init", "-q", str(clone)], check=True)
        subprocess.run(["git", "-C", str(clone), "fetch", "-q", "--depth", "1", r["repo"] + ".git", r["sha"]], check=True)
        subprocess.run(["git", "-C", str(clone), "checkout", "-q", "FETCH_HEAD"], check=True)
        head = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()
        if head != r["sha"]:
            sys.exit(f"{name}: fetched {head}, pinned {r['sha']}")
        files = []
        for f in r["cleared_files"]:
            data = (clone / f["path"]).read_bytes()
            got = hashlib.sha256(data).hexdigest()
            if got != f["sha256"]:
                sys.exit(f"{name}/{f['path']}: sha256 {got} != pinned {f['sha256']}")
            dest = f"vendor/{name}/{local_name(f['path'])}"
            staged[dest] = data
            files.append({"upstream_path": f["path"], "path": dest, "sha256": got})
        lock["repos"][name] = {"repo": r["repo"], "sha": r["sha"], "license": r["license"], "files": files}
    lock["binaries"] = json.loads((KIT / "scripts" / "binary-pins.json").read_text())
    shutil.rmtree(KIT / "vendor", ignore_errors=True)
    for dest, data in staged.items():
        (KIT / dest).parent.mkdir(parents=True, exist_ok=True)
        (KIT / dest).write_bytes(data)
    (KIT / "upstream.lock").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    print(f"vendored {len(staged)} files from {len(lock['repos'])} repos")


if __name__ == "__main__":
    main(sys.argv[1])
