#!/usr/bin/env python3
"""Fresh Mualiy S-UI reset, then run the checksum-pinned Trojan publisher.

This is deliberately narrow: it archives only the known mualiy-sui panel and
mualiy-sui-tunnel state after strict ownership checks. It never deletes that
state, touches ThinLinc/Minecraft/Jitsi, flushes a firewall, or accepts secrets
on the command line. --apply is interactive and must run from the VDS terminal.
"""
import argparse
import fcntl
import getpass
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = Path('/opt/mualiy-sui')
LIVE = Path('/opt/mualiy-sui-live')
PROJECT = 'mualiy-sui'
SERVICE = 'panel'
TUNNEL_PROJECT = 'mualiy-sui-tunnel'
PANEL_MARKER = 'mualiy-sui-loopback-bootstrap-v1'
LIVE_MARKER = 'mualiy-sui-live-v1'
PANEL_IMAGE = 'alireza7/s-ui:v1.6.7@sha256:c262ebd5cd53fd098d3080089af46220473bacbaf1a113e767aa9aadd2eed36d'
PUBLISHER_NAME = 'mualiy-yayinla-347f20b5.py'
PUBLISHER_SHA256 = '347f20b5a4e3115891837a85b6a502e80100ef0235d5b6c6966152535efc8639'


class Stop(Exception):
    pass


def command(args, check=True, timeout=180):
    """Use only the local Docker socket and never print daemon output."""
    env = dict(os.environ)
    for key in ('DOCKER_CONTEXT', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'):
        env.pop(key, None)
    env['DOCKER_HOST'] = 'unix:///var/run/docker.sock'
    result = subprocess.run([str(arg) for arg in args], text=True, capture_output=True,
                            env=env, timeout=timeout)
    if check and result.returncode:
        raise Stop(f'{args[0]} islemi basarisiz (kod {result.returncode}); ham cikti ekrana basilmayacak.')
    return result


def docker_ids(project):
    return command(['docker', 'ps', '-aq', '--filter', f'label=com.docker.compose.project={project}']).stdout.split()


def regular_dir(path, label):
    if path.is_symlink() or not path.is_dir():
        raise Stop(f'{label} beklenen normal dizin degil; otomatik sifirlama durdu.')


def exact_marker(path, marker, label):
    marker_path = path / '.mualiy-managed' if path == ROOT else path / '.managed'
    if marker_path.is_symlink() or not marker_path.is_file() or marker_path.read_text().strip() != marker:
        raise Stop(f'{label} yonetim isareti beklenenden farkli; otomatik sifirlama durdu.')


def load_json_docker(template, container):
    text = command(['docker', 'inspect', '-f', template, container]).stdout
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise Stop('Docker denetim bilgisi guvenli okunamadi; otomatik sifirlama durdu.') from error


def resolve(path):
    return Path(path).resolve()


def managed_panel():
    """Return the sole known panel container, or None if only known files exist."""
    root_exists = os.path.lexists(ROOT)
    ids = docker_ids(PROJECT)
    if len(ids) > 1:
        raise Stop('mualiy-sui projesinde birden fazla container var; otomatik sifirlama durdu.')
    if not root_exists:
        if ids:
            raise Stop('Panel dizini yok ama mualiy-sui containeri var; otomatik sifirlama durdu.')
        return None
    regular_dir(ROOT, 'Mevcut panel dizini')
    exact_marker(ROOT, PANEL_MARKER, 'Mevcut panel dizini')
    for name in ('db', 'cert', 'compose.yaml'):
        path = ROOT / name
        if path.is_symlink() or not path.exists():
            raise Stop(f'Mevcut panelin {name} yolu beklenenden farkli; otomatik sifirlama durdu.')
    if not ids:
        return None
    cid = ids[0]
    labels = load_json_docker('{{json .Config.Labels}}', cid)
    mounts = load_json_docker('{{json .Mounts}}', cid)
    if labels.get('com.docker.compose.service') != SERVICE:
        raise Stop('mualiy-sui containeri beklenen panel servisi degil; otomatik sifirlama durdu.')
    expected = {str(resolve(ROOT / 'db')): '/app/db', str(resolve(ROOT / 'cert')): '/app/cert'}
    actual = {str(resolve(m.get('Source', '/nonexistent'))): m.get('Destination') for m in mounts}
    if not all(actual.get(source) == destination for source, destination in expected.items()):
        raise Stop('Mevcut panel DB/cert mountlari beklenenden farkli; otomatik sifirlama durdu.')
    return cid


def managed_tunnel():
    """Return the sole known connector container, or None when none exists."""
    live_exists = os.path.lexists(LIVE)
    ids = docker_ids(TUNNEL_PROJECT)
    if len(ids) > 1:
        raise Stop('mualiy-sui-tunnel projesinde birden fazla container var; otomatik sifirlama durdu.')
    if not live_exists:
        if ids:
            raise Stop('Tunnel state dizini yok ama mualiy-sui-tunnel containeri var; otomatik sifirlama durdu.')
        return None
    regular_dir(LIVE, 'Mevcut yayin state dizini')
    exact_marker(LIVE, LIVE_MARKER, 'Mevcut yayin state dizini')
    if not ids:
        return None
    cid = ids[0]
    labels = load_json_docker('{{json .Config.Labels}}', cid)
    mounts = load_json_docker('{{json .Mounts}}', cid)
    expected_token = str(resolve(LIVE / 'tunnel-token'))
    expected_mount = any(m.get('Destination') == '/run/secrets/tunnel-token' and
                         str(resolve(m.get('Source', '/nonexistent'))) == expected_token
                         for m in mounts)
    if labels.get('com.docker.compose.service') != 'connector' or not expected_mount:
        raise Stop('Mevcut connector beklenen mualiy tunnel yapisi degil; otomatik sifirlama durdu.')
    return cid


def user_publisher():
    user = os.environ.get('SUDO_USER', '')
    if not user or user == 'root':
        raise Stop('Normal VDS kullanicisindan sudo ile calistir; SUDO_USER bulunamadi.')
    try:
        home = Path(pwd.getpwnam(user).pw_dir)
    except KeyError as error:
        raise Stop('SUDO_USER icin kullanici dizini bulunamadi.') from error
    path = home / PUBLISHER_NAME
    if path.is_symlink() or not path.is_file():
        raise Stop(f'Dogrulanmis yayin dosyasi bulunamadi: {path}')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != PUBLISHER_SHA256:
        raise Stop('Yayin dosyasinin SHA-256 degeri beklenenden farkli; otomatik sifirlama durdu.')
    return path


def ensure_engine():
    version = command(['docker', 'version', '--format', '{{.Server.Version}}']).stdout.strip()
    match = re.match(r'^(\d+)\.', version)
    if not match or int(match.group(1)) < 28:
        raise Stop('Loopback port korumasi icin Docker Engine 28+ gerekli; otomatik guncellenmedi.')
    command(['docker', 'compose', 'version'])


def ensure_ports_free():
    ids = command(['docker', 'ps', '-aq']).stdout.split()
    if ids:
        bindings = command(['docker', 'inspect', '-f', '{{json .HostConfig.PortBindings}}', *ids]).stdout.splitlines()
        for item in bindings:
            try:
                values = json.loads(item) or {}
            except json.JSONDecodeError as error:
                raise Stop('Docker port eslemeleri guvenli okunamadi; otomatik sifirlama durdu.') from error
            for entries in values.values():
                if any(str(entry.get('HostPort')) in {'2095', '2096'} for entry in entries or []):
                    raise Stop('Baska bir Docker containeri 2095/2096 yayini kullaniyor; otomatik sifirlama durdu.')
    if command(['ss', '-H', '-lnt', '( sport = :2095 or sport = :2096 )']).stdout.strip():
        raise Stop('2095/2096 portlarindan biri hala dinleniyor; bilinmeyen surece dokunulmadi.')


def compose_content():
    return '''name: mualiy-sui
services:
  panel:
    image: alireza7/s-ui:v1.6.7@sha256:c262ebd5cd53fd098d3080089af46220473bacbaf1a113e767aa9aadd2eed36d
    platform: linux/amd64
    user: "10001:10001"
    restart: "no"
    init: true
    environment:
      TZ: Europe/Istanbul
      SUI_DB_FOLDER: /app/db
      SUI_LOG_LEVEL: warn
    ports:
      - "127.0.0.1:2095:2095/tcp"
      - "127.0.0.1:2096:2096/tcp"
    volumes:
      - type: bind
        source: ./db
        target: /app/db
        bind:
          create_host_path: false
      - type: bind
        source: ./cert
        target: /app/cert
        read_only: true
        bind:
          create_host_path: false
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    mem_limit: 512m
    cpus: "1.0"
    pids_limit: 256
    stop_grace_period: 20s
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
'''


def archive(path, label):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    destination = path.with_name(path.name + '-reset-archive-' + stamp)
    if os.path.lexists(destination):
        raise Stop('Yedek dizin adi zaten var; otomatik sifirlama durdu.')
    os.replace(path, destination)
    destination.chmod(0o700)
    print(f'Korunan {label} arsivi: {destination}')


def stop_and_remove(container, label):
    # Exact Compose-label and mount checks already happened before this point.
    command(['docker', 'update', '--restart=no', container])
    command(['docker', 'rm', '-f', container], timeout=90)
    print(f'Yalniz dogrulanmis eski {label} containeri kaldirildi.')


def ask_admin():
    user = input('YENI S-UI kullanici adi (3-64, harf/rakam/._-): ').strip()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{2,63}', user):
        raise Stop('Yeni kullanici adi bicimi uygun degil.')
    password = getpass.getpass('YENI S-UI sifresi (gorunmez): ')
    again = getpass.getpass('YENI S-UI sifresi tekrar (gorunmez): ')
    if password != again:
        raise Stop('Yeni sifreler ayni degil.')
    if len(password) < 16 or any(char.isspace() for char in password) or password == 'admin':
        raise Stop('Yeni sifre en az 16 karakter olmali, bosluk icermemeli ve admin olmamali.')
    return user, password


class LocalAPI:
    """Loopback-only S-UI login/change-password helper; passwords never enter argv."""
    def __init__(self):
        self.http = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), http.cookiejar.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.base = 'http://127.0.0.1:2095/app/api/'

    def post(self, action, data):
        request = urllib.request.Request(
            self.base + action,
            data=urllib.parse.urlencode(data).encode(),
            headers={'Origin': 'http://127.0.0.1:2095', 'X-Requested-With': 'XMLHttpRequest',
                     'Content-Type': 'application/x-www-form-urlencoded'},
        )
        try:
            with self.http.open(request, timeout=20) as response:
                result = json.loads(response.read())
        except Exception as error:
            raise Stop('Yerel panel API istegi basarisiz; parolalar ekrana basilmayacak.') from error
        if not result.get('success'):
            raise Stop('Yerel panel API istegi reddedildi; parolalar ekrana basilmayacak.')


def configure_fresh_admin(user, password):
    api = LocalAPI()
    api.post('login', {'user': 'admin', 'pass': 'admin'})
    api.post('changePass', {'oldPass': 'admin', 'newUsername': user, 'newPass': password})
    verified = LocalAPI()
    verified.post('login', {'user': user, 'pass': password})


def create_fresh_panel(user, password):
    ROOT.mkdir(mode=0o750)
    try:
        os.chown(ROOT, 0, 10001)
        db, cert = ROOT / 'db', ROOT / 'cert'
        db.mkdir(mode=0o700)
        cert.mkdir(mode=0o750)
        os.chown(db, 10001, 10001)
        os.chown(cert, 0, 10001)
        compose = ROOT / 'compose.yaml'
        with compose.open('x', encoding='utf-8') as handle:
            handle.write(compose_content())
        compose.chmod(0o640)
        (ROOT / '.mualiy-managed').write_text(PANEL_MARKER + '\n', encoding='utf-8')
        command(['docker', 'compose', '-p', PROJECT, '-f', compose, 'config', '--quiet'])
        print('Yeni panel loopback 2095/2096 ile baslatiliyor...')
        command(['docker', 'compose', '-p', PROJECT, '-f', compose,
                 'up', '-d', '--wait', '--wait-timeout', '120', SERVICE], timeout=180)
        ids = docker_ids(PROJECT)
        if len(ids) != 1:
            raise Stop('Yeni panel containeri benzersiz bulunamadi.')
        state = load_json_docker('{{json .State}}', ids[0])
        if not state.get('Running') or state.get('Health', {}).get('Status') != 'healthy':
            raise Stop('Yeni panel healthy olmadi.')
        configure_fresh_admin(user, password)
        print('Yeni panel ve admin hesabi yerelde dogrulandi.')
    except Exception:
        # Keep new files for diagnosis, but stop only this known new Compose project.
        command(['docker', 'compose', '-p', PROJECT, '-f', ROOT / 'compose.yaml', 'stop'], check=False)
        raise


def plan():
    ensure_engine()
    publisher = user_publisher()
    panel = managed_panel()
    tunnel = managed_tunnel()
    return publisher, panel, tunnel


def apply():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise Stop('Gizli girisler icin dosyayi dogrudan VDS terminalinde calistir; pipe kullanma.')
    publisher, panel, tunnel = plan()
    print('Bu islem dogrulanmis eski mualiy panel/tunnel state dizinlerini root-ozel arsive tasir; silmez.')
    if input('Sifirdan kurulum ve yayin icin SIFIRLA yaz: ').strip() != 'SIFIRLA':
        raise Stop('Sifirlama onayi verilmedi.')
    user, password = ask_admin()
    print('Sabit S-UI image indiriliyor; mevcut servisler yeniden baslatilmiyor...')
    command(['docker', 'pull', '--platform', 'linux/amd64', PANEL_IMAGE], timeout=900)
    if tunnel:
        stop_and_remove(tunnel, 'mualiy-sui-tunnel')
    if os.path.lexists(LIVE):
        archive(LIVE, 'yayin state')
    if panel:
        stop_and_remove(panel, 'mualiy-sui/panel')
    if os.path.lexists(ROOT):
        archive(ROOT, 'panel')
    ensure_ports_free()
    create_fresh_panel(user, password)
    # Clear sensitive Python objects before the publisher asks for them again.
    del password
    print('Yeni panel hazir. Access/DNS/tunnel on kosullari uygunsa yayin araci simdi baslayacak.')
    result = subprocess.run(['/usr/bin/python3', str(publisher), '--apply'], env=os.environ.copy())
    if result.returncode:
        raise Stop('Yeni panel korundu ancak yayin araci tamamlanmadi; DUR satirini paylas, arsivleri silme.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true', help='Only verify reset scope; no changes')
    group.add_argument('--apply', action='store_true', help='Archive known state, create panel, then publish')
    args = parser.parse_args()
    try:
        if os.geteuid() != 0:
            raise Stop('VDS terminalinde sudo python3 ile calistir.')
        if os.uname().machine not in ('x86_64', 'amd64'):
            raise Stop('Bu sabit image Linux x86_64 VDS icindir.')
        for tool in ('docker', 'ss', 'python3'):
            if shutil.which(tool) is None:
                raise Stop(f'Gerekli komut yok: {tool}; otomatik paket kurulumu yapilmadi.')
        os.umask(0o077)
        lock_fd = os.open('/run/lock/mualiy-sui-reset.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(lock_fd, 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if args.check:
                publisher, panel, tunnel = plan()
                print('SIFIRLAMA_ON_KONTROL_OK')
                print('Eski panel containeri: ' + ('var' if panel else 'yok'))
                print('Eski tunnel connectoru: ' + ('var' if tunnel else 'yok'))
                print('Dogrulanmis yayin dosyasi: ' + str(publisher))
            else:
                apply()
    except (Stop, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        message = str(error) if isinstance(error, Stop) else type(error).__name__ + '. Ham hata veya sir ekrana basilmayacak.'
        print('DUR: ' + message, file=sys.stderr)
        print('Arsivlenen veya yeni olusan dosyalari silme; token/parola/link/log gonderme.', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nDUR: Iptal edildi. Arsivlenen veya yeni olusan dosyalari silme.', file=sys.stderr)
        return 130
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
