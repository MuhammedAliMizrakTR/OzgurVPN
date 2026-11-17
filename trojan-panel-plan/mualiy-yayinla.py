#!/usr/bin/env python3
"""Mualiy: existing Docker S-UI -> DNS-01 TLS, Trojan and separate panel tunnel.
Only the existing mualiy-sui panel may be recreated. No password reset, host
80/443 takeover, Docker restart/prune, old-directory removal or firewall flush.
Secrets are entered locally without echo, never supplied as command arguments.
"""
import argparse
import base64
import fcntl
import getpass
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

DOMAIN = 'vpn.mualiy.net'
PUBLIC_IP = '38.210.77.17'
PANEL_HOST = 'panel.mualiy.net'
ROOT = Path('/opt/mualiy-sui')
LIVE = Path('/opt/mualiy-sui-live')
MARKER = 'mualiy-sui-live-v1'
PROJECT = 'mualiy-sui'
TAG = 'mualiy-trojan'
TLS_NAME = 'mualiy-vpn-tls'
CERTBOT = 'certbot/dns-cloudflare:v5.10.0@sha256:6d5e1e84f687ce81786c97cbeccb9dda94d86bbb29a81dbb85527bd68008d77d'
CLOUDFLARED = 'cloudflare/cloudflared:2026.11.0@sha256:b94b96edf2c9c4360f8879c8580cfaa99077f19c849ec595ca2f711b27d4f344'
PANEL_IMAGE = 'alireza7/s-ui:v1.6.7@sha256:c262ebd5cd53fd098d3080089af46220473bacbaf1a113e767aa9aadd2eed36d'
BASE_URL = 'http://127.0.0.1:2095'


class Stop(Exception):
    pass


def command(args, check=True, timeout=120):
    env = dict(os.environ)
    for key in ('DOCKER_CONTEXT', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'):
        env.pop(key, None)
    env['DOCKER_HOST'] = 'unix:///var/run/docker.sock'
    r = subprocess.run(list(map(str, args)), capture_output=True, text=True, env=env, timeout=timeout)
    if check and r.returncode:
        # Do not echo command output: ACME/config errors can contain secrets.
        if not LIVE.is_symlink() and (LIVE / '.managed').is_file() and (LIVE / '.managed').read_text().strip() == MARKER:
            private_write(LIVE / 'son-hata.log', r.stdout + '\n' + r.stderr)
        raise Stop(f'{args[0]} islemi basarisiz (kod {r.returncode}). Varsa ozel log: {LIVE}/son-hata.log; sohbete yukleme.')
    return r


def compose(*args):
    return command(['docker', 'compose', '-p', PROJECT, '-f', ROOT / 'compose.yaml', *args], timeout=240)


def private_write(path, data, mode=0o600, gid=None):
    path = Path(path)
    if path.is_symlink():
        raise Stop('Sembolik dosyaya yazilmayacak: ' + str(path))
    if isinstance(data, str):
        data = data.encode()
    fd, name = tempfile.mkstemp(prefix='.mualiy-', dir=path.parent)
    try:
        os.fchmod(fd, mode)
        if gid is not None:
            os.fchown(fd, 0, gid)
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def save_state(state):
    private_write(LIVE / 'state.json', json.dumps(state, indent=2) + '\n')


def require_private_root():
    if LIVE.is_symlink():
        raise Stop('Yayin dizini symlink; duruldu.')
    if LIVE.exists():
        if LIVE.stat().st_uid != 0 or (LIVE / '.managed').read_text().strip() != MARKER:
            raise Stop('Yayin dizini bu betige ait degil; uzerine yazilmadi.')
        LIVE.chmod(0o700)
    else:
        LIVE.mkdir(mode=0o700)
        private_write(LIVE / '.managed', MARKER + '\n')
    for sub in ('letsencrypt', 'work', 'logs'):
        p = LIVE / sub
        if p.is_symlink():
            raise Stop('ACME dizini symlink; duruldu.')
        p.mkdir(mode=0o700, exist_ok=True)


def panel_id(require_healthy=True):
    ids = command(['docker', 'ps', '-aq', '--filter', 'label=com.docker.compose.project=mualiy-sui',
                   '--filter', 'label=com.docker.compose.service=panel']).stdout.split()
    if len(ids) != 1 or not re.fullmatch('[a-f0-9]{12,64}', ids[0]):
        raise Stop('Beklenen tek mualiy-sui/panel containeri bulunamadi; yeni kurulum/parola sifirlama yapilmadi.')
    cid = ids[0]
    state = json.loads(command(['docker', 'inspect', '-f', '{{json .State}}', cid]).stdout)
    mounts = json.loads(command(['docker', 'inspect', '-f', '{{json .Mounts}}', cid]).stdout)
    for dst, src in (('/app/db', ROOT / 'db'), ('/app/cert', ROOT / 'cert')):
        if not any(m.get('Destination') == dst and Path(m.get('Source', '/')).resolve() == src.resolve() for m in mounts):
            raise Stop('Panel DB/cert mountu beklenenden farkli; dosyalara dokunulmadi.')
    if require_healthy and (not state.get('Running') or state.get('Health', {}).get('Status') != 'healthy'):
        raise Stop('Yeni panel healthy degil. Once yerel panelin acildigini dogrula.')
    return cid, state


def checked_config():
    if ROOT.is_symlink() or (ROOT / 'db').is_symlink() or (ROOT / 'cert').is_symlink():
        raise Stop('Panel/veri dizini symlink; otomatik yayin durdu.')
    if (ROOT / '.mualiy-managed').read_text().strip() != 'mualiy-sui-loopback-bootstrap-v1':
        raise Stop('Mevcut panel bootstrap isareti bulunamadi; yeni kurulum yapilmadi.')
    cfg = json.loads(compose('config', '--format', 'json').stdout)
    if set(cfg.get('services', {})) != {'panel'}:
        raise Stop('Compose icinde beklenmeyen baska servis var; degistirilmedi.')
    svc = cfg['services']['panel']
    if svc.get('image') != PANEL_IMAGE or svc.get('user') != '10001:10001':
        raise Stop('Beklenen sabit S-UI image/UID bulunamadi; otomatik degistirilmedi.')
    for port in svc.get('ports', []):
        target = int(port['target'])
        if target in (2095, 2096) and port.get('host_ip') != '127.0.0.1':
            raise Stop('Yonetim portu loopback disina acilmis; once bu durumu duzelt.')
        if target not in (2095, 2096, 8443):
            raise Stop('Compose portlari beklenenden farkli; otomatik degistirilmedi.')
        if target == 8443 and (str(port.get('published')) != '8443' or port.get('host_ip') != '0.0.0.0' or port.get('protocol', 'tcp') != 'tcp'):
            raise Stop('Mevcut 8443 yayini beklenenden farkli; otomatik degistirilmedi.')
    return cfg


def check_tunnel_scope():
    ids = command(['docker', 'ps', '-aq', '--filter', 'label=com.docker.compose.project=mualiy-sui-tunnel']).stdout.split()
    if not ids:
        return
    if len(ids) != 1 or not all(re.fullmatch('[a-f0-9]{12,64}', i) for i in ids):
        raise Stop('Ayni adli baska tunnel projesi var; dokunulmadi.')
    labels = json.loads(command(['docker', 'inspect', '-f', '{{json .Config.Labels}}', ids[0]]).stdout)
    mounts = json.loads(command(['docker', 'inspect', '-f', '{{json .Mounts}}', ids[0]]).stdout)
    if labels.get('com.docker.compose.service') != 'connector' or not any(
            m.get('Destination') == '/run/secrets/tunnel-token' and
            m.get('Source') == str(LIVE / 'tunnel-token') for m in mounts):
        raise Stop('Mevcut tunnel containeri bu kuruluma ait degil; dokunulmadi.')
    if not (LIVE / '.managed').is_file() or (LIVE / '.managed').read_text().strip() != MARKER:
        raise Stop('Var olan tunnel projesinin yonetim isareti yok; dokunulmadi.')


class API:
    def __init__(self, user, password, base=BASE_URL):
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        self.http = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(self.jar))
        self.request('login', {'user': user, 'pass': password})

    def raw(self, action, data=None):
        headers = {'Origin': self.base, 'X-Requested-With': 'XMLHttpRequest'}
        body = None
        if data is not None:
            body = urllib.parse.urlencode(data).encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        req = urllib.request.Request(self.base + '/app/api/' + action, data=body, headers=headers)
        try:
            with self.http.open(req, timeout=45) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            raise Stop(f'Yerel panel API istegi reddedildi (HTTP {e.code}); sifren degistirilmedi.') from None

    def request(self, action, data=None):
        response = json.loads(self.raw(action, data))
        if not response.get('success'):
            raise Stop('Panel API islemi reddedildi: ' + action + '. Parola/config degeri ekrana basilmayacak.')
        return response.get('obj')

    def items(self, kind):
        return (self.request(kind) or {}).get(kind) or []

    def add(self, kind, obj, extra=None):
        print('Panel API: ' + kind + ' kaydi olusturuluyor...')
        payload = {'object': kind, 'action': 'new', 'data': json.dumps(obj)}
        if extra:
            payload.update(extra)
        return self.request('save', payload)


def configure_api(api, state, cert_path='/app/cert/mualiy-fullchain.pem', key_path='/app/cert/mualiy-privkey.pem', port=8443):
    tls_records = [t for t in api.items('tls') if t['name'] == TLS_NAME]
    if len(tls_records) > 1:
        raise Stop('Ayni adli birden fazla TLS profili var; degistirilmedi.')
    if not tls_records:
        api.add('tls', {'name': TLS_NAME,
            'server': {'enabled': True, 'server_name': DOMAIN, 'min_version': '1.2',
                       'certificate_path': cert_path, 'key_path': key_path},
            'client': {'enabled': True, 'server_name': DOMAIN, 'insecure': False}})
        tls_records = [t for t in api.items('tls') if t['name'] == TLS_NAME]
    tls_rec = tls_records[0]
    if tls_rec['server'].get('certificate_path') != cert_path or tls_rec['server'].get('key_path') != key_path:
        raise Stop('Ayni adli TLS profili baska sertifika kullaniyor; uzerine yazilmadi.')
    # S-UI starts a running inbound through sing-box before committing it. A
    # fresh Trojan inbound needs its first user at that point, so create the
    # client record first and pass its ID as initUsers while creating inbound.
    # Creating the inbound with an empty user list can be rejected by a real
    # running core even though a simplified local fixture accepts it.
    existing = [i for i in api.items('inbounds') if i['tag'] == TAG]
    if len(existing) > 1:
        raise Stop('Ayni tagli birden fazla inbound var; degistirilmedi.')
    clients = [c for c in api.items('clients') if c['name'] == state['client_name']]
    if len(clients) > 1:
        raise Stop('Ayni adli birden fazla client var; degistirilmedi.')
    if not clients:
        initial_inbounds = [existing[0]['id']] if existing else []
        api.add('clients', {'enable': True, 'name': state['client_name'],
            'remark': 'Mualiy', 'group': 'private', 'desc': 'Mualiy private Trojan',
            'config': {'trojan': {'name': state['client_name'], 'password': state['trojan_password']}},
            'inbounds': initial_inbounds, 'links': [], 'volume': 0, 'expiry': 0})
        clients = [c for c in api.items('clients') if c['name'] == state['client_name']]
    if len(clients) != 1:
        raise Stop('Beklenen tek Mualiy client kaydi olusturulamadi; degistirilmedi.')
    client = clients[0]
    if not existing:
        api.add('inbounds', {'type': 'trojan', 'tag': TAG, 'tls_id': tls_rec['id'],
            'listen': '0.0.0.0', 'listen_port': port,
            'addrs': [{'server': DOMAIN, 'server_port': port}], 'out_json': {}},
            {'initUsers': str(client['id'])})
        existing = [i for i in api.items('inbounds') if i['tag'] == TAG]
    if len(existing) != 1:
        raise Stop('Beklenen tek Mualiy inbound kaydi olusturulamadi; degistirilmedi.')
    inbound = existing[0]
    if inbound['type'] != 'trojan' or int(inbound['listen_port']) != port or inbound['tls_id'] != tls_rec['id']:
        raise Stop('Ayni tag baska inbound icin kullaniliyor; degistirilmedi.')
    detail = api.request('clients?id=' + str(client['id']))['clients'][0]
    if detail.get('config', {}).get('trojan', {}).get('password') != state['trojan_password'] or inbound['id'] not in detail.get('inbounds', []):
        raise Stop('Var olan client kaydi beklenenden farkli; uzerine yazilmadi.')
    settings = api.request('settings')
    sub_uri = 'https://sub.mualiy.net/sub/'
    if settings.get('subURI', '') not in ('', sub_uri):
        raise Stop('Mevcut abonelik adresi farkli; uzerine yazilmadi.')
    if settings.get('subURI') != sub_uri:
        api.request('save', {'object': 'settings', 'action': 'edit', 'data': json.dumps({'subURI': sub_uri})})
    state['inbound_id'] = inbound['id']
    state['tls_id'] = tls_rec['id']


def reconcile_core_if_missing_inbound(api, cid):
    """Clear an unsaved hot-added inbound before retrying its DB transaction."""
    if any(inbound.get('tag') == TAG for inbound in api.items('inbounds')):
        return False
    # S-UI adds a live inbound before its DB transaction commits. A failed
    # earlier attempt can therefore leave a private, unpersisted core inbound
    # with TAG. Restart only the already-verified panel to make its core match
    # the DB before retrying; this does not delete DB, cert, or live state.
    print('Kayitsiz onceki core durumu temizleniyor; yalniz mualiy-sui paneli DB ile yeniden baslatiliyor...')
    command(['docker', 'restart', '-t', '20', cid], timeout=90)
    deadline = time.monotonic() + 120
    last_error = None
    while time.monotonic() < deadline:
        try:
            panel_id()
            return True
        except Stop as error:
            last_error = error
            time.sleep(2)
    raise Stop('Yalniz mualiy-sui paneli yeniden baslatildi ama 120 saniyede healthy olmadi; tekrar API denemesi yapilmadi.') from last_error


def free_port_or_stop_old(cid):
    # If an existing managed panel is already published, a rerun may continue.
    bindings = json.loads(command(['docker', 'inspect', '-f', '{{json .HostConfig.PortBindings}}', cid]).stdout) or {}
    if any(b.get('HostPort') == '8443' for b in bindings.get('8443/tcp', []) or []):
        return
    ids = command(['docker', 'ps', '-q']).stdout.split()
    if ids:
        bindings_all = command(['docker', 'inspect', '-f', '{{json .HostConfig.PortBindings}}', *ids]).stdout
        for line in bindings_all.splitlines():
            for entries in (json.loads(line) or {}).values():
                if any(b.get('HostPort') == '8443' for b in entries or []):
                    raise Stop('8443 baska bir Docker containerinda yayinli; ona dokunulmadi.')
    listeners = command(['ss', '-H', '-lntp', '( sport = :8443 )']).stdout
    if listeners.strip():
        old = command(['systemctl', 'show', 'ozgur-trojan.service', '--property=ExecStart', '--value'], False).stdout
        pids = set(re.findall(r'pid=(\d+)', listeners))
        main = command(['systemctl', 'show', 'ozgur-trojan.service', '--property=MainPID', '--value'], False).stdout.strip()
        unit_text = command(['systemctl', 'cat', 'ozgur-trojan.service', '--no-pager'], False).stdout
        if len(pids) == 1 and main in pids and 'path=/opt/ozgur-vds/sing-box ;' in old and not re.search(r'docker|podman|cloudflared|mualiy-sui|ExecStop', unit_text + old):
            print('Onceden kaldirilmasini istedigin eski ozgur-trojan durduruluyor (dizinler silinmeyecek).')
            command(['systemctl', 'stop', 'ozgur-trojan.service'])
            command(['systemctl', 'disable', 'ozgur-trojan.service'])
        else:
            raise Stop('8443 baska/bilinmeyen surecte; korumak icin duruldu. Eski temizlik sonucunu paylas.')
    if command(['ss', '-H', '-lnt', '( sport = :8443 )']).stdout.strip():
        raise Stop('8443 hala dolu; hicbir surec ismine gore oldurulmedi.')


def check_access():
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        r = opener.open(urllib.request.Request('https://' + PANEL_HOST + '/app/', headers={'User-Agent':'MualiySetup/1.1'}), timeout=20)
    except urllib.error.HTTPError as e:
        r = e
    except (urllib.error.URLError, OSError):
        raise Stop('panel.mualiy.net DNS/HTTPS adresine erisilemedi. Once Access uygulamasi ve yeni tunnel hostname rotasini kaydet; DNS yayilinca ayni komutu tekrar dene.') from None
    location = r.headers.get('Location', '')
    host = urllib.parse.urlparse(location).hostname or ''
    if r.code not in (301, 302, 303, 307, 308) or not (host.endswith('.cloudflareaccess.com') or (host == PANEL_HOST and '/cdn-cgi/access/' in location)):
        raise Stop('panel.mualiy.net uzerinde Access giris yonlendirmesi dogrulanamadi. Once Access uygulamasi ve tunnel hostname kaydini olustur; panel korumasiz yayinlanmayacak.')
    print('Cloudflare Access giris katmani goruldu (izin politikasini dashboardda yalniz kendi e-postanla sinirla).')


def certbot(action, email=None):
    args = ['docker', 'run', '--rm', '--cap-drop=ALL', '--security-opt=no-new-privileges:true',
        '--mount', f'type=bind,src={LIVE}/letsencrypt,dst=/etc/letsencrypt',
        '--mount', f'type=bind,src={LIVE}/work,dst=/var/lib/letsencrypt',
        '--mount', f'type=bind,src={LIVE}/logs,dst=/var/log/letsencrypt',
        '--mount', f'type=bind,src={LIVE}/cloudflare.ini,dst=/run/cloudflare.ini,readonly', CERTBOT]
    if action == 'new':
        args += ['certonly', '--non-interactive', '--agree-tos', '--email', email,
                 '--dns-cloudflare', '--dns-cloudflare-credentials', '/run/cloudflare.ini',
                 '--dns-cloudflare-propagation-seconds', '30', '--cert-name', DOMAIN,
                 '--keep-until-expiring', '--key-type', 'ecdsa', '-d', DOMAIN]
    else:
        args += ['renew', '--cert-name', DOMAIN, '--non-interactive', '--no-random-sleep-on-renew']
    print('DNS-01 sertifika islemi; 80/443 kullanilmayacak...')
    command(args, timeout=900)


def deploy_cert():
    source = LIVE / 'letsencrypt/live' / DOMAIN
    cert, key = source / 'fullchain.pem', source / 'privkey.pem'
    command(['openssl', 'x509', '-in', cert, '-noout', '-checkhost', DOMAIN])
    command(['openssl', 'x509', '-in', cert, '-noout', '-checkend', '86400'])
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)  # Reject a mismatched key before replacing files.
    changed = False
    for src, name in ((cert, 'mualiy-fullchain.pem'), (key, 'mualiy-privkey.pem')):
        dest = ROOT / 'cert' / name
        contents = src.read_bytes()
        if not dest.exists() or dest.read_bytes() != contents:
            private_write(dest, contents, 0o640, 10001)
            changed = True
    return changed


def test_tls():
    context = ssl.create_default_context()
    with socket.create_connection(('127.0.0.1', 8443), timeout=10) as s:
        with context.wrap_socket(s, server_hostname=DOMAIN) as tls:
            print('Yerel Trojan TLS: CA + hostname dogrulandi; ' + tls.version())


def install_renewal():
    target = LIVE / 'mualiy-yayinla.py'
    if Path(__file__).resolve() != target:
        private_write(target, Path(__file__).read_bytes(), 0o700)
    units = {
        'mualiy-sui-cert.service': f'''# {MARKER}
[Unit]
Description=Mualiy S-UI certificate renewal only
After=docker.service network-online.target
Wants=network-online.target
[Service]
Type=oneshot
UMask=0077
ExecStart=/usr/bin/python3 {target} --renew
TimeoutStartSec=1200
''',
        'mualiy-sui-cert.timer': f'''# {MARKER}
[Unit]
Description=Mualiy S-UI daily certificate check
[Timer]
OnCalendar=*-*-* 04,16:20:00
RandomizedDelaySec=1800
Persistent=true
[Install]
WantedBy=timers.target
'''}
    for name, contents in units.items():
        path = Path('/etc/systemd/system') / name
        if path.exists() and MARKER not in path.read_text():
            raise Stop('Ayni adli baska sertifika birimi var; uzerine yazilmadi.')
        private_write(path, contents, 0o644)
    command(['systemctl', 'daemon-reload'])
    command(['systemctl', 'enable', '--now', 'mualiy-sui-cert.timer'])


def start_tunnel():
    cfg = {'name': 'mualiy-sui-tunnel', 'services': {'connector': {
        'image': CLOUDFLARED, 'user': '65532:65532', 'network_mode': 'host',
        'restart': 'unless-stopped', 'cap_drop': ['ALL'],
        'security_opt': ['no-new-privileges:true'],
        'command': ['tunnel', '--no-autoupdate', '--disable-path-normalization=false', '--protocol', 'http2',
                    'run', '--token-file', '/run/secrets/tunnel-token'],
        'volumes': [{'type': 'bind', 'source': str(LIVE / 'tunnel-token'), 'target': '/run/secrets/tunnel-token', 'read_only': True}],
        'logging': {'driver': 'json-file', 'options': {'max-size': '5m', 'max-file': '2'}}}}}
    path = LIVE / 'compose.tunnel.json'
    private_write(path, json.dumps(cfg, indent=2) + '\n')
    command(['docker', 'compose', '-p', 'mualiy-sui-tunnel', '-f', path, 'config', '--quiet'])
    command(['docker', 'compose', '-p', 'mualiy-sui-tunnel', '-f', path, 'up', '-d'], timeout=180)


def export_links(state):
    uri = 'trojan://' + state['trojan_password'] + '@' + DOMAIN + ':8443?security=tls&type=tcp&sni=' + DOMAIN + '&allowInsecure=0#Mualiy-Trojan'
    text = ('GIZLI — sohbete/screenshotlara koyma.\n\nTrojan linki:\n' + uri +
            '\n\nAbonelik (sub hostname rotasini ekledikten sonra):\nhttps://sub.mualiy.net/sub/' + state['client_name'] +
            '\n\nAndroid MikuBox: linki panodan ice aktar, VPN/TUN modunda baslat. Sertifika dogrulamasini kapatma.\n')
    private_write(LIVE / 'baglanti.txt', text)
    user = os.environ.get('SUDO_USER')
    if user and user != 'root':
        p = pwd.getpwnam(user)
        home = Path(p.pw_dir)
        if p.pw_uid and not home.is_symlink() and home.stat().st_uid == p.pw_uid:
            dest = Path(tempfile.mkdtemp(prefix='mualiy-baglanti-', dir=home))
            file = dest / 'baglanti.txt'
            private_write(file, text)
            os.chown(file, p.pw_uid, p.pw_gid)
            os.chown(dest, p.pw_uid, p.pw_gid)
            print('MikuBox icin gizli link dosyan (VDS dosya yoneticisinden ac): ' + str(file))
    print('Root-ozel link dosyasi: ' + str(LIVE / 'baglanti.txt'))


def apply():
    if not sys.stdin.isatty():
        raise Stop('Gizli girisler icin dosyayi dogrudan VDS terminalinde calistir; pipe kullanma.')
    cid, _ = panel_id()
    cfg = checked_config()
    check_tunnel_scope()
    addresses = {r[4][0] for r in socket.getaddrinfo(DOMAIN, 8443, socket.AF_INET, socket.SOCK_STREAM)}
    if addresses != {PUBLIC_IP}:
        raise Stop('vpn DNS A kaydi beklenen DNS-only VDS IP adresi degil; once vpn kaydini kontrol et.')
    check_access()  # Before starting any new connector or changing the panel.
    print('Mevcut panel kullanici adini ve YENI sifreni yalniz bu VDS terminaline gir.')
    user = input('Panel kullanici adi: ').strip()
    password = getpass.getpass('Panel sifresi (gorunmez, kaydedilmez): ')
    if password == 'admin':
        raise Stop('Varsayilan admin sifresiyle yayin yapilmaz; parola sifirlanmadi.')
    api = API(user, password)
    require_private_root()
    state_path = LIVE / 'state.json'
    if state_path.exists():
        state = json.loads(state_path.read_text())
    else:
        state = {'client_name': 'mualiy-' + secrets.token_hex(16), 'trojan_password': secrets.token_urlsafe(32)}
        save_state(state)
    if not (LIVE / 'panel-once.db').exists():
        backup = api.raw('getdb')
        if not backup.startswith(b'SQLite format 3\x00'):
            raise Stop('Tutarlı panel DB yedegi alinamadi; devam edilmedi.')
        private_write(LIVE / 'panel-once.db', backup)
        private_write(LIVE / 'compose-once.yaml', (ROOT / 'compose.yaml').read_bytes())
    if not (LIVE / 'cloudflare.ini').exists():
        token = getpass.getpass('Yalniz mualiy.net Zone:DNS:Edit API Token (gorunmez): ').strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{25,256}', token):
            raise Stop('DNS API token bicimi uygun degil; Global API Key kullanma.')
        private_write(LIVE / 'cloudflare.ini', 'dns_cloudflare_api_token = ' + token + '\n')
        del token
    if not (LIVE / 'tunnel-token').exists():
        token = getpass.getpass('YENI mualiy-panel tunnel token (gorunmez; sadece token): ').strip()
        try:
            decoded = json.loads(base64.b64decode(token + '=' * (-len(token) % 4)))
            if not all(decoded.get(k) for k in ('a', 't', 's')):
                raise ValueError()
        except (ValueError, TypeError):
            raise Stop('Tunnel token bicimi uygun degil. Komutun tamamini degil, --token sonrasindaki tokeni yapistir.') from None
        private_write(LIVE / 'tunnel-token', token + '\n', 0o640, 65532)
        del token
    if not state.get('email'):
        email = input('Sertifika icin e-posta: ').strip()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise Stop('Gecerli e-posta gerekli.')
        print('Let\'s Encrypt sartlari: https://letsencrypt.org/repository/')
        if input('Sertifika sartlarini kabul ediyor musun? [EVET]: ').strip().upper() != 'EVET':
            raise Stop('Sertifika islemi iptal edildi.')
        state['email'] = email
        save_state(state)
    for image in (CERTBOT, CLOUDFLARED):
        print('Sabit yardimci image indiriliyor; mevcut servisler guncellenmeyecek...')
        command(['docker', 'pull', '--platform', 'linux/amd64', image], timeout=900)
    certbot('new', state['email'])
    deploy_cert()
    free_port_or_stop_old(cid)
    api = API(user, password)  # Refresh a session after a slow image/ACME download.
    if reconcile_core_if_missing_inbound(api, cid):
        api = API(user, password)  # Container restart invalidates the local API session.
    configure_api(api, state)
    save_state(state)
    # Publish only Trojan; keep both admin/subscription loopback-only.
    svc = cfg['services']['panel']
    if not any(int(p['target']) == 8443 for p in svc.get('ports', [])):
        svc.setdefault('ports', []).append({'target': 8443, 'published': '8443', 'host_ip': '0.0.0.0', 'protocol': 'tcp'})
    svc['restart'] = 'unless-stopped'
    private_write(ROOT / 'compose.yaml', json.dumps(cfg, indent=2) + '\n', 0o640)
    compose('config', '--quiet')
    print('YALNIZ yeni mualiy-sui paneli 8443 yayini icin yeniden olusturuluyor; DB/parola ayni.')
    compose('up', '-d', '--no-deps', '--wait', '--wait-timeout', '120', 'panel')
    panel_id()
    test_tls()
    install_renewal()
    start_tunnel()
    export_links(state)
    state['local_tls_verified'] = True
    state['external_ingress_and_device_tun_verified'] = False
    save_state(state)
    print('\nHAZIRLANAN: https://panel.mualiy.net/app/ | Trojan vpn.mualiy.net:8443')
    print('Dashboardda yeni tunnel Connected olmali. Panelde once Access, sonra mevcut S-UI girisi gorunmeli.')
    print('Saglayici firewalli varsa TCP 8443 izin ver. SSH/80/443/Minecraft/ThinLinc ayarlarina dokunulmadi.')
    print('Yerel TLS dogrulandi; dis erisim, MikuBox TUN/cikis IP ve UDP testi cihazinda yapilmali.')


def renew():
    require_private_root()
    _, before = panel_id(False)
    certbot('renew')
    if deploy_cert() and before.get('Running'):
        cid, _ = panel_id(False)
        print('Yenilenen sertifika icin yalniz mualiy-sui paneli yeniden baslatiliyor.')
        command(['docker', 'restart', '-t', '20', cid], timeout=90)
    print('Sertifika yenileme kontrolu tamam.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--apply', action='store_true')
    group.add_argument('--renew', action='store_true')
    args = parser.parse_args()
    try:
        if os.geteuid() != 0:
            raise Stop('VDS terminalinde sudo python3 ile calistir.')
        os.umask(0o077)
        for tool in ('docker', 'systemctl', 'ss', 'openssl'):
            if shutil.which(tool) is None:
                raise Stop('Gerekli komut yok: ' + tool + '; otomatik paket kurulumu yapilmadi.')
        engine = command(['docker', 'version', '--format', '{{.Server.Version}}']).stdout.strip()
        if not re.match(r'^(2[89]|[3-9][0-9])\.', engine):
            raise Stop('Loopback korumasi icin Docker Engine 28+ gerekli; otomatik guncellenmedi.')
        fd = os.open('/run/lock/mualiy-sui-yayin.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if args.renew:
                renew()
            else:
                apply()
    except (Stop, OSError, ValueError, KeyError, subprocess.SubprocessError, EOFError) as e:
        if isinstance(e, Stop):
            print('DUR: ' + str(e), file=sys.stderr)
        else:
            print('DUR: ' + type(e).__name__ + '. Sir icerebilecek ham hata/config basilmayacak; bulundugun asamayi bildir.', file=sys.stderr)
        print('DB/parola sifirlanmadi. Islem kismen ilerlediyse dosyalari silme; ayni betik tekrar calistirilabilir.', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nIptal edildi; gizli dosyalari sohbete yukleme.', file=sys.stderr)
        return 130
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
