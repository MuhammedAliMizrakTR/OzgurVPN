#!/usr/bin/env python3
"""Offline guards for fresh-panel reset scope; Docker and VDS are never used."""
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
SCRIPT = BASE / 'mualiy-sifirla-ve-yayinla.py'
PUBLISHER = BASE / 'mualiy-yayinla.py'
spec = importlib.util.spec_from_file_location('fresh_reset', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FreshResetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.panel = root / 'mualiy-sui'
        self.live = root / 'mualiy-sui-live'
        patcher = patch.multiple(m, ROOT=self.panel, LIVE=self.live)
        patcher.start()
        self.addCleanup(patcher.stop)

    def panel_tree(self):
        self.panel.mkdir()
        (self.panel / '.mualiy-managed').write_text(m.PANEL_MARKER + '\n')
        (self.panel / 'db').mkdir()
        (self.panel / 'cert').mkdir()
        (self.panel / 'compose.yaml').write_text('name: mualiy-sui\n')

    def live_tree(self):
        self.live.mkdir()
        (self.live / '.managed').write_text(m.LIVE_MARKER + '\n')

    def test_python_compiles_and_compose_is_loopback_only(self):
        compile(SCRIPT.read_text(), str(SCRIPT), 'exec')
        content = m.compose_content()
        self.assertIn('127.0.0.1:2095:2095/tcp', content)
        self.assertIn('127.0.0.1:2096:2096/tcp', content)
        self.assertNotIn('8443', content)
        self.assertIn('user: "10001:10001"', content)
        self.assertIn('no-new-privileges:true', content)

    def test_known_stopped_panel_is_accepted_for_archive(self):
        self.panel_tree()
        with patch.object(m, 'docker_ids', return_value=[]):
            self.assertIsNone(m.managed_panel())

    def test_unmarked_panel_is_not_archived(self):
        self.panel.mkdir()
        (self.panel / 'db').mkdir()
        (self.panel / 'cert').mkdir()
        (self.panel / 'compose.yaml').write_text('name: mualiy-sui\n')
        with patch.object(m, 'docker_ids', return_value=[]):
            with self.assertRaises(m.Stop):
                m.managed_panel()

    def test_known_panel_container_requires_exact_mounts(self):
        self.panel_tree()
        mounts = [
            {'Source': str(self.panel / 'db'), 'Destination': '/app/db'},
            {'Source': str(self.panel / 'cert'), 'Destination': '/app/cert'},
        ]
        with patch.object(m, 'docker_ids', return_value=['a' * 12]), \
             patch.object(m, 'load_json_docker', side_effect=[
                 {'com.docker.compose.service': 'panel'}, mounts,
             ]):
            self.assertEqual(m.managed_panel(), 'a' * 12)

    def test_tunnel_without_owned_live_state_is_refused(self):
        with patch.object(m, 'docker_ids', return_value=['b' * 12]):
            with self.assertRaises(m.Stop):
                m.managed_tunnel()

    def test_archive_moves_data_without_deleting_it(self):
        self.panel_tree()
        (self.panel / 'db' / 'keep').write_text('recoverable')
        m.archive(self.panel, 'panel')
        archives = list(Path(self.temporary.name).glob('mualiy-sui-reset-archive-*'))
        self.assertEqual(len(archives), 1)
        self.assertEqual((archives[0] / 'db' / 'keep').read_text(), 'recoverable')
        self.assertFalse(self.panel.exists())

    def test_admin_prompt_rejects_short_or_mismatched_passwords(self):
        with patch('builtins.input', return_value='panel-owner'), \
             patch.object(m.getpass, 'getpass', side_effect=['short', 'short']):
            with self.assertRaises(m.Stop):
                m.ask_admin()
        with patch('builtins.input', return_value='panel-owner'), \
             patch.object(m.getpass, 'getpass', side_effect=['A' * 12, 'B' * 12]):
            with self.assertRaises(m.Stop):
                m.ask_admin()

    def test_admin_prompt_accepts_twelve_character_password(self):
        with patch('builtins.input', return_value='panel-owner'), \
             patch.object(m.getpass, 'getpass', side_effect=['A1b2C3d4E5f6', 'A1b2C3d4E5f6']):
            self.assertEqual(m.ask_admin(), ('panel-owner', 'A1b2C3d4E5f6'))

    def test_local_api_constructs_cookie_opener(self):
        api = m.LocalAPI()
        self.assertEqual(api.base, 'http://127.0.0.1:2095/app/api/')
        self.assertIsNotNone(api.http)

    def test_reset_publisher_pin_matches_current_publisher(self):
        self.assertEqual(m.PUBLISHER_NAME, 'mualiy-yayinla-7e5d51de.py')
        self.assertEqual(m.PUBLISHER_SHA256, hashlib.sha256(PUBLISHER.read_bytes()).hexdigest())

    def test_no_secret_command_line_or_destructive_wildcard(self):
        source = SCRIPT.read_text()
        self.assertNotIn('cloudflare_api_token', source)
        self.assertNotIn('rm -rf', source)
        self.assertIn("subprocess.run(['/usr/bin/python3', str(publisher), '--apply']", source)
        self.assertIn("input('Sifirdan kurulum ve yayin icin SIFIRLA yaz: ')", source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
