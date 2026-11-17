#!/usr/bin/env python3
"""Real pinned sing-box client/server tests with a local Render-like TLS terminator.
Positive tests require example.com, Cloudflare DoH, curl, openssl, and Linux.
All credentials, certificates, and logs are ephemeral and removed on exit.
"""
import argparse
import contextlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import select
import signal
import socket
import socketserver
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from client import make_config


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_port(port, process, timeout=12):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError('A required process exited before opening its port.')
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise AssertionError('Port startup deadline exceeded.')


def child_pids(pid):
    # Go may fork from any OS thread, not necessarily the thread-group leader.
    children = set()
    for path in Path(f'/proc/{pid}/task').glob('*/children'):
        with contextlib.suppress(FileNotFoundError):
            children.update(path.read_text().split())
    return sorted(children)


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


class SinkHandler(BaseHTTPRequestHandler):
    hits = 0

    def do_GET(self):
        type(self).hits += 1
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'PRIVATE TARGET MUST NOT BE REACHED')

    def log_message(self, *_):
        pass


class TLSRelay(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def get_request(self):
        sock, address = super().get_request()
        sock.settimeout(10)
        try:
            return self.tls.wrap_socket(sock, server_side=True), address
        except BaseException:
            sock.close()
            raise

    def handle_error(self, *_):
        # Expected when the negative TLS trust test closes during the handshake.
        pass


class RelayHandler(socketserver.BaseRequestHandler):
    def handle(self):
        with contextlib.suppress(OSError), socket.create_connection(('127.0.0.1', self.server.target_port), timeout=10) as backend:
            sockets = [self.request, backend]
            while True:
                readable, _, _ = select.select(sockets, [], [], 15)
                if isinstance(self.request, ssl.SSLSocket) and self.request.pending():
                    if self.request not in readable:
                        readable.append(self.request)
                if not readable:
                    return
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    destination = backend if source is self.request else self.request
                    destination.sendall(data)


def run(args):
    gateway = Path(args.gateway).resolve()
    core = Path(args.core).resolve()
    if not gateway.is_file() or not core.is_file():
        raise ValueError('Build the gateway and fetch the pinned core first (make e2e).')
    results = []
    processes = []
    log_files = []
    servers = []
    forbidden_strings = []

    def passed(name, condition=True):
        if not condition:
            raise AssertionError(name)
        print('PASS:', name, flush=True)
        results.append(name)

    with tempfile.TemporaryDirectory(prefix='ozgurag-e2e-') as directory:
        temp = Path(directory)
        try:
            password, wrong_password = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            forbidden_strings.extend([password, wrong_password])
            origin_port, core_port = free_port(), free_port()
            sink = ThreadingHTTPServer(('127.0.0.1', 0), SinkHandler)
            SinkHandler.hits = 0
            servers.append(sink)
            threading.Thread(target=sink.serve_forever, daemon=True).start()
            sink_port = sink.server_port
            env = {k: v for k, v in os.environ.items() if not k.startswith('TROJAN_')}
            env.update(TROJAN_PASSWORD=password, PORT=str(origin_port), CORE_PORT=str(core_port),
                       SING_BOX_BINARY=str(core), MAX_TUNNELS='4', WS_PATH='/tunnel',
                       EGRESS_TCP_PORTS=f'80,443,{sink_port}', HANDSHAKES_PER_MINUTE='60', HANDSHAKE_BURST='20')

            def launch(command, name, environment=None):
                path = temp / (name + '.log')
                log = open(path, 'wb')
                log_files.append((path, log))
                p = subprocess.Popen(command, env=environment, stdout=log, stderr=subprocess.STDOUT)
                processes.append(p)
                return p

            service = launch([str(gateway), 'serve'], 'gateway', env)
            wait_port(origin_port, service)
            direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with direct.open(f'http://127.0.0.1:{origin_port}/healthz', timeout=3) as response:
                health = json.load(response)
            passed('gateway readiness + real core listener', health == {'status': 'ok', 'core': 'ready'})

            cert, key = temp / 'local-ca.crt', temp / 'local-ca.key'
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                            '-keyout', str(key), '-out', str(cert), '-subj', '/CN=localhost',
                            '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1'], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            tls.load_cert_chain(cert, key)
            relay = TLSRelay(('127.0.0.1', 0), RelayHandler)
            relay.tls, relay.target_port = tls, origin_port
            servers.append(relay)
            threading.Thread(target=relay.serve_forever, daemon=True).start()

            def launch_client(secret, name, trusted=True, ws_path='/tunnel'):
                port = free_port()
                conf = make_config('127.0.0.1', secret, ws_path, relay.server_address[1], port)
                conf['outbounds'][0]['tls']['server_name'] = 'localhost'
                if trusted:
                    conf['outbounds'][0]['tls']['certificate_path'] = str(cert)
                path = temp / (name + '.json')
                path.write_text(json.dumps(conf))
                path.chmod(0o600)
                result = subprocess.run([str(core), 'check', '-c', str(path)], capture_output=True)
                if result.returncode:
                    raise AssertionError('Generated client schema is incompatible: ' + result.stderr.decode())
                process = launch([str(core), 'run', '-c', str(path)], name)
                wait_port(port, process)
                return port

            proxy_port = launch_client(password, 'client-valid')
            passed('generated client JSON accepted by pinned sing-box core')

            def curl(port, url, socks=False):
                command = ['curl', '--silent', '--show-error', '--fail-with-body', '--noproxy', '', '--connect-timeout', '8', '--max-time', '20',
                           '--proxy', f'{"socks5h" if socks else "http"}://127.0.0.1:{port}', url]
                return subprocess.run(command, capture_output=True, timeout=25)

            for name, url, socks in [
                ('HTTP → Trojan/WSS → public HTTP', 'http://example.com/', False),
                ('HTTP CONNECT → Trojan/WSS → public HTTPS', 'https://example.com/', False),
                ('SOCKS5h → Trojan/WSS → public HTTPS', 'https://example.com/', True),
            ]:
                result = curl(proxy_port, url, socks)
                if result.returncode:
                    raise AssertionError(name + ': ' + result.stderr.decode(errors='replace'))
                passed(name, b'Example Domain' in result.stdout)

            bad_port = launch_client(wrong_password, 'client-wrong-password')
            result = curl(bad_port, 'https://example.com/')
            passed('wrong Trojan password rejected', result.returncode != 0 and b'Example Domain' not in result.stdout)

            untrusted_port = launch_client(password, 'client-untrusted-ca', trusted=False)
            result = curl(untrusted_port, 'https://example.com/')
            passed('untrusted TLS certificate rejected (no insecure mode)', result.returncode != 0)

            wrong_path_port = launch_client(password, 'client-wrong-path', ws_path='/another-path')
            result = curl(wrong_path_port, 'https://example.com/')
            passed('wrong WebSocket path rejected', result.returncode != 0)

            for name, url in [
                ('loopback target blocked, even on an allowed custom port', f'http://127.0.0.1:{sink_port}/'),
                ('cloud metadata IPv4 target blocked', 'http://169.254.169.254/'),
                ('private IPv4 target blocked', 'http://10.0.0.1/'),
                ('loopback IPv6 target blocked', 'http://[::1]/'),
                ('IPv4-mapped IPv6 loopback target blocked', 'http://[::ffff:127.0.0.1]/'),
                ('disallowed destination port blocked', 'http://1.1.1.1:22/'),
                ('private hostname blocked', f'http://localhost:{sink_port}/'),
            ]:
                result = curl(proxy_port, url)
                passed(name, result.returncode != 0 and b'PRIVATE TARGET' not in result.stdout)
            passed('private HTTP sink received zero requests', SinkHandler.hits == 0)

            # Confirm a public DNS name really points to loopback before testing it.
            request = urllib.request.Request('https://cloudflare-dns.com/dns-query?name=localtest.me&type=A', headers={'Accept': 'application/dns-json'})
            with urllib.request.urlopen(request, timeout=15) as response:
                answers = json.load(response).get('Answer', [])
            passed('DNS rebinding fixture resolves to loopback', any(a.get('type') == 1 and a.get('data') == '127.0.0.1' for a in answers))
            result = curl(proxy_port, f'http://localtest.me:{sink_port}/')
            passed('domain resolving to private IP is blocked', result.returncode != 0 and SinkHandler.hits == 0)

            connection = http.client.HTTPConnection('127.0.0.1', origin_port, timeout=3)
            connection.request('CONNECT', 'example.com:443')
            response = connection.getresponse()
            passed('public gateway is not an open HTTP CONNECT proxy', response.status == 405)
            response.close()
            connection.close()

            statuses = []
            for _ in range(28):
                connection = http.client.HTTPConnection('127.0.0.1', origin_port, timeout=3)
                connection.request('GET', '/tunnel', headers={'Connection': 'Upgrade', 'Upgrade': 'websocket',
                                   'Sec-WebSocket-Version': '13', 'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ=='})
                response = connection.getresponse()
                statuses.append(response.status)
                response.close()
                connection.close()
            passed('global handshake token bucket returns 429 under burst', 429 in statuses)

            joined_logs = '\n'.join(path.read_text(errors='replace') for path, _ in log_files)
            passed('generated passwords are absent from process logs', all(secret not in joined_logs for secret in forbidden_strings))

            child_ids = child_pids(service.pid)
            passed('core child is tracked for lifecycle assertions', bool(child_ids))
            service.terminate()
            service.wait(timeout=8)
            passed('SIGTERM shuts down gateway cleanly', service.returncode == 0)
            passed('SIGTERM leaves no core child behind', all(not Path('/proc', pid).exists() for pid in child_ids))

            crash_env = dict(env, PORT=str(free_port()), CORE_PORT=str(free_port()))
            crash_service = launch([str(gateway), 'serve'], 'gateway-core-crash', crash_env)
            wait_port(int(crash_env['PORT']), crash_service)
            children = child_pids(crash_service.pid)
            if not children:
                raise AssertionError('Could not identify the core child for failure testing.')
            os.kill(int(children[0]), signal.SIGKILL)
            crash_service.wait(timeout=8)
            passed('unexpected core exit fails the gateway instead of reporting healthy', crash_service.returncode != 0)

        except BaseException:
            for path, log in log_files:
                log.flush()
                text = path.read_text(errors='replace')[-5000:]
                for secret in forbidden_strings:
                    text = text.replace(secret, '[REDACTED]')
                print(f'--- {path.name} ---\n{text}', file=sys.stderr)
            raise
        finally:
            for process in reversed(processes):
                stop(process)
            for server in reversed(servers):
                server.shutdown()
                server.server_close()
            for _, log in log_files:
                log.close()
    report = {'result': 'passed', 'checks': results, 'count': len(results), 'transport': 'Trojan/WebSocket with TLS verified via a temporary local CA', 'render_deployed': False, 'docker_built_here': False}
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f'\n{len(results)} end-to-end checks passed. Render deployment is NOT tested here.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gateway', required=True)
    parser.add_argument('--core', required=True)
    parser.add_argument('--report')
    args = parser.parse_args()
    run(args)
