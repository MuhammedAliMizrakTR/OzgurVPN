#!/usr/bin/env python3
"""Offline tests only. All network and service tools are mocked."""
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('vds-on-kontrol.sh')
MOCK = r'''#!/usr/bin/python3
import json, os, pathlib, sys
name=pathlib.Path(sys.argv[0]).name
args=sys.argv[1:]
with open(os.environ['MOCK_LOG'],'a') as f:
    f.write(json.dumps([name,args])+'\n')
if name=='curl':
    if '--version' in args:
        print('curl 8.0.0 MOCK\nProtocols: http https'); sys.exit(0)
    if '--help' in args:
        # More than a pipe buffer: the detector must not use grep -q with pipefail.
        print('--doh-url <URL>\n' + ('x'*1000+'\n')*150); sys.exit(0)
    assert args[0]=='--disable'
    assert '--noproxy' in args and '--output' in args
    assert '-k' not in args and '--insecure' not in args
    assert 'SSLKEYLOGFILE' not in os.environ
    assert '--location' not in args
    code=int(os.environ.get('MOCK_CURL_EXIT','0'))
    print('http=403 hedef_ip=203.0.113.5 tls_sonucu=0 sure=0.01s',end='')
    sys.exit(code)
if name=='ip':
    if os.environ.get('MOCK_IPV6','1')=='1': print('default via 2001:db8::1 dev eth0')
    sys.exit(0)
if name=='ss':
    print('LISTEN 0 128 0.0.0.0:443 0.0.0.0:*')
    print('LISTEN 0 128 [::]:8443 [::]:*')
    sys.exit(0)
if name=='getent':
    print('2001:db8::5 STREAM test' if 'ahostsv6' in args else '203.0.113.5 STREAM test')
    sys.exit(0)
if name=='systemctl':
    if args and args[0]=='is-active': print('inactive'); sys.exit(3)
    print('FORBIDDEN_SECRET_MARKER'); sys.exit(1)
if name=='pgrep': sys.exit(1)
if name=='systemd-detect-virt': print('kvm'); sys.exit(0)
if name=='modinfo': sys.exit(1)
if name=='cloudflared': print('cloudflared version MOCK'); sys.exit(0)
if name=='sing-box': print('sing-box version MOCK'); sys.exit(0)
if name in ('nft','iptables'): print(name+' MOCK'); sys.exit(0)
raise SystemExit(90)
'''

class PreflightTests(unittest.TestCase):
    def run_case(self, args=(), **env_vars):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        cwd=Path(td.name)
        bindir=cwd/'bin'; bindir.mkdir()
        log=cwd/'calls.jsonl'
        for name in ('curl','ip','ss','getent','systemctl','pgrep','systemd-detect-virt','modinfo','cloudflared','sing-box','nft','iptables'):
            p=bindir/name; p.write_text(MOCK); p.chmod(0o700)
        env={**os.environ,'PATH':str(bindir)+':/usr/bin:/bin','MOCK_LOG':str(log),
             'SSLKEYLOGFILE':str(cwd/'must-not-exist.keys'), **env_vars}
        r=subprocess.run(['/bin/bash',str(SCRIPT),*args],cwd=cwd,env=env,capture_output=True,text=True,timeout=25)
        calls=[json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
        return r,cwd,calls

    def test_bash_syntax(self):
        self.assertEqual(subprocess.run(['/bin/bash','-n',str(SCRIPT)],capture_output=True).returncode,0)

    def test_help_no_actions(self):
        r,cwd,calls=self.run_case(('--help',))
        self.assertEqual(r.returncode,0); self.assertFalse(calls)
        self.assertFalse(list(cwd.glob('vds-on-kontrol.*.txt')))

    def test_invalid_hostname_does_not_echo_token(self):
        r,cwd,calls=self.run_case(('--hostname','https://x.example/?token=PRIVATE_TOKEN'))
        self.assertEqual(r.returncode,2); self.assertFalse(calls)
        self.assertNotIn('PRIVATE_TOKEN',r.stdout+r.stderr)

    def test_no_network_no_report(self):
        r,cwd,calls=self.run_case(('--no-network','--stdout-only'))
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('--no-network nedeniyle',r.stdout)
        self.assertFalse(list(cwd.glob('vds-on-kontrol.*.txt')))
        self.assertFalse(any(n=='getent' or (n=='curl' and '--version' not in a) for n,a in calls))

    def test_private_report_and_hidden_bind_addresses(self):
        r,cwd,calls=self.run_case(('--no-network',))
        self.assertEqual(r.returncode,0,r.stderr)
        reports=list(cwd.glob('vds-on-kontrol.*.txt')); self.assertEqual(len(reports),1)
        self.assertEqual(stat.S_IMODE(reports[0].stat().st_mode),0o600)
        text=reports[0].read_text()
        self.assertIn('TCP 443: dinlemede',text)
        self.assertNotIn('0.0.0.0',text)
        self.assertNotIn('FORBIDDEN_SECRET_MARKER',text)
        self.assertTrue(all(a and a[0]=='is-active' for n,a in calls if n=='systemctl'))

    def test_ipv6_and_doh_probes(self):
        r,cwd,calls=self.run_case(('--stdout-only','--hostname','vpn.example.com'))
        self.assertEqual(r.returncode,0,r.stderr)
        probes=[a for n,a in calls if n=='curl' and '--write-out' in a]
        self.assertEqual(len(probes),13)
        self.assertEqual(sum('--doh-url' in a for a in probes),3)
        self.assertEqual(sum('-6' in a for a in probes),5)
        self.assertTrue(any(n=='getent' and a[-1]=='vpn.example.com' for n,a in calls))
        self.assertFalse((cwd/'must-not-exist.keys').exists())
        self.assertIn('ses/UDP',r.stdout)
        self.assertIn('Trojan/zapret2 KURULMADI',r.stdout)

    def test_probe_failure_continues_and_ipv6_is_optional(self):
        r,cwd,calls=self.run_case(('--stdout-only',),MOCK_CURL_EXIT='28',MOCK_IPV6='0')
        self.assertEqual(r.returncode,0,r.stderr)
        probes=[a for n,a in calls if n=='curl' and '--write-out' in a]
        self.assertEqual(len(probes),8)
        self.assertFalse(any('-6' in a for a in probes))
        self.assertEqual(r.stdout.count('curl_exit=28'),8)
        self.assertIn('Sonuclari yorumlama',r.stdout)

    def test_unknown_option_no_actions(self):
        r,cwd,calls=self.run_case(('--install',))
        self.assertEqual(r.returncode,2); self.assertFalse(calls)

if __name__=='__main__': unittest.main(verbosity=2)
