#!/usr/bin/env python3
"""Repo checks that need no sandbox: vendored bytes, lock, skill, guard.

    python3 tests/test_repo.py

Set TOKEN_SAVER_PINS=/path/to/pins.json to also compare upstream.lock with the
auditor's pins file; the check skips when it is not set.
"""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import plistlib
import re
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
KIT = Path(__file__).resolve().parent.parent
LOCK = json.loads((KIT / "upstream.lock").read_text())


def load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class VendorTest(unittest.TestCase):
    def test_lock_has_four_pinned_repos(self):
        self.assertEqual(set(LOCK["repos"]), {"rtk", "headroom", "caveman", "ponytail"})
        for r in LOCK["repos"].values():
            self.assertRegex(r["sha"], r"^[0-9a-f]{40}$")

    def test_vendored_bytes_match_lock(self):
        listed = set()
        for r in LOCK["repos"].values():
            for f in r["files"]:
                listed.add(f["path"])
                data = (KIT / f["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), f["sha256"], f["path"])
        on_disk = {p.relative_to(KIT).as_posix() for p in (KIT / "vendor").rglob("*") if p.is_file()}
        self.assertEqual(on_disk, listed, "vendor/ holds exactly the cleared files")

    def test_license_files_kept(self):
        for name, r in LOCK["repos"].items():
            self.assertTrue(any(Path(f["path"]).name == "LICENSE" for f in r["files"]), name)
        for f in ("vendor/caveman/NOTICE", "vendor/caveman/TRADEMARKS.md", "vendor/headroom/NOTICE"):
            self.assertTrue((KIT / f).is_file(), f)

    @unittest.skipUnless(os.environ.get("TOKEN_SAVER_PINS"), "TOKEN_SAVER_PINS not set")
    def test_lock_matches_audit_pins(self):
        pins = json.loads(Path(os.environ["TOKEN_SAVER_PINS"]).read_text())
        for name, p in pins["repos"].items():
            r = LOCK["repos"][name]
            self.assertEqual(r["sha"], p["sha"], name)
            self.assertEqual(sorted((f["upstream_path"], f["sha256"]) for f in r["files"]),
                             sorted((f["path"], f["sha256"]) for f in p["cleared_files"]), name)


class SkillTest(unittest.TestCase):
    def test_frontmatter(self):
        text = (KIT / "skill" / "SKILL.md").read_text()
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        self.assertTrue(m)
        fm = m.group(1)
        name = re.search(r"(?m)^name: (.+)$", fm).group(1)
        conf = re.search(r"(?m)^NAME=(.+)$", (KIT / "kit.conf").read_text()).group(1)
        self.assertEqual(name, conf)
        self.assertRegex(name, r"^[a-z0-9-]{1,64}$")
        self.assertNotIn("caveman", name)
        self.assertIn("description:", fm)

    def test_derived_text_applies(self):
        mod = load(KIT / "install", "kit_install")
        files = mod.payload_files()
        self.assertIn("`rtk proxy <cmd>`", files["references/upstream/rtk/hooks/rtk-awareness.md"].decode())
        for rel, data in files.items():
            if rel != "SKILL.md":
                self.assertNotEqual(Path(rel).name, "SKILL.md", rel)
        self.assertFalse(any("megacave" in r for r in files), "megacave is never shipped")
        for rel in ("references/upstream/caveman/skills/caveman/SKILL.upstream.md",
                    "references/upstream/ponytail/skills/ponytail-review/SKILL.upstream.md",
                    "references/upstream/ponytail/skills/ponytail-audit/SKILL.upstream.md"):
            text = files[rel].decode()
            self.assertNotRegex(text, r"(?<![\w`])/(caveman|ponytail-review|ponytail-audit)\b(?!-)", rel)

    def test_no_secrets_or_internal_hosts(self):
        bad = re.compile(r"AKIA[0-9A-Z]{16}|aws_secret_access_key|\.corp\.|amazon\.com|a2z\.com|dev-dsk-|/local/home/")
        for p in KIT.rglob("*"):
            if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts and "vendor" not in p.parts and p.name != "test_repo.py":
                self.assertIsNone(bad.search(p.read_text(errors="ignore")), p)


class UpdateScheduleTest(unittest.TestCase):
    def test_launchd_runs_weekly(self):
        installer = load(KIT / "install", "kit_install_schedule_macos")
        job = plistlib.loads(installer.PLIST.format(
            name=installer.NAME, python="/usr/bin/python3",
            installer="/kit/install", log="/kit/update.log").encode())
        self.assertEqual(job["StartCalendarInterval"],
                         {"Weekday": 1, "Hour": 10, "Minute": 17})
        self.assertEqual(job["ProgramArguments"],
                         ["/usr/bin/python3", "/kit/install", "update", "--apply"])

    def test_cron_runs_weekly(self):
        installer = load(KIT / "install", "kit_install_schedule_cron")
        cron = installer.cron_line(Path("/kit/update.log"))
        self.assertEqual(cron.split()[:5], ["17", "10", "*", "*", "1"])
        self.assertIn("update --apply >> /kit/update.log", cron)


class HeadroomGuardTest(unittest.TestCase):
    def setUp(self):
        self.g = load(KIT / "bin" / "headroom-guard", "headroom_guard")
        self.tmp = tempfile.TemporaryDirectory()
        fake = Path(self.tmp.name) / "headroom"
        fake.write_text("#!/bin/sh\nexit 0\n")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        self.env = {"PATH": self.tmp.name, "HEADROOM_PROXY_TOKEN": "x" * 40, "AWS_REGION": "us-west-2",
                    "HEADROOM_HOST": "0.0.0.0", "HEADROOM_LICENSE": "k", "HEADROOM_API_KEY": "k",
                    "HEADROOM_ALLOW_UNAUTHENTICATED_BIND": "1", "HEADROOM_HF_PIN": "off",
                    "OPENAI_TARGET_API_URL": "https://example.invalid", "BEDROCK_TARGET_API_URL": "https://gw",
                    "HTTPS_PROXY": "http://example.invalid:3128"}

    def tearDown(self):
        self.tmp.cleanup()

    def test_off_without_flag(self):
        with self.assertRaises(SystemExit):
            self.g.build([], self.env)

    def test_fails_closed(self):
        for drop in ("HEADROOM_PROXY_TOKEN", "AWS_REGION"):
            env = dict(self.env)
            del env[drop]
            with self.assertRaises(SystemExit, msg=drop):
                self.g.build(["--enable-unverified"], env)
        with self.assertRaises(SystemExit):
            self.g.build(["--enable-unverified"], dict(self.env, PATH="/nonexistent"))

    def test_safe_command_and_env(self):
        cmd, env = self.g.build(["--enable-unverified"], self.env)
        self.assertEqual(cmd[1], "proxy")
        self.assertEqual(cmd[cmd.index("--host") + 1], "127.0.0.1")
        self.assertEqual(cmd[cmd.index("--backend") + 1], "bedrock")
        for flag in ("--no-telemetry", "--no-ccr", "--stateless"):
            self.assertIn(flag, cmd)
        for word in ("wrap", "init", "install", "learn", "--memory", "--learn"):
            self.assertNotIn(word, cmd)
        for k, v in {"HEADROOM_OFFLINE": "1", "DO_NOT_TRACK": "1", "HEADROOM_BEACON": "off",
                     "HEADROOM_TELEMETRY": "off", "HEADROOM_UPDATE_CHECK": "off",
                     "HEADROOM_PROXY_METRICS_REQUIRE_LOOPBACK": "true", "HEADROOM_BACKEND": "bedrock"}.items():
            self.assertEqual(env[k], v, k)
        for k in ("HEADROOM_HOST", "HEADROOM_LICENSE", "HEADROOM_API_KEY", "HEADROOM_ALLOW_UNAUTHENTICATED_BIND",
                  "HEADROOM_HF_PIN", "BEDROCK_TARGET_API_URL", "HTTPS_PROXY"):
            self.assertNotIn(k, env)
        for k in self.g.NON_BEDROCK_URLS:
            self.assertEqual(env[k], "http://127.0.0.1:9", k)

    def test_endpoint_and_trust_overrides_dropped(self):
        bad = {k: "https://example.invalid" for k in (
            "AWS_ENDPOINT_URL", "AWS_ENDPOINT_URL_BEDROCK_RUNTIME", "AWS_BEDROCK_RUNTIME_ENDPOINT",
            "AWS_CONFIG_FILE", "LITELLM_API_BASE", "LITELLM_PROXY_API_BASE", "WSS_PROXY", "wss_proxy",
            "PYTHONPATH", "PYTHONSTARTUP", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "SSL_CERT_DIR",
            "AWS_CA_BUNDLE", "CURL_CA_BUNDLE", "NODE_EXTRA_CA_CERTS")}
        cmd, env = self.g.build(["--enable-unverified"], dict(self.env, **bad))
        for k in bad:
            self.assertNotIn(k, env)
        self.assertEqual(env["AWS_IGNORE_CONFIGURED_ENDPOINT_URLS"], "true")

    def test_region_validated(self):
        for region in ("evil.example.com/", "us-west-2.evil.com", "US-WEST-2", "us-west-2/", "", "us-west-123"):
            with self.assertRaises(SystemExit, msg=region):
                self.g.build(["--enable-unverified", "--region", region], self.env) if region else \
                    self.g.build(["--enable-unverified"], dict(self.env, AWS_REGION=region))
            with self.assertRaises(SystemExit, msg=region):
                self.g.build(["--enable-unverified"], dict(self.env, AWS_REGION=region))
        for region in ("us-west-2", "eu-central-1", "ap-southeast-2", "us-gov-west-1"):
            cmd, env = self.g.build(["--enable-unverified", "--region", region], self.env)
            self.assertEqual(cmd[cmd.index("--region") + 1], region)
            self.assertEqual(env["AWS_REGION"], region)

    def test_flag_not_abbreviated(self):
        with self.assertRaises(SystemExit):
            self.g.build(["--enable"], self.env)


if __name__ == "__main__":
    unittest.main(verbosity=2)
