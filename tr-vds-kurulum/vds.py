#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Private native Trojan/TUN deployment and scoped, optional zapret2 integration."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import platform
import pwd
import secrets
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from download import core, zapret, private_new

APP = Path('/opt/ozgur-vds')
CONF = Path('/etc/ozgur-vds')
CLIENTS = Path('/root/ozgur-vds-clients')
ZCONF = Path('/etc/ozgur-zapret')
UNIT = Path('/etc/systemd/system/ozgur-trojan.service')
ZUNIT = Path('/etc/systemd/system/ozgur-zapret.service')
SERVICE_USER = 'ozgur-trojan'
ZUSER = 'ozgur-zapret'
TABLE = 'ozgur_vpn_zapret'
OWNER = 'ozgur-vds-managed-v1'
QNUM = 61234
MARK = '0x40000000'
BLOCKED = ['0.0.0.0/8','10.0.0.0/8','100.64.0.0/10','127.0.0.0/8',
 '169.254.0.0/16','172.16.0.0/12','192.0.0.0/24','192.0.2.0/24',
 '192.88.99.0/24','192.168.0.0/16','198.18.0.0/15','198.51.100.0/24',
 '203.0.113.0/24','224.0.0.0/4','240.0.0.0/4']


def run(args, *, check=True, quiet=False, timeout=120):
    # Never log full command/config text or use shell=True.
    return subprocess.run([str(x) for x in args], check=check, timeout=timeout,
                          capture_output=quiet, text=True)


def dump(path, obj, mode=0o600):
    private_new(path, json.dumps(obj, ensure_ascii=False, indent=2)+'\n', mode)


def endpoint(value):
    try:
        ip = ipaddress.IPv4Address(value.strip())
    except ValueError:
        raise ValueError('Bu ilk surum icin alan adi degil, VDSnin genel IPv4 adresi gerekli.')
    if not ip.is_global or ip.is_multicast:
        raise ValueError('Genel, tekil IPv4 adresi gerekli; yerel/CGNAT/ozel adres kullanma.')
    return str(ip)


def checked_port(value):
    value = int(value)
    if not 1024 <= value <= 65535 or value in (80,443):
        raise ValueError('1024-65535 arasinda ayri bir port gerekli; 80/443 korunur.')
    return value


def dns_server(detour=None):
    d = {'type':'https','tag':'public-doh','server':'1.1.1.1','server_port':443,
         'path':'/dns-query','tls':{'enabled':True,'server_name':'cloudflare-dns.com'}}
    if detour:
        d['detour'] = detour
    return d


def server_config(password, port, cert, key, listen='0.0.0.0'):
    return {
      'log':{'level':'warn','timestamp':True},
      'dns':{'servers':[dns_server()], 'final':'public-doh'},
      'inbounds':[{'type':'trojan','tag':'trojan-in','listen':listen,'listen_port':port,
        'users':[{'name':'owner','password':password}],
        'tls':{'enabled':True,'min_version':'1.3','handshake_timeout':'10s',
               'certificate_path':str(cert),'key_path':str(key)}}],
      'outbounds':[{'type':'direct','tag':'internet'}],
      'route':{'rules':[
        {'domain':['localhost','metadata.google.internal','instance-data.ec2.internal'],
         'domain_suffix':['.localhost','.local','.internal','.lan','.home','.invalid','.test'], 'action':'reject'},
        {'port':[25,465,587], 'action':'reject'},
        {'action':'resolve','server':'public-doh','strategy':'ipv4_only','timeout':'5s'},
        {'ip_cidr':BLOCKED,'action':'reject'},
        {'ip_is_private':True,'action':'reject'},
        {'ip_version':6,'action':'reject'}],
        'final':'internet','default_domain_resolver':{'server':'public-doh','strategy':'ipv4_only'}}}


def client_config(ip, port, password, cert_pem, tun=True, local_port=18980):
    # No direct fallback; all app TCP/UDP exits through Trojan. IPv6 captured then rejected.
    outbound = {'type':'trojan','tag':'trojan-out','server':ip,'server_port':port,
      'password':password,'tls':{'enabled':True,'server_name':ip,'insecure':False,
      'min_version':'1.3','certificate':cert_pem.splitlines()}}
    inbound = {'type':'tun','tag':'device-vpn','address':['172.19.0.1/30','fdfe:dcba:9876::1/126'],
               'mtu':1400,'auto_route':True,'strict_route':True,'dns_mode':'hijack'} if tun else {
               'type':'mixed','tag':'local-test','listen':'127.0.0.1','listen_port':local_port}
    return {'log':{'level':'warn','timestamp':True},
      'dns':{'servers':[dns_server('trojan-out')],'final':'public-doh',
             'rules':[{'query_type':['AAAA'],'action':'predefined','rcode':'NOERROR'}]},
      'inbounds':[inbound], 'outbounds':[outbound],
      'route':{'auto_detect_interface':True,'rules':[
        {'action':'sniff'}, {'protocol':'dns','action':'hijack-dns'},
        {'ip_version':6,'action':'reject'}], 'final':'trojan-out',
        'default_domain_resolver':{'server':'public-doh','strategy':'ipv4_only'}}}


def make_cert(directory, ip):
    directory = Path(directory)
    cert, key = directory/'server.crt', directory/'server.key'
    # Private directory and umask protect key even while openssl creates it.
    run(['openssl','req','-x509','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256',
         '-sha256','-nodes','-days','365','-subj','/CN=Ozgur VDS private endpoint',
         '-addext',f'subjectAltName=IP:{ip}',
         '-addext','basicConstraints=critical,CA:FALSE',
         '-addext','keyUsage=critical,digitalSignature',
         '-addext','extendedKeyUsage=serverAuth','-keyout',key,'-out',cert], quiet=True)
    os.chmod(key,0o600)
    return cert,key


def trojan_unit():
    return f'''[Unit]
Description=Private sing-box Trojan endpoint
Wants=network-online.target
After=network-online.target
[Service]
Type=simple
User={SERVICE_USER}
Group={SERVICE_USER}
ExecStartPre={APP}/sing-box check -c {CONF}/server.json
ExecStart={APP}/sing-box run -c {CONF}/server.json
Restart=on-failure
RestartSec=3
NoNewPrivileges=yes
CapabilityBoundingSet=
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
LockPersonality=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX AF_NETLINK
UMask=0077
LimitNOFILE=4096
TasksMax=256
MemoryMax=512M
[Install]
WantedBy=multi-user.target
'''


def nft_rules(uid, zuid):
    if not isinstance(uid,int) or not isinstance(zuid,int) or min(uid,zuid)<1:
        raise ValueError('Servisler ayri, root olmayan UID kullanmali.')
    return f'''table inet {TABLE} {{
 comment "{OWNER}";
 chain raw_out {{
  type filter hook output priority -401; policy accept;
  meta skuid {zuid} meta mark & {MARK} != 0 notrack
 }}
 chain scoped_post {{
  type filter hook postrouting priority srcnat + 1; policy accept;
  meta skuid {uid} oifname != "lo" meta mark & {MARK} == 0 tcp dport 443 ct original packets 1-20 counter queue num {QNUM} bypass
  meta skuid {uid} oifname != "lo" meta mark & {MARK} == 0 tcp dport 443 tcp flags & (fin | rst) != 0 counter queue num {QNUM} bypass
 }}
}}
'''


def zapret_args(base, hosts, profile='split', user=None):
    if profile not in ('split','disorder'):
        raise ValueError('Profil split veya disorder olmali.')
    base = Path(base)
    args = [str(base/'nfqws2'),f'--qnum={QNUM}',f'--fwmark={MARK}',
      f'--lua-init=@{base}/lua/zapret-lib.lua',f'--lua-init=@{base}/lua/zapret-antidpi.lua',
      '--filter-tcp=443','--filter-l7=tls',f'--hostlist={hosts}',
      '--payload=tls_client_hello',
      '--lua-desync='+('multisplit' if profile=='split' else 'multidisorder')+':pos=1,midsld']
    if user:
        args.insert(1,'--user='+user)
    return args


def zapret_unit(profile='split'):
    command = ' '.join(zapret_args(APP/'zapret2',ZCONF/'hosts.txt',profile,ZUSER))
    return f'''[Unit]
Description=Scoped zapret2 for private Trojan egress
Wants=network-online.target
After=network-online.target ozgur-trojan.service
[Service]
Type=simple
# nfqws2 drops to its dedicated user and retains NET_ADMIN/NET_RAW internally.
User=root
ExecStart={command}
ExecStartPost=/usr/bin/python3 {APP}/vds.py firewall-on
ExecStopPost=-/usr/bin/python3 {APP}/vds.py firewall-off
Restart=on-failure
RestartSec=3
NoNewPrivileges=yes
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_RAW CAP_SETUID CAP_SETGID CAP_SETPCAP
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
InaccessiblePaths={CONF}
RestrictSUIDSGID=yes
LockPersonality=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX AF_NETLINK
Environment=PYTHONDONTWRITEBYTECODE=1
UMask=0077
LimitNOFILE=1024
TasksMax=64
MemoryMax=256M
[Install]
WantedBy=multi-user.target
'''


def require_root():
    if os.geteuid()!=0:
        raise ValueError('Bu komut sudo/root gerektirir.')


def user_create(name):
    try:
        pwd.getpwnam(name)
    except KeyError:
        run(['useradd','--system','--user-group','--no-create-home','--home-dir','/nonexistent',
             '--shell','/usr/sbin/nologin',name])
    else:
        raise ValueError('Ayni adli hesap zaten var; baska hizmetle UID paylasmamak icin duruldu: '+name)
    return pwd.getpwnam(name)


def guard_new(paths):
    for p in paths:
        if p.exists() or p.is_symlink():
            raise ValueError(f'Var olan dosya/dizin uzerine yazilmaz: {p}')


def check_config(binary,path):
    # Core errors can echo config values: retain private, never print its full stderr.
    r = run([binary,'check','-c',path],check=False,quiet=True)
    if r.returncode:
        raise ValueError('sing-box yapilandirma kontrolu basarisiz; gizli icerik ekrana basilmayacak.')


def local_tls(cert,ip,port):
    ctx = ssl.create_default_context(cafile=str(cert))
    ctx.minimum_version=ssl.TLSVersion.TLSv1_3
    until=time.monotonic()+12
    while time.monotonic()<until:
        try:
            with socket.create_connection(('127.0.0.1',port),timeout=2) as s:
                with ctx.wrap_socket(s,server_hostname=ip):
                    return
        except (OSError,ssl.SSLError):
            time.sleep(.2)
    raise ValueError('Yerel TLS hazirlik kontrolu basarisiz. Servis durumu incelenmeli.')


def install(ip,port,apply=False):
    if not apply:
        raise ValueError('Gercek kurulum icin --apply gerekli.')
    require_root(); ip=endpoint(ip); port=checked_port(port)
    osrel=Path('/etc/os-release').read_text()
    if platform.machine()!='x86_64' or 'ID=ubuntu' not in osrel or 'VERSION_ID="24.04"' not in osrel:
        raise ValueError('Bu paket yalniz rapordaki Ubuntu 24.04 x86_64 icin hazirlandi.')
    for tool in ('openssl','systemctl','useradd','ss'):
        if not shutil.which(tool):
            raise ValueError('Gerekli arac eksik: '+tool+'; otomatik apt/upgrade yapilmadi.')
    guard_new([APP,CONF,CLIENTS,UNIT])
    with socket.socket() as s:
        s.bind(('0.0.0.0',port))
    p=user_create(SERVICE_USER)
    # No existing TLS ports, firewall, cloudflared, sysctl, DNS, or default routes are changed.
    APP.mkdir(mode=0o755); APP.chmod(0o755)
    CONF.mkdir(mode=0o750); CONF.chmod(0o750); os.chown(CONF,0,p.pw_gid)
    CLIENTS.mkdir(mode=0o700); CLIENTS.chmod(0o700)
    try:
        print('Resmi sing-box surumu SHA-256 ile dogrulanarak indiriliyor...')
        core(APP/'sing-box')
        for name in ('vds.py','download.py','versions.json','LICENSE','THIRD_PARTY_NOTICES.md'):
            shutil.copyfile(Path(__file__).with_name(name),APP/name)
            os.chmod(APP/name,0o644)
        cert,key=make_cert(CONF,ip)
        password=secrets.token_urlsafe(36)
        cfg=server_config(password,port,cert,key)
        rules=cfg['route']['rules']
        resolved=next(i for i,r in enumerate(rules) if r.get('action')=='resolve')
        rules.insert(resolved+1,{'ip_cidr':[ip+'/32'],'action':'reject'})
        dump(CONF/'server.json',cfg)
        for path in (cert,key,CONF/'server.json'):
            os.chown(path,0,p.pw_gid); os.chmod(path,0o640)
        dump(CONF/'state.json',{'format':1,'endpoint':ip,'port':port,'user':SERVICE_USER})
        client=client_config(ip,port,password,cert.read_text())
        dump(CLIENTS/'android-tun.json',client)
        check_config(APP/'sing-box',CONF/'server.json')
        check_config(APP/'sing-box',CLIENTS/'android-tun.json')
        private_new(UNIT,trojan_unit(),0o644)
        run(['systemctl','daemon-reload'])
        run(['systemctl','enable','--now',UNIT.name])
        local_tls(cert,ip,port)
    except Exception:
        if UNIT.exists():
            run(['systemctl','disable','--now',UNIT.name],check=False,quiet=True)
        print('Kurulum tamamlanamadi; yeni servis durduruldu. Kismi dosyalar inceleme icin korundu.',file=sys.stderr)
        raise
    print('Trojan servisi ve yerel TLS dogrulamasi hazir.')
    print(f'Port: TCP {port}. 80/443/cloudflared degistirilmedi.')
    print(f'Android gizli profili: {CLIENTS}/android-tun.json (parola icerir; sohbete gonderme).')
    print('Firewall/yonlendirici/saglayici tarafinda bu TCP portunu ayrica acman gerekebilir.')
    if shutil.which('ufw'):
        r=run(['ufw','status'],check=False,quiet=True)
        print('UFW: '+('aktif' if 'Status: active' in r.stdout else 'aktif oldugu dogrulanmadi'))
        if 'Status: active' in r.stdout:
            print(f'Acikca izin vermek istersen: sudo ufw allow {port}/tcp comment ozgur-vds')
    print(f'Tunel uzerinden ilk olcum: sudo python3 {APP}/vds.py test')


def state():
    s=json.loads((CONF/'state.json').read_text())
    if s.get('format')!=1 or s.get('user')!=SERVICE_USER:
        raise ValueError('Beklenen kurulum metaverisi bulunamadi.')
    endpoint(s['endpoint']); checked_port(s['port'])
    return s


def install_zapret(apply=False,profile='split'):
    if not apply:
        raise ValueError('zapret2 kurmak icin --apply gerekli.')
    require_root(); s=state()
    guard_new([APP/'zapret2',ZCONF,ZUNIT])
    for name in ('nft','modprobe'):
        if not shutil.which(name):
            raise ValueError(name+' eksik; nftables ve kmod paketlerini ayri adimda kur.')
    if run(['nft','list','table','inet',TABLE],check=False,quiet=True).returncode==0:
        raise ValueError('Ayni adli nft tablosu zaten var; dokunulmadi.')
    run(['modprobe','nfnetlink_queue'])
    queue_file=Path('/proc/net/netfilter/nfnetlink_queue')
    if queue_file.exists() and any(x.split() and x.split()[0]==str(QNUM) for x in queue_file.read_text().splitlines()):
        raise ValueError('Secilen NFQUEUE numarasi baska bir surecte kullaniliyor.')
    zp=user_create(ZUSER); tp=pwd.getpwnam(SERVICE_USER)
    ZCONF.mkdir(mode=0o750); ZCONF.chmod(0o750); os.chown(ZCONF,0,zp.pw_gid)
    backup=ZCONF/'firewall-before.txt'
    r=run(['nft','list','ruleset'],quiet=True)
    private_new(backup,r.stdout)
    print('Resmi zapret2 arsivi ve binary SHA-256 ile dogrulaniyor...')
    zapret(APP/'zapret2')
    private_new(ZCONF/'hosts.txt','wattpad.com\n',0o640)
    os.chown(ZCONF/'hosts.txt',0,zp.pw_gid)
    private_new(ZCONF/'rules.nft',nft_rules(tp.pw_uid,zp.pw_uid),0o640)
    os.chown(ZCONF/'rules.nft',0,zp.pw_gid)
    run(['nft','--check','--file',ZCONF/'rules.nft'])
    # --dry-run validates syntax; --intercept=0 ALSO loads actual Lua but creates no NFQUEUE.
    args=zapret_args(APP/'zapret2',ZCONF/'hosts.txt',profile,ZUSER)
    run(args+['--dry-run'],quiet=True)
    run(args+['--intercept=0'],quiet=True)
    private_new(ZUNIT,zapret_unit(profile),0o644)
    run(['systemctl','daemon-reload'])
    try:
        run(['systemctl','enable','--now',ZUNIT.name])
        run(['systemctl','is-active','--quiet',ZUNIT.name])
    except Exception:
        run(['systemctl','disable','--now',ZUNIT.name],check=False,quiet=True)
        firewall_off()
        raise
    print('zapret2 aktif: yalniz Trojan UID + disari TCP/443; hostlist yalniz wattpad.com.')
    print('Bu, Wattpadin acildigi veya DPI stratejisinin ISSne uydugu anlami DEGILDIR.')
    print(f'Yeniden olcum: sudo python3 {APP}/vds.py test')
    print('Geri alma: sudo systemctl disable --now ozgur-zapret.service')


def set_profile(profile,apply=False):
    if not apply:
        raise ValueError('Profil degisikligi icin --apply gerekli.')
    require_root(); state()
    if ZUNIT.is_symlink() or not ZUNIT.is_file():
        raise ValueError('Paket tarafindan uretilmis zapret2 servisi bulunamadi.')
    old=ZUNIT.read_text()
    if old not in (zapret_unit('split'),zapret_unit('disorder')):
        raise ValueError('Servis elle degistirilmis; otomatik uzerine yazilmadi.')
    new=zapret_unit(profile)
    args=zapret_args(APP/'zapret2',ZCONF/'hosts.txt',profile,ZUSER)
    run(args+['--dry-run'],quiet=True)
    run(args+['--intercept=0'],quiet=True)
    active=run(['systemctl','is-active','--quiet',ZUNIT.name],check=False,quiet=True).returncode==0
    backup=ZCONF/('unit-before-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+secrets.token_hex(3)+'.service')
    private_new(backup,old)
    fd,tmp=tempfile.mkstemp(prefix='.ozgur-zapret-',dir=ZUNIT.parent)
    try:
        with os.fdopen(fd,'w') as f:
            os.fchmod(f.fileno(),0o644);f.write(new)
        os.replace(tmp,ZUNIT)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    run(['systemctl','daemon-reload'])
    if active:run(['systemctl','restart',ZUNIT.name])
    print('zapret2 profili: '+profile+(' (servis yeniden baslatildi)' if active else ' (servis baslatilmadi)'))
    print(f'Karsilastirma: sudo python3 {APP}/vds.py test')


def firewall_on():
    require_root()
    until=time.monotonic()+10
    p=Path('/proc/net/netfilter/nfnetlink_queue')
    while time.monotonic()<until:
        if p.exists() and any(x.split() and x.split()[0]==str(QNUM) for x in p.read_text().splitlines()):
            break
        time.sleep(.1)
    else:
        raise ValueError('NFQUEUE hazir degil; nft kurali EKLENMEDI.')
    # Ownership: installer refused pre-existing tables; only this fixed table is ever removed.
    if run(['nft','list','table','inet',TABLE],check=False,quiet=True).returncode==0:
        raise ValueError('Beklenmeyen mevcut tablo; uzerine yazilmadi.')
    run(['nft','--file',ZCONF/'rules.nft'])


def firewall_off():
    require_root()
    r=run(['nft','--json','list','table','inet',TABLE],check=False,quiet=True)
    if r.returncode!=0:return
    tables=[x.get('table',{}) for x in json.loads(r.stdout).get('nftables',[])]
    owned=any(t.get('family')=='inet' and t.get('name')==TABLE and t.get('comment')==OWNER for t in tables)
    if not owned:
        raise ValueError('Tablonun paket sahiplik etiketi yok; silinmedi.')
    run(['nft','delete','table','inet',TABLE],quiet=True)


def test_tunnel():
    require_root(); s=state()
    server=json.loads((CONF/'server.json').read_text())
    password=server['inbounds'][0]['users'][0]['password']
    with socket.socket() as sk:
        sk.bind(('127.0.0.1',0)); local_port=sk.getsockname()[1]
    conf=client_config(s['endpoint'],s['port'],password,(CONF/'server.crt').read_text(),False,local_port)
    conf['outbounds'][0]['server']='127.0.0.1'
    report=[]
    with tempfile.TemporaryDirectory(prefix='ozgur-vds-test-') as td:
        td=Path(td); cp=td/'client.json';dump(cp,conf)
        with (td/'core.log').open('w') as log:
            p=subprocess.Popen([str(APP/'sing-box'),'run','-c',str(cp)],stdout=log,stderr=log)
            try:
                until=time.monotonic()+8
                while time.monotonic()<until:
                    if p.poll() is not None: raise ValueError('Yerel test istemcisi baslatilamadi.')
                    try:
                        with socket.create_connection(('127.0.0.1',local_port),timeout=.3): break
                    except OSError: time.sleep(.1)
                else: raise ValueError('Yerel test istemcisi dinlemeye gecmedi.')
                targets=[('discord','https://discord.com/api/v10/gateway'),
                         ('roblox','https://games.roblox.com/v1/games?universeIds=1'),
                         ('wattpad','https://www.wattpad.com/')]
                for name,url in targets:
                    cmd=['curl','--disable','--noproxy','','--proxy',f'socks5h://127.0.0.1:{local_port}',
                         '--proto','=https','--silent','--show-error','--connect-timeout','6','--max-time','20',
                         '--max-filesize','524288','--output','/dev/null','--write-out','HTTP=%{http_code} TLS=%{ssl_verify_result}',url]
                    r=run(cmd,check=False,quiet=True,timeout=25)
                    row={'target':name,'curl_exit':r.returncode,'result':r.stdout.strip(),
                         'error':r.stderr.strip()[:300]}
                    report.append(row)
                    print(f"{name}: {row['result']} curl_exit={r.returncode}")
                    if row['error']: print(row['error'])
            finally:
                p.terminate()
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.kill();p.wait()
    out=Path('/root')/('ozgur-vds-test-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+secrets.token_hex(3)+'.json')
    z=run(['systemctl','is-active',ZUNIT.name],check=False,quiet=True)
    dump(out,{'zapret_active':z.stdout.strip()=='active','results':report,
              'note':'Yalniz HTTP/TLS olcumu; Android/oyun/ses testi degil.'})
    print('Paylasilabilir olcum raporu (yine de once gozden gecir): '+str(out))
    good=all(r['curl_exit']==0 and r['result']=='HTTP=200 TLS=0' for r in report)
    print('HTTPS olcum ozeti: '+('3/3 HTTP200 ve TLS dogrulandi' if good else 'en az bir hedef basarisiz; raporu karsilastir'))
    return 0 if good else 1


def export_client(user):
    require_root()
    p=pwd.getpwnam(user)
    if p.pw_uid==0 or not Path(p.pw_dir).is_dir():
        raise ValueError('Normal kullanici hesabi gerekli.')
    home=Path(p.pw_dir)
    if home.is_symlink() or home.stat().st_uid!=p.pw_uid:
        raise ValueError('Kullanici ev dizini guvenli dogrulanamadi.')
    # New random directory, never overwrite or follow an existing profile symlink.
    dest=Path(tempfile.mkdtemp(prefix='ozgur-vds-client-',dir=home))
    dest.chmod(0o700)
    target=dest/'android-tun.json'
    private_new(target,(CLIENTS/'android-tun.json').read_bytes())
    os.chown(target,p.pw_uid,p.pw_gid); os.chown(dest,p.pw_uid,p.pw_gid)
    print('GIZLI Android profili: '+str(target))
    print('Yalniz kendi telefonuna SFTP ile aktar. Bu JSON dosyasini sohbete gonderme.')


def main():
    os.umask(0o077)
    os.environ.pop('SSLKEYLOGFILE',None)
    os.environ['LC_ALL']='C'
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('install');p.add_argument('--endpoint',required=True);p.add_argument('--port',type=int,default=8443);p.add_argument('--apply',action='store_true')
    p=sub.add_parser('zapret-install');p.add_argument('--apply',action='store_true');p.add_argument('--profile',choices=['split','disorder'],default='split')
    p=sub.add_parser('zapret-profile');p.add_argument('--apply',action='store_true');p.add_argument('--profile',choices=['split','disorder'],required=True)
    sub.add_parser('test');sub.add_parser('firewall-on');sub.add_parser('firewall-off')
    p=sub.add_parser('export-client');p.add_argument('--user',required=True)
    a=ap.parse_args()
    try:
        if a.command=='install':install(a.endpoint,a.port,a.apply)
        elif a.command=='zapret-install':install_zapret(a.apply,a.profile)
        elif a.command=='zapret-profile':set_profile(a.profile,a.apply)
        elif a.command=='test':raise SystemExit(test_tunnel())
        elif a.command=='firewall-on':firewall_on()
        elif a.command=='firewall-off':firewall_off()
        elif a.command=='export-client':export_client(a.user)
    except (ValueError,OSError,subprocess.SubprocessError) as e:
        # Do not echo subprocess args, private config text, or TLS keys.
        if isinstance(e,subprocess.SubprocessError):
            print('Islem basarisiz: alt komut tamamlanamadi. Gizli yapilandirma ekrana basilmadi.',file=sys.stderr)
        else:print('Hata: '+str(e),file=sys.stderr)
        raise SystemExit(1)

if __name__=='__main__': main()
