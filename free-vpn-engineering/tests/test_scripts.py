import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from client import make_config, normalize_host
from common import read_env, write_private, valid_path
from init_env import create
from healthcheck import check

PASSWORD = 'TEST_ONLY_9nx2Tz4F7c6V3a8B0m5W1rQ'


class ClientTests(unittest.TestCase):
    def test_default_tls_and_loopback(self):
        conf = make_config('demo.onrender.com', PASSWORD)
        self.assertEqual(conf['inbounds'][0]['listen'], '127.0.0.1')
        self.assertEqual(conf['outbounds'][0]['network'], 'tcp')
        self.assertTrue(conf['outbounds'][0]['tls']['enabled'])
        self.assertFalse(conf['outbounds'][0]['tls']['insecure'])
        self.assertEqual(conf['route']['final'], 'render-trojan')
        self.assertNotIn('direct', [x['type'] for x in conf['outbounds']])

    def test_no_plaintext_remote(self):
        with self.assertRaises(ValueError):
            make_config('demo.onrender.com', PASSWORD, plaintext=True)

    def test_local_plaintext_only(self):
        conf = make_config('127.0.0.1', PASSWORD, plaintext=True, port=10000)
        self.assertNotIn('tls', conf['outbounds'][0])

    def test_host_validation(self):
        for host in ('https://demo.onrender.com', 'user:pass@host', '-bad.host', 'a..com', 'host/path', '127.0.0.1:443'):
            with self.subTest(host=host), self.assertRaises(ValueError):
                normalize_host(host)
        self.assertEqual(normalize_host('DEMO.onrender.com'), 'demo.onrender.com')

    def test_path_validation(self):
        for path in ('/', '//evil', '/tunnel?x=y', '/healthz', '/assets/status.js'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                valid_path(path)

    def test_no_weak_password(self):
        with self.assertRaises(ValueError):
            make_config('demo.onrender.com', 'short')

    def test_private_file_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private.json'
            write_private(path, '{}\n')
            if os.name == 'posix':
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            with self.assertRaises(FileExistsError):
                write_private(path, 'overwritten')

    def test_init_env(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            create(path)
            values = read_env(path)
            self.assertGreaterEqual(len(values['TROJAN_PASSWORD']), 40)
            valid_path(values['WS_PATH'])
            json.dumps(make_config('demo.onrender.com', values['TROJAN_PASSWORD'], values['WS_PATH']))

    def test_read_env_does_not_execute(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('VALUE=$(do-not-execute)\n')
            self.assertEqual(read_env(path)['VALUE'], '$(do-not-execute)')

    def test_monitor_rejects_unsafe_url(self):
        for url in ('http://example.com', 'https://user:pass@example.com', 'https://example.com?token=secret', 'https://example.com/path'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                check(url)


if __name__ == '__main__':
    unittest.main()
