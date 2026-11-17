#!/usr/bin/env python3
"""Download one pinned official sing-box archive and verify its locked SHA-256."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def fetch(dest, arch=None):
    lock = json.loads((ROOT / 'versions.json').read_text())
    arch = arch or {'x86_64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}.get(platform.machine())
    if arch not in lock['archives']:
        raise ValueError('Only Linux amd64 and arm64 archives are supported.')
    version = lock['sing_box']
    filename = f'sing-box-{version}-linux-{arch}.tar.gz'
    url = f'https://github.com/SagerNet/sing-box/releases/download/v{version}/{filename}'
    request = urllib.request.Request(url, headers={'User-Agent': 'ozgur-ag-build/1.0'})
    with urllib.request.urlopen(request, timeout=120) as response:
        blob = response.read(80 * 1024 * 1024 + 1)
    if len(blob) > 80 * 1024 * 1024:
        raise ValueError('Archive size limit exceeded.')
    if hashlib.sha256(blob).hexdigest() != lock['archives'][arch]['sha256']:
        raise ValueError('SHA-256 mismatch; refusing to install sing-box.')
    # Extract ONLY the exact binary; never trust arbitrary archive paths.
    member_name = f'sing-box-{version}-linux-{arch}/sing-box'
    with tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz') as archive:
        member = archive.getmember(member_name)
        if not member.isfile() or member.size > 160 * 1024 * 1024:
            raise ValueError('Unexpected archive member.')
        binary = archive.extractfile(member).read()
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_name(dest.name + '.verified.tmp')
    try:
        with open(temporary, 'xb') as output:
            output.write(binary)
        os.chmod(temporary, 0o755)
        os.replace(temporary, dest)
    finally:
        temporary.unlink(missing_ok=True)
    print(f'sing-box {version} / {arch}: SHA-256 verified → {dest}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arch', choices=['amd64', 'arm64'])
    parser.add_argument('--dest', required=True, type=Path)
    args = parser.parse_args()
    fetch(args.dest, args.arch)
