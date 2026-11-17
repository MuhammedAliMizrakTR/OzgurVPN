#!/usr/bin/env python3
"""Operator-only: generate distinct invitation credentials into a private file."""
import argparse
import json
from pathlib import Path
import re
import secrets
from common import write_private


def make_users(names):
    if not 1 <= len(names) <= 64 or len(set(names)) != len(names):
        raise ValueError('Choose 1-64 distinct user names.')
    if any(not re.fullmatch(r'[A-Za-z0-9_-]{1,32}', name) for name in names):
        raise ValueError('Names must contain 1-32 letters, digits, underscores or hyphens.')
    return [{'name': name, 'password': secrets.token_urlsafe(32)} for name in names]


def select_password(path, name):
    if not name:
        raise ValueError('--user is required with --users-file.')
    try:
        users = json.loads(Path(path).read_text(encoding='utf-8'))
        matches = [u['password'] for u in users if u['name'] == name]
    except (TypeError, KeyError, ValueError):
        raise ValueError('Invalid users JSON file.') from None
    if len(matches) != 1 or not isinstance(matches[0], str):
        raise ValueError('Exactly one matching user must exist in the users file.')
    return matches[0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--names', required=True, help='Comma-separated names, e.g. owner,friend')
    parser.add_argument('--output', type=Path, default=Path('secrets/users.json'))
    args = parser.parse_args()
    try:
        users = make_users(args.names.split(','))
        write_private(args.output, json.dumps(users, separators=(',', ':')) + '\n')
    except (ValueError, OSError) as error:
        parser.exit(1, f'Cannot generate users: {error}\n')
    print(f'Private credentials for {len(users)} users written to {args.output}. No secrets printed.')
    print('Store its contents ONLY as the private TROJAN_USERS_JSON environment value; remove TROJAN_PASSWORD.')
