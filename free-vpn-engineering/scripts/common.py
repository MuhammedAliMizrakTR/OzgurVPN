"""Small standard-library-only helpers. Never evaluate a .env file as code."""
import os
from pathlib import Path
import re

PATH_RE = re.compile(r'/[A-Za-z0-9_-]{4,80}\Z')


def read_env(path):
    values = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep or not re.fullmatch(r'[A-Z][A-Z0-9_]*', key):
            raise ValueError('Unsupported .env syntax. Use simple KEY=value entries.')
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def write_private(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # No silent overwrite, no following an existing symlink, private from creation.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as output:
        output.write(content)


def valid_path(value):
    if not PATH_RE.fullmatch(value) or value in ('/healthz', '/robots'):
        raise ValueError('WS path must be a non-reserved /path of 4-80 URL-safe characters.')
    return value
