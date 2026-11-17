#!/usr/bin/env python3
"""Build-independent smoke check for the image built by CI. Requires Docker."""
import argparse
import json
import os
import secrets
import subprocess
import time
import urllib.request


def run(image):
    name = 'ozgurag-test-' + secrets.token_hex(5)
    env = dict(os.environ, TROJAN_PASSWORD=secrets.token_urlsafe(32))
    try:
        subprocess.run(['docker', 'run', '-d', '--name', name, '--read-only', '--tmpfs', '/tmp:rw,nosuid,noexec,size=16m,mode=1777',
                        '--cap-drop=ALL', '--security-opt=no-new-privileges:true', '-e', 'TROJAN_PASSWORD',
                        '-p', '127.0.0.1::10000', image], env=env, check=True, stdout=subprocess.DEVNULL)
        mapping = subprocess.check_output(['docker', 'port', name, '10000/tcp'], text=True).strip()
        port = int(mapping.rsplit(':', 1)[1])
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                with opener.open(f'http://127.0.0.1:{port}/healthz', timeout=1) as response:
                    if json.load(response).get('status') == 'ok':
                        break
            except (OSError, ValueError):
                pass
            time.sleep(0.2)
        else:
            raise AssertionError('Container did not become ready.')
        uid = subprocess.check_output(['docker', 'exec', name, 'id', '-u'], text=True).strip()
        assert uid == '10001', 'Expected non-root UID 10001.'
        subprocess.run(['docker', 'exec', name, 'vpn-gateway', 'healthcheck'], check=True)
        write_test = subprocess.run(['docker', 'exec', name, 'touch', '/must-not-be-writable'], capture_output=True)
        assert write_test.returncode != 0, 'Expected a read-only root filesystem.'
        print('PASS: real container is healthy, non-root, read-only, and runs without capabilities.')
    finally:
        subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', default='ozgurag:ci')
    run(parser.parse_args().image)
