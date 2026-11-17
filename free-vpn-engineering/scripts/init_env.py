#!/usr/bin/env python3
"""Create a fresh private local .env without printing credentials."""
import argparse
from pathlib import Path
import secrets
from common import write_private


def create(path):
    password = secrets.token_urlsafe(32)
    ws_path = '/t-' + secrets.token_urlsafe(12)
    data = (
        '# PRIVATE — never commit or share this file.\n'
        f'TROJAN_PASSWORD={password}\n'
        f'WS_PATH={ws_path}\n'
        'PORT=10000\nCORE_PORT=10001\nEGRESS_TCP_PORTS=80,443\n'
        'MAX_TUNNELS=16\nHANDSHAKES_PER_MINUTE=60\nHANDSHAKE_BURST=20\n'
        'TUNNEL_IDLE_TIMEOUT=2m\nTUNNEL_MAX_AGE=30m\nLOG_LEVEL=warn\n'
    )
    write_private(path, data)
    print(f'Private environment created: {path} (POSIX mode 0600). No secrets printed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('.env'))
    args = parser.parse_args()
    try:
        create(args.output)
    except FileExistsError:
        parser.exit(1, 'Refusing to overwrite an existing file. Back it up or choose --output.\n')
