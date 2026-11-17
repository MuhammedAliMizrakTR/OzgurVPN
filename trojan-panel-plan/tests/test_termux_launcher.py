#!/usr/bin/env python3
"""Offline checks for the Termux/VDS launcher; never contacts GitHub or sudo."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
LAUNCHER = BASE / 'termux-yayin-baslat.sh'
PUBLISHER = BASE / 'mualiy-yayinla.py'
EXPECTED_SHA256 = 'c1501cb8dade1e8583f256b1f02dc2c69e02beb6f4ea603550ba59d42679ab17'


class TermuxLauncherTests(unittest.TestCase):
    def run_launcher(self, home, mode, source=PUBLISHER):
        fake_bin = home / 'bin'
        fake_bin.mkdir()
        curl = fake_bin / 'curl'
        curl.write_text('#!/bin/sh\ncat -- "$MUALIY_TEST_SOURCE"\n')
        curl.chmod(0o700)
        environment = dict(os.environ)
        environment.update({
            'HOME': str(home),
            'MUALIY_TEST_SOURCE': str(source),
            'PATH': str(fake_bin) + os.pathsep + environment['PATH'],
        })
        return subprocess.run(
            ['bash', str(LAUNCHER), mode],
            text=True,
            capture_output=True,
            env=environment,
            check=False,
        )

    def test_shell_syntax_and_pinned_source(self):
        subprocess.run(['bash', '-n', str(LAUNCHER)], check=True)
        text = LAUNCHER.read_text()
        self.assertIn("readonly SOURCE_COMMIT='8e52da1033b4971bc8a881e6601f8c3d38bb9e2e'", text)
        self.assertIn(EXPECTED_SHA256, text)
        self.assertIn('raw.githubusercontent.com/MuhammedAliMizrakTR/OzgurVPN/', text)
        self.assertIn("curl --proto '=https' --tlsv1.2", text)
        self.assertIn('exec sudo python3 "$DESTINATION" --apply', text)
        self.assertNotIn('curl |', text)
        self.assertNotIn('sha256sum --check --status - || true', text)

    def test_dry_run_verifies_publisher_without_saving_or_sudo(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / 'home'
            home.mkdir()
            result = self.run_launcher(home, '--dry-run')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('DRY-RUN BASARILI', result.stdout)
            self.assertFalse((home / 'mualiy-yayinla.py').exists())

    def test_existing_unexpected_versioned_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / 'home'
            home.mkdir()
            target = home / 'mualiy-yayinla-c1501cb8.py'
            target.write_text('not the checksum-pinned publisher\n')
            result = self.run_launcher(home, '--dry-run')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('beklenen sabit kaynak degil', result.stderr)
            self.assertEqual(target.read_text(), 'not the checksum-pinned publisher\n')

    def test_legacy_unversioned_file_is_left_alone(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / 'home'
            home.mkdir()
            legacy = home / 'mualiy-yayinla.py'
            legacy.write_text('older manually transferred publisher\n')
            result = self.run_launcher(home, '--dry-run')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(legacy.read_text(), 'older manually transferred publisher\n')
            self.assertFalse((home / 'mualiy-yayinla-c1501cb8.py').exists())

    def test_apply_requires_tty_before_any_target_write(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / 'home'
            home.mkdir()
            result = self.run_launcher(home, '--apply')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pipe kullanma', result.stderr)
            self.assertFalse((home / 'mualiy-yayinla.py').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
