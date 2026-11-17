#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Locked official downloads; never extract arbitrary paths or execute shell text."""
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import urllib.request

LOCK = json.loads(Path(__file__).with_name('versions.json').read_text())

def blob(url, expected, limit=85 * 1024 * 1024):
    req = urllib.request.Request(url, headers={'User-Agent': 'ozgur-vds/1.0'})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read(limit + 1)
    if len(data) > limit or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Indirme boyutu/SHA-256 uyusmadi; dosya kullanilmayacak.')
    return data

def private_new(path, data, mode=0o600):
    path = Path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as f:
        os.fchmod(f.fileno(), mode)
        f.write(data if isinstance(data, bytes) else data.encode())

def core(dest):
    v = LOCK['sing_box']['version']
    name = f'sing-box-{v}-linux-amd64'
    data = blob(f'https://github.com/SagerNet/sing-box/releases/download/v{v}/{name}.tar.gz', LOCK['sing_box']['amd64_sha256'])
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as t:
        m = t.getmember(name + '/sing-box')
        if not m.isfile() or m.size > 160 * 1024 * 1024:
            raise ValueError('Beklenmeyen binary.')
        private_new(dest, t.extractfile(m).read(), 0o755)

def zapret(dest):
    v = LOCK['zapret2']
    data = blob(v['url'], v['sha256'], 32 * 1024 * 1024)
    dest = Path(dest)
    dest.mkdir(mode=0o755)
    dest.chmod(0o755)
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as t:
        wanted_binary = v['prefix'] + '/binaries/linux-x86_64/nfqws2'
        m = t.getmember(wanted_binary)
        if not m.isfile() or m.size > 16 * 1024 * 1024:
            raise ValueError('Beklenmeyen nfqws2 binary boyutu/turu.')
        binary = t.extractfile(m).read()
        if hashlib.sha256(binary).hexdigest() != v['binary_sha256']:
            raise ValueError('nfqws2 SHA-256 uyusmadi.')
        private_new(dest / 'nfqws2', binary, 0o755)
        for m in t.getmembers():
            prefix = v['prefix'] + '/'
            if not m.name.startswith(prefix):
                continue
            rel = Path(m.name[len(prefix):])
            if rel.is_absolute() or '..' in rel.parts:
                raise ValueError('Arsiv yolu reddedildi.')
            # Lua dependencies, published fake blobs, and upstream license only.
            wanted = rel.parts and rel.parts[0] in ('lua', 'files')
            wanted = wanted or str(rel) == 'docs/LICENSE.txt'
            if not wanted or not m.isfile():
                continue
            if m.size > 8 * 1024 * 1024:
                raise ValueError('Beklenmeyen arsiv dosyasi boyutu.')
            p = dest / rel
            p.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            for parent in (p.parent, *p.parent.parents):
                if parent == dest:
                    break
                parent.chmod(0o755)
            private_new(p, t.extractfile(m).read(), 0o644)
