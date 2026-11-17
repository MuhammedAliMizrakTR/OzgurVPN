#!/usr/bin/env python3
"""One-shot readiness monitoring, NOT a 15-minute sleep bypass or tunnel test."""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def check(base):
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise ValueError('SERVICE_URL must be an HTTPS origin, e.g. https://your-service.onrender.com')
    url = base.rstrip('/') + '/healthz'
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'ozgur-ag-readiness/1.0'})
            with urllib.request.urlopen(request, timeout=85) as response:
                data = json.loads(response.read(4096))
            if data.get('status') == 'ok' and data.get('core') == 'ready':
                print('PASS: gateway and core listener are ready. Egress/authentication are not tested.')
                return
        except (urllib.error.URLError, ValueError, TimeoutError):
            pass
        if attempt < 2:
            time.sleep(10)
    raise RuntimeError('Readiness did not succeed; cold start, quota, deploy, or outage may be responsible.')


if __name__ == '__main__':
    try:
        check(os.environ.get('SERVICE_URL', ''))
    except (ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
