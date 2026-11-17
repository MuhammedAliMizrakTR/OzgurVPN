#!/usr/bin/env python3
"""Retire only old native VPN units; preserve the new mualiy-sui Docker panel.
Default: --check. --apply stops/disables the named old units and moves old files
into a root-private archive. It does NOT permanently erase data or remove users.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

UNITS = ('ozgur-trojan.service', 's-ui.service', 's.ui.service', 'sing-box.service')
PANEL_ROOT = Path('/opt/mualiy-sui')
PROJECT = 'mualiy-sui'
SYSTEM_DIRS = (Path('/etc/systemd/system'), Path('/run/systemd/system'))
VENDOR_DIRS = (Path('/usr/lib/systemd/system'), Path('/lib/systemd/system'))
OLD_DATA = tuple(map(Path, (
    '/opt/ozgur-vds', '/etc/ozgur-vds', '/root/ozgur-vds-clients',
    '/usr/local/s-ui', '/usr/bin/s-ui', '/usr/local/bin/s-ui',
)))
BACKUP_ROOT = Path('/root')
PROC_ROOT = Path('/proc')
LOCK = Path('/run/lock/mualiy-old-native-cleanup.lock')
LIVE_STATES = {'active', 'activating', 'reloading', 'deactivating'}


class Refuse(Exception):
    pass


def run(args, check=True):
    env = dict(os.environ)
    for key in ('DOCKER_CONTEXT', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'):
        env.pop(key, None)
    env['DOCKER_HOST'] = 'unix:///var/run/docker.sock'
    # Never print full commands, unit ExecStart strings or inspect environments.
    result = subprocess.run([str(a) for a in args], env=env, capture_output=True,
                            text=True, timeout=90)
    if check and result.returncode:
        raise Refuse(f'{args[0]} islemi basarisiz (kod {result.returncode}); temizlik surdurulmedi.')
    return result


def exists(path):
    return os.path.lexists(path)


def canonical(path):
    return Path(os.path.realpath(path))


def overlaps(a, b):
    a, b = canonical(a), canonical(b)
    return a == b or a in b.parents or b in a.parents


def unit_info(unit):
    result = run(['systemctl', 'show', unit,
                  '--property=LoadState,ActiveState,UnitFileState,FragmentPath', '--no-pager'], False)
    info = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if not info.get('LoadState'):
        raise Refuse('systemd durumu guvenli okunamadi; hicbir birim silinmeyecek.')
    if info['LoadState'] not in {'loaded', 'not-found', 'masked'}:
        raise Refuse(f'{unit}: beklenmeyen LoadState; once birim incelenmeli.')
    return info


def docker_panel():
    result = run(['docker', 'ps', '-q', '--filter', f'label=com.docker.compose.project={PROJECT}',
                  '--filter', 'label=com.docker.compose.service=panel'])
    ids = result.stdout.split()
    if len(ids) != 1 or not re.fullmatch(r'[a-f0-9]{12,64}', ids[0]):
        raise Refuse('Yeni mualiy-sui panel containeri bulunamadi; eski S-UI yanlislikla kaldirilmamasi icin duruldu.')
    cid = ids[0]
    state = json.loads(run(['docker', 'inspect', '--format', '{{json .State}}', cid]).stdout)
    if not state.get('Running') or state.get('Health', {}).get('Status') != 'healthy':
        raise Refuse('Yeni Docker paneli healthy degil; once paneli dogrula, eski kurulum silinmedi.')
    mounts = json.loads(run(['docker', 'inspect', '--format', '{{json .Mounts}}', cid]).stdout)
    if not any(m.get('Destination') == '/app/db' and
               canonical(m.get('Source', '/nonexistent')) == canonical(PANEL_ROOT / 'db')
               for m in mounts):
        raise Refuse('Yeni panelin DB dizini beklenenden farkli; sifre/veri kaybini onlemek icin duruldu.')
    return cid


def mounted_sources():
    # Protect data used by stopped containers too, not just currently running ones.
    ids = run(['docker', 'ps', '-aq']).stdout.split()
    if not ids:
        raise Refuse('Docker envanteri bos; panel durumu degismis olabilir.')
    if not all(re.fullmatch(r'[a-f0-9]{12,64}', i) for i in ids):
        raise Refuse('Docker kimlikleri guvenli okunamadi.')
    result = run(['docker', 'inspect', '--format', '{{json .Mounts}}', *ids])
    sources = []
    for line in result.stdout.splitlines():
        for mount in json.loads(line):
            if mount.get('Source'):
                sources.append(Path(mount['Source']))
    return sources


def candidates():
    paths = list(OLD_DATA)
    for base in SYSTEM_DIRS:
        for unit in UNITS:
            paths.extend(base / (unit + suffix) for suffix in ('', '.d', '.wants', '.requires'))
        # Exact old unit basenames only; never move an entire target's wants dir.
        if base.is_dir():
            for parent in base.iterdir():
                if parent.is_dir() and parent.name.endswith(('.wants', '.requires')):
                    paths.extend(parent / unit for unit in UNITS)
    return sorted({p for p in paths if exists(p)}, key=str)


def inspect_plan():
    cid = docker_panel()
    helper = unit_info('ozgur-zapret.service')
    if helper['LoadState'] != 'not-found' or helper.get('ActiveState') in LIVE_STATES:
        raise Refuse('ozgur-zapret.service bulundu; /opt/ozgur-vds yardimcisina bagimli olabilir. Resmi zapret2 degistirilmedi; once bu bagimlilik incelenmeli.')
    states = {unit: unit_info(unit) for unit in UNITS}
    allowed = {str(base / unit) for base in SYSTEM_DIRS for unit in UNITS}
    protected_markers = (str(PANEL_ROOT), PROJECT, cid, cid[:12])
    native_executables = {
        'ozgur-trojan.service': {str(OLD_DATA[0] / 'sing-box')},
        's-ui.service': {str(OLD_DATA[3] / 'sui'), str(OLD_DATA[3] / 's-ui')},
        's.ui.service': {str(OLD_DATA[3] / 'sui'), str(OLD_DATA[3] / 's-ui')},
        'sing-box.service': {str(OLD_DATA[0] / 'sing-box'), '/usr/bin/sing-box', '/usr/local/bin/sing-box'},
    }
    unit_texts = {}
    for unit, info in states.items():
        # A distro-managed/vendor unit requires package-aware removal, not rm.
        if any(exists(base / unit) for base in VENDOR_DIRS):
            raise Refuse(f'{unit}: vendor/paket birim dosyasi var; otomatik dosya kaldirma yapilmadi.')
        fragment = info.get('FragmentPath', '')
        if fragment and fragment != '/dev/null' and fragment not in allowed:
            raise Refuse(f'{unit}: standart disi birim konumu; once inceleme gerekli.')
        if info['LoadState'] == 'loaded':
            start = run(['systemctl', 'show', unit, '--property=ExecStart', '--value']).stdout
            # Includes real unit fragment and drop-ins; retain only in the private backup.
            contents = run(['systemctl', 'cat', unit, '--no-pager']).stdout
            if any(marker in start + contents for marker in protected_markers):
                raise Refuse(f'{unit}: yeni Docker paneline referans veriyor; korumak icin duruldu.')
            if re.search(r'\b(?:docker|podman|cloudflared)\b', start + contents):
                raise Refuse(f'{unit}: container/tunel komutu iceriyor; native kurulum oldugu dogrulanamadi.')
            executables = re.findall(r'\bpath=([^\s;]+)\s*;', start)
            if len(executables) != 1 or executables[0] not in native_executables[unit]:
                raise Refuse(f'{unit}: ExecStart beklenen eski native binary degil; once inceleme gerekli.')
            unit_texts[unit] = contents
    paths = candidates()
    sources = mounted_sources()
    for path in paths:
        if overlaps(path, PANEL_ROOT) or any(overlaps(path, source) for source in sources):
            raise Refuse(f'Planlanan eski yol Docker/protected veriyle cakisti: {path}; tasinmadi.')
        if path.is_dir() and not path.is_symlink() and os.path.ismount(path):
            raise Refuse(f'Planlanan yol bir mountpoint: {path}; tasinmadi.')
    return states, paths, unit_texts


def process_references():
    """Best-effort extra guard after unit stop; never kill processes by name."""
    for entry in PROC_ROOT.iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            paths = [os.readlink(entry / part).removesuffix(' (deleted)') for part in ('exe', 'cwd')]
            arguments = (entry / 'cmdline').read_bytes().decode(errors='replace').split('\0')
        except (OSError, ProcessLookupError):
            continue
        for candidate in OLD_DATA:
            root = str(candidate)
            if any(p == root or p.startswith(root + '/') for p in paths):
                raise Refuse(f'Eski dizini kullanan baska surec var (PID {entry.name}); dosyalar tasinmadi.')
            if any(arg == root or arg.startswith(root + '/') or ('=' + root + '/') in arg
                   for arg in arguments):
                raise Refuse(f'Eski dosyaya referans veren baska surec var (PID {entry.name}); dosyalar tasinmadi.')


def execute(apply=False):
    if os.geteuid() != 0:
        raise Refuse('VDS terminalinde sudo python3 ile calistir.')
    os.umask(0o077)
    states, paths, unit_texts = inspect_plan()
    for unit, info in states.items():
        print(f"{unit}: {info['LoadState']} / {info.get('ActiveState', '?')} / {info.get('UnitFileState', '-')}")
    print(f'Aktif konumlardan arsivlenecek nesne: {len(paths)}')
    for path in paths:
        print('  ' + str(path))
    if not apply:
        print('Kontrol bitti. Degisiklik icin ayni dosyayi --apply ile calistir.')
        return None

    backup = Path(tempfile.mkdtemp(prefix='mualiy-eski-servisler-', dir=BACKUP_ROOT))
    backup.chmod(0o700)
    print('Root-ozel geri donus arsivi: ' + str(backup))
    metadata = {'units_before': states, 'planned_paths': [str(p) for p in paths],
                'moved_paths': [], 'scope': 'old native units only; users, firewall and Docker data preserved'}
    manifest = backup / 'manifest.json'
    manifest.write_text(json.dumps(metadata, indent=2) + '\n')
    for unit, contents in unit_texts.items():
        (backup / (unit + '.snapshot.txt')).write_text(contents)
    try:
        for unit in states:
            # A previous disable can also remove an alias among the exact targets.
            current = unit_info(unit)
            if current['LoadState'] != 'not-found' or current.get('ActiveState') in LIVE_STATES:
                run(['systemctl', 'stop', unit])
                if current.get('UnitFileState') in {'enabled', 'enabled-runtime', 'linked', 'linked-runtime', 'indirect'}:
                    run(['systemctl', 'disable', unit])
                if unit_info(unit).get('ActiveState') in LIVE_STATES:
                    raise Refuse(f'{unit} hala calisiyor; dosyalara dokunulmadi.')
        process_references()
        # Recheck Docker mounts after the units stopped, before moving any data.
        sources = mounted_sources()
        docker_panel()
        for path in paths:
            if not exists(path):
                continue
            if overlaps(path, PANEL_ROOT) or any(overlaps(path, src) for src in sources):
                raise Refuse(f'Docker veri cakismasi olustu: {path}; devam edilmedi.')
            dest = backup / 'files' / str(path).lstrip('/')
            dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            run(['mv', '--', path, dest])
            metadata['moved_paths'].append(str(path))
            manifest.write_text(json.dumps(metadata, indent=2) + '\n')
        run(['systemctl', 'daemon-reload'])
        for unit in UNITS:
            run(['systemctl', 'reset-failed', unit], False)
        docker_panel()
    except Exception:
        print('Islem yarida kaldiysa eski birimler durdurulmus olabilir; otomatik yeniden baslatilmaz.', file=sys.stderr)
        print('Geri donus dosyalari silinmedi: ' + str(backup), file=sys.stderr)
        raise
    print('\nYeni Docker S-UI ve DB korundu. Eski native dosyalar canli konumlardan arsive tasindi.')
    print('Arsiv ESKI parola/anahtar icerebilir: sohbete yukleme; yalniz root erissin.')
    print('No-login sistem hesaplari ve ortak paketler bilerek silinmedi. Firewall/DNS/zapret2 degismedi.')
    print('8443 socket kontrolu (baska bir dinleyici varsa otomatik oldurulmez):')
    result = run(['ss', '-H', '-lntp', '( sport = :8443 )'], False)
    print(result.stdout.strip() or '8443 icin TCP socket dinleyicisi gorunmuyor.')
    for unit in UNITS:
        info = unit_info(unit)
        print(f"{unit}: {info['LoadState']} / {info.get('ActiveState', '?')}")
    return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--apply', action='store_true')
    group.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        if os.geteuid() != 0:
            raise Refuse('sudo python3 ile calistir.')
        fd = os.open(LOCK, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Refuse('Baska bir eski-servis temizligi calisiyor.')
            execute(args.apply)
    except (Refuse, OSError, ValueError, subprocess.SubprocessError) as error:
        # Generic execution failures never dump unit ExecStart or config contents.
        print('DUR: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
