#!/usr/bin/env python3
"""Opt-in, non-root, loopback-only S-UI API + authenticated Trojan TCP fixture.

No VDS, Docker, real ACME, Cloudflare account or external endpoint is touched.
Obtain the official S-UI v1.6.7 Linux-amd64 binary separately. This test verifies
its exact binary SHA-256, uses a temporary database/certificate and stops it.
Usage: python3 tests/test_publish_native.py --binary /absolute/path/to/sui
Alternatively set SUI_TEST_BINARY. An optional --report creates a NEW JSON file;
the historical reports distributed with the repository are never overwritten.
"""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import socket
import socketserver
import sqlite3
import ssl
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publish_fixture', BASE / 'mualiy-yayinla.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
BINARY_SHA256 = 'f57c3bc95b490f1c3154c5013451d98b8e74426174fd688c85052ce338413a11'


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class Echo(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(8)
        self.request.sendall(self.request.recv(1024))


class LoopbackFixtureAPI(m.API):
    """Only the temporary fixture inbound differs from production publication."""
    def add(self, kind, obj):
        if kind == 'inbounds':
            obj = dict(obj, listen='127.0.0.1')
        return super().add(kind, obj)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=os.environ.get('SUI_TEST_BINARY'))
    parser.add_argument('--report', type=Path, help='Optional new, non-existing report file')
    args = parser.parse_args()
    if args.binary is None:
        parser.error('Provide --binary or SUI_TEST_BINARY; no cached/VDS binary is assumed.')
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        parser.error('This exact binary fixture requires Linux amd64.')
    if os.geteuid() == 0:
        parser.error('Run this disposable native fixture as a normal user, not root.')
    if shutil.which('openssl') is None:
        parser.error('openssl is required; nothing will be installed automatically.')
    binary = Path(args.binary).expanduser().resolve(strict=True)
    if not binary.is_file() or not os.access(binary, os.X_OK):
        parser.error('Binary must be an existing executable file.')
    if hashlib.sha256(binary.read_bytes()).hexdigest() != BINARY_SHA256:
        parser.error('Official v1.6.7 binary SHA-256 mismatch; refusing to execute.')
    if args.report and os.path.lexists(args.report):
        parser.error('--report must not overwrite an existing file or symlink.')

    result = {
        'evidence_scope': 'fresh disposable localhost fixture, not a VDS rollout',
        'native_version': 'S-UI 1.6.7 / embedded sing-box 1.14.4',
        'binary_sha256': BINARY_SHA256,
        'docker_tested': False,
        'real_acme_tested': False,
        'vds_changed': False,
        'all_fixture_listeners_loopback': True,
        'fixture_stopped': False,
    }
    process = None
    old_umask = os.umask(0o077)
    try:
        with tempfile.TemporaryDirectory(prefix='mualiy-publish-fixture-') as tmp:
            p = Path(tmp)
            env = {k: v for k, v in os.environ.items() if not k.startswith('SUI_')}
            env.update(SUI_DB_FOLDER=str(p / 'db'), SUI_LOG_LEVEL='warn')
            (p / 'db').mkdir(mode=0o700)
            ports = set()
            while len(ports) < 3:
                ports.add(free_port())
            http_port, sub_port, vpn_port = sorted(ports)
            user = 'native-fixture'
            password = secrets.token_urlsafe(24)
            # These CLI credentials are temporary test data, never VDS credentials.
            for cli in (
                ['setting', '-port', str(http_port), '-path', '/app/',
                 '-subPort', str(sub_port), '-subPath', '/sub/'],
                ['admin', '-username', user, '-password', password],
            ):
                completed = subprocess.run([str(binary), *cli], cwd=tmp, env=env,
                                           capture_output=True, text=True, timeout=10)
                if completed.returncode:
                    raise RuntimeError('native fixture CLI setup failed')
            # The CLI has no listen-address flag. Only this NEW, STOPPED temporary
            # database is edited; this must never be copied to a production DB.
            with sqlite3.connect(p / 'db' / 's-ui.db') as database:
                for key in ('webListen', 'subListen'):
                    database.execute('DELETE FROM settings WHERE key = ?', (key,))
                    database.execute('INSERT INTO settings (key, value) VALUES (?, ?)',
                                     (key, '127.0.0.1'))
            cert, key = p / 'cert.pem', p / 'key.pem'
            subprocess.run([
                'openssl', 'req', '-x509', '-newkey', 'ec', '-pkeyopt',
                'ec_paramgen_curve:P-256', '-nodes', '-days', '2',
                '-subj', '/CN=' + m.DOMAIN, '-addext', 'subjectAltName=DNS:' + m.DOMAIN,
                '-keyout', str(key), '-out', str(cert),
            ], capture_output=True, check=True, timeout=15)
            with (p / 'native.log').open('wb') as log:
                process = subprocess.Popen([str(binary)], env=env, cwd=tmp,
                                           stdout=log, stderr=subprocess.STDOUT)
                try:
                    base = 'http://127.0.0.1:' + str(http_port)
                    deadline = time.monotonic() + 15
                    while True:
                        try:
                            api = LoopbackFixtureAPI(user, password, base)
                            break
                        except (OSError, urllib.error.URLError):
                            if time.monotonic() > deadline or process.poll() is not None:
                                raise RuntimeError('native fixture did not start') from None
                            time.sleep(.15)
                    result['login_with_cookie_and_same_origin'] = True
                    result['consistent_sqlite_backup'] = api.raw('getdb').startswith(b'SQLite format 3\x00')
                    state = {
                        'client_name': 'fixture-' + secrets.token_hex(10),
                        'trojan_password': secrets.token_urlsafe(32),
                    }
                    m.configure_api(api, state, str(cert), str(key), vpn_port)
                    result['api_tls_inbound_and_client_created'] = True
                    m.configure_api(api, state, str(cert), str(key), vpn_port)
                    result['api_setup_idempotent'] = True
                    if api.request('load')['subURI'] != 'https://sub.mualiy.net/sub/':
                        raise RuntimeError('public subscription base URL mismatch')
                    result['public_subscription_base_configured'] = True
                    context = ssl.create_default_context(cafile=str(cert))
                    with socketserver.TCPServer(('127.0.0.1', 0), Echo) as echo:
                        thread = threading.Thread(target=echo.serve_forever, daemon=True)
                        thread.start()
                        try:
                            echo_port = echo.server_address[1]
                            with socket.create_connection(('127.0.0.1', vpn_port), timeout=8) as sock:
                                with context.wrap_socket(sock, server_hostname=m.DOMAIN) as tls:
                                    result['tls_hostname_and_fixture_ca_verified'] = True
                                    header = hashlib.sha224(state['trojan_password'].encode()).hexdigest().encode()
                                    payload = b'mualiy-authenticated-trojan-fixture'
                                    tls.sendall(header + b'\r\n\x01\x01' + socket.inet_aton('127.0.0.1')
                                                + echo_port.to_bytes(2, 'big') + b'\r\n' + payload)
                                    data = b''
                                    while len(data) < len(payload):
                                        part = tls.recv(len(payload) - len(data))
                                        if not part:
                                            raise RuntimeError('authenticated Trojan TCP echo ended early')
                                        data += part
                                    if data != payload:
                                        raise RuntimeError('authenticated Trojan TCP echo mismatch')
                                    result['authenticated_trojan_tcp_echo'] = True
                        finally:
                            echo.shutdown()
                            thread.join(timeout=2)
                    m.API(user, password, base)
                    result['admin_password_unchanged'] = True
                    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                    with opener.open('http://127.0.0.1:' + str(sub_port) + '/sub/'
                                     + state['client_name'], timeout=10) as response:
                        body = response.read()
                    decoded = body if b'trojan://' in body else base64.b64decode(body)
                    if b'trojan://' not in decoded or m.DOMAIN.encode() not in decoded:
                        raise RuntimeError('subscription did not contain a compatible Trojan URI')
                    result['subscription_http_ok'] = True
                    result['subscription_base64_trojan_uri_verified'] = True
                    result['subscription_response_bytes'] = len(body)
                    if not all(result[k] for k in ('consistent_sqlite_backup', 'authenticated_trojan_tcp_echo')):
                        raise RuntimeError('fixture invariant failed')
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
                    result['fixture_stopped'] = True
    finally:
        os.umask(old_umask)
    text = json.dumps(result, indent=2) + '\n'
    if args.report:
        with args.report.open('x', encoding='utf-8') as report:
            report.write(text)
    print(text, end='')


if __name__ == '__main__':
    main()
