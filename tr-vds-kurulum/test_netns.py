#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Disposable local protocol test. MUST run in a fresh network namespace.
No actual VDS, Android, ISP censorship, public endpoint or remote site is tested.
Usage: sudo unshare --net python3 test_netns.py --inside --core PATH --zapret PATH
"""
import argparse
import copy
import http.server
import ipaddress
import json
import os
from pathlib import Path
import pwd
import shutil
import socket
import socketserver
import ssl
import struct
import subprocess
import sys
import tempfile
import threading
import time
import vds

TARGET='9.9.9.9'
SNI='www.wattpad.com'
RESULTS=[]


def sh(args):
    return subprocess.run([str(x) for x in args],check=True,capture_output=True,text=True,timeout=15)


def wait_file(p,process,seconds=8):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if Path(p).exists():return
        if process.poll() is not None:raise RuntimeError('Test subprocess exited before ready: '+str(process.returncode))
        time.sleep(.05)
    raise TimeoutError(str(p))


def wait_port(port,p):
    end=time.monotonic()+8
    while time.monotonic()<end:
        if p.poll() is not None:raise RuntimeError('Core exited: '+str(p.returncode))
        try:
            with socket.create_connection(('127.0.0.1',port),timeout=.2):return
        except OSError:time.sleep(.05)
    raise TimeoutError('local core')


def exact(s,n):
    b=b''
    while len(b)<n:
        part=s.recv(n-len(b))
        if not part:raise OSError('EOF')
        b+=part
    return b


def socks_start(port):
    s=socket.create_connection(('127.0.0.1',port),timeout=4);s.settimeout(4)
    s.sendall(b'\x05\x01\x00')
    if exact(s,2)!=b'\x05\x00':raise OSError('SOCKS negotiation')
    return s


def socks_reply(s):
    h=exact(s,4)
    if h[:2]!=b'\x05\x00':raise OSError('SOCKS request rejected')
    if h[3]==1:a=socket.inet_ntoa(exact(s,4))
    elif h[3]==4:a=socket.inet_ntop(socket.AF_INET6,exact(s,16))
    elif h[3]==3:a=exact(s,exact(s,1)[0]).decode()
    else:raise OSError('ATYP')
    return a,struct.unpack('!H',exact(s,2))[0]


def connect_via(port,host,target_port):
    s=socks_start(port)
    try:
        ip=ipaddress.ip_address(host)
        addr=(b'\x01' if ip.version==4 else b'\x04')+ip.packed
    except ValueError:
        encoded=host.encode();addr=b'\x03'+bytes([len(encoded)])+encoded
    s.sendall(b'\x05\x01\x00'+addr+struct.pack('!H',target_port))
    try:socks_reply(s)
    except Exception:s.close();raise
    return s


def https_via(port,crt):
    ctx=ssl.create_default_context(cafile=str(crt))
    raw=connect_via(port,TARGET,443)
    with ctx.wrap_socket(raw,server_hostname=SNI) as s:
        s.sendall(b'GET / HTTP/1.1\r\nHost: www.wattpad.com\r\nConnection: close\r\n\r\n')
        data=b''
        while True:
            b=s.recv(4096)
            if not b:break
            data+=b
    assert b'200 OK' in data and data.endswith(b'local-fixture-only\n'),data


def udp_via(port):
    tcp=socks_start(port)
    try:
        tcp.sendall(b'\x05\x03\x00\x01'+b'\x00'*6)
        a,p=socks_reply(tcp)
        if a=='0.0.0.0':a='127.0.0.1'
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as u:
            u.settimeout(4)
            payload=b'udp-through-trojan-'+os.urandom(12)
            header=b'\x00\x00\x00\x01'+socket.inet_aton(TARGET)+struct.pack('!H',28080)
            u.sendto(header+payload,(a,p));response,_=u.recvfrom(65535)
            assert response[3]==1 and response[10:]==payload,response
    finally:tcp.close()


def fixture_cert(path):
    sh(['openssl','req','-x509','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256',
        '-sha256','-nodes','-days','1','-subj','/CN=Local isolated test',
        '-addext','subjectAltName=DNS:'+SNI,'-addext','basicConstraints=critical,CA:FALSE',
        '-addext','keyUsage=critical,digitalSignature','-addext','extendedKeyUsage=serverAuth',
        '-keyout',path/'web.key','-out',path/'web.crt'])


def target_child(path):
    assert os.geteuid()==0 and os.readlink('/proc/self/ns/net')!=os.readlink(f'/proc/{os.getppid()}/ns/net'), 'isolated child namespace required'
    while not (path/'go').exists():time.sleep(.03)
    sh(['ip','link','set','lo','up']);sh(['ip','link','set','ozv1','up'])
    sh(['ip','addr','add','172.30.77.2/30','dev','ozv1'])
    sh(['ip','addr','add',TARGET+'/32','dev','lo'])
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            b=b'local-fixture-only\n';self.send_response(200);self.send_header('Content-Length',str(len(b)))
            self.end_headers();self.wfile.write(b)
        def log_message(self,*a):pass
    web=http.server.ThreadingHTTPServer((TARGET,443),H)
    ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(path/'web.crt',path/'web.key')
    web.socket=ctx.wrap_socket(web.socket,server_side=True)
    threading.Thread(target=web.serve_forever,daemon=True).start()
    u=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);u.bind((TARGET,28080))
    def echo():
        while True:
            b,a=u.recvfrom(65535);u.sendto(b,a)
    threading.Thread(target=echo,daemon=True).start()
    (path/'target-ready').write_text('ready')
    threading.Event().wait()


def expect_failure(fn):
    try:fn()
    except (OSError,ssl.SSLError,AssertionError):return
    raise AssertionError('Operation should have failed')


def main(args):
    assert os.geteuid()==0,'root required ONLY inside isolated test namespace'
    assert os.readlink('/proc/self/ns/net')!=os.readlink(f'/proc/{os.getppid()}/ns/net'), 'fresh net namespace required'
    nft=shutil.which('nft') or '/usr/sbin/nft'
    processes=[];logs=[]
    with tempfile.TemporaryDirectory(prefix='ozgur-protocol-test-') as tmp:
        path=Path(tmp);path.chmod(0o755)
        try:
            sh(['ip','link','set','lo','up'])
            fixture_cert(path)
            log=(path/'target.log').open('w');logs.append(log)
            target=subprocess.Popen(['unshare','--net',sys.executable,__file__,'--target',str(path)],stdout=log,stderr=log)
            processes.append(target)
            # Ensure unshare has entered its child network namespace before moving veth.
            end=time.monotonic()+5
            while time.monotonic()<end:
                if os.readlink(f'/proc/{target.pid}/ns/net')!=os.readlink('/proc/self/ns/net'):break
                time.sleep(.03)
            else:raise TimeoutError('nested namespace')
            sh(['ip','link','add','ozv0','type','veth','peer','name','ozv1'])
            sh(['ip','link','set','ozv1','netns',str(target.pid)])
            sh(['ip','addr','add','172.30.77.1/30','dev','ozv0']);sh(['ip','link','set','ozv0','up'])
            sh(['ip','route','add',TARGET+'/32','via','172.30.77.2','dev','ozv0'])
            (path/'go').write_text('go');wait_file(path/'target-ready',target)
            cert,key=vds.make_cert(path,'8.8.8.8')
            cert.chmod(0o644);key.chmod(0o644) # disposable fixture only, never production
            password=os.urandom(24).hex()
            cfg=vds.server_config(password,18443,cert,key,'127.0.0.1')
            def start_core(conf,name,port,uid=None):
                f=path/(name+'.json');f.write_text(json.dumps(conf));f.chmod(0o644)
                log=(path/(name+'.log')).open('w');logs.append(log)
                kw={}
                if uid is not None:kw={'user':uid,'group':uid,'extra_groups':[]}
                p=subprocess.Popen([args.core,'run','-c',str(f)],stdout=log,stderr=log,**kw)
                processes.append(p);wait_port(port,p);return p
            start_core(cfg,'server',18443,1000)
            client=vds.client_config('8.8.8.8',18443,password,cert.read_text(),False,18980)
            client['outbounds'][0]['server']='127.0.0.1'
            start_core(client,'client',18980)
            for name,c in [('server',cfg),('android',vds.client_config('8.8.8.8',18443,password,cert.read_text()))]:
                f=path/('check-'+name+'.json');f.write_text(json.dumps(c));sh([args.core,'check','-c',f])
            RESULTS.append('sing-box server + Android TUN schema accepted by 1.14.4')
            ctx=ssl.create_default_context(cafile=str(cert))
            with socket.create_connection(('127.0.0.1',18443)) as raw:
                with ctx.wrap_socket(raw,server_hostname='8.8.8.8'):pass
            RESULTS.append('Trojan TLS custom trust + correct IP SAN verified')
            def bad_host():
                with socket.create_connection(('127.0.0.1',18443)) as raw:
                    with ctx.wrap_socket(raw,server_hostname='8.8.4.4'):pass
            expect_failure(bad_host);RESULTS.append('wrong TLS identity rejected')
            default=ssl.create_default_context()
            def untrusted():
                with socket.create_connection(('127.0.0.1',18443)) as raw:
                    with default.wrap_socket(raw,server_hostname='8.8.8.8'):pass
            expect_failure(untrusted);RESULTS.append('untrusted TLS certificate rejected')
            https_via(18980,path/'web.crt');RESULTS.append('HTTPS/TCP payload relayed over authenticated Trojan')
            udp_via(18980);RESULTS.append('SOCKS UDP -> Trojan/TLS -> remote UDP echo returned exact payload')
            bad=copy.deepcopy(client);bad['inbounds'][0]['listen_port']=18981;bad['outbounds'][0]['password']='wrong-fixture-password'
            start_core(bad,'wrong-password',18981)
            expect_failure(lambda:https_via(18981,path/'web.crt'));RESULTS.append('wrong Trojan password cannot reach target')
            def private_probe():
                with connect_via(18980,'127.0.0.1',18443) as s:
                    s.sendall(b'private-probe');data=s.recv(10)
                    if not data:raise OSError('blocked')
            expect_failure(private_probe);RESULTS.append('loopback target rejected by server policy')
            # nft and nfqws run ONLY in this disposable namespace; no host firewall is touched.
            zbase=path/'zapret2';shutil.copytree(args.zapret,zbase)
            for parent,dirs,files in os.walk(zbase):
                os.chmod(parent,0o755)
                for f in files:os.chmod(Path(parent)/f,0o755 if f=='nfqws2' else 0o644)
            (path/'hosts.txt').write_text('wattpad.com\n');(path/'hosts.txt').chmod(0o644)
            rules=path/'rules.nft';rules.write_text(vds.nft_rules(1000,65534))
            sh([nft,'--check','--file',rules]);RESULTS.append('scoped nftables rules validated by real isolated kernel')
            sh([nft,'add','table','inet','preserve_me'])
            for profile in ('split','disorder'):
                zargs=vds.zapret_args(zbase,path/'hosts.txt',profile)
                zargs.insert(1,'--uid=65534:65534')
                sh(zargs+['--dry-run']);sh(zargs+['--intercept=0'])
                log=(path/('nfq-'+profile+'.log')).open('w');logs.append(log)
                restricted=['setpriv','--no-new-privs',
                            '--bounding-set=-all,+net_admin,+net_raw,+setuid,+setgid,+setpcap']
                z=subprocess.Popen(restricted+zargs,stdout=log,stderr=log);processes.append(z)
                queue=Path('/proc/net/netfilter/nfnetlink_queue')
                until=time.monotonic()+6
                while time.monotonic()<until:
                    if z.poll() is not None:raise RuntimeError('nfqws2 exited; see fixture log')
                    if queue.exists() and any(x.split() and x.split()[0]=='61234' for x in queue.read_text().splitlines()):break
                    time.sleep(.05)
                else:raise TimeoutError('NFQUEUE unavailable')
                sh([nft,'--file',rules])
                https_via(18980,path/'web.crt')
                r=json.loads(sh([nft,'--json','list','table','inet',vds.TABLE]).stdout)
                def count(obj):
                    if isinstance(obj,dict):
                        return sum((v.get('packets',0) if k=='counter' and isinstance(v,dict) else count(v)) for k,v in obj.items())
                    if isinstance(obj,list):return sum(count(x) for x in obj)
                    return 0
                before=count(r);assert before>0,'UID-scoped NFQUEUE did not receive packets'
                # Unrelated root-owned HTTPS egress must not enter the Trojan UID queue.
                raw=socket.create_connection((TARGET,443));webctx=ssl.create_default_context(cafile=str(path/'web.crt'))
                with webctx.wrap_socket(raw,server_hostname=SNI) as s:
                    s.sendall(b'GET / HTTP/1.0\r\nHost: www.wattpad.com\r\n\r\n')
                    while s.recv(4096):pass
                after=count(json.loads(sh([nft,'--json','list','table','inet',vds.TABLE]).stdout))
                # Close notifications of prior Trojan request may add a few final packets.
                assert after<=before+3,(before,after)
                RESULTS.append('real NFQUEUE + '+profile+' Lua loaded; scoped HTTPS relay succeeded')
                z.terminate();z.wait(timeout=5)
                https_via(18980,path/'web.crt');RESULTS.append(profile+': queue bypass kept Trojan working after nfqws2 stopped')
                vds.firewall_off();sh([nft,'list','table','inet','preserve_me'])
            RESULTS.append('rollback preserved unrelated nft table')
            sh([nft,'add','table','inet',vds.TABLE])
            try:vds.firewall_off()
            except ValueError:pass
            else:raise AssertionError('unowned table must not be deleted')
            sh([nft,'list','table','inet',vds.TABLE])
            RESULTS.append('rollback refused same-name table without package ownership marker')
        except Exception:
            for p in processes:
                if p.poll() is None:p.terminate()
            for p in processes:
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:p.kill();p.wait()
            for f in path.glob('*.log'):
                print('\nFIXTURE LOG '+f.name+'\n'+f.read_text()[-6000:],file=sys.stderr)
            raise
        finally:
            for p in reversed(processes):
                if p.poll() is None:
                    p.terminate()
                    try:p.wait(timeout=3)
                    except subprocess.TimeoutExpired:p.kill();p.wait()
            for f in logs:f.close()
    print(json.dumps({'passed':RESULTS,'count':len(RESULTS),
      'limits':['isolated Debian sandbox, not Ubuntu VDS','local synthetic HTTPS target, not actual Wattpad',
                'no actual Android TUN, DNS/IPv6 leak or kill-switch test','no censorship bypass assertion']},indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inside',action='store_true');ap.add_argument('--target')
    ap.add_argument('--core');ap.add_argument('--zapret')
    a=ap.parse_args()
    if a.target:target_child(Path(a.target))
    elif a.inside and a.core and a.zapret:main(a)
    else:ap.error('Use a fresh isolated namespace as shown in the module docstring.')
