#!/usr/bin/env python3
"""Offline fixture tests only: Docker and curl are mocks, no daemon is used.
Run as root to exercise the script's root-only installer in temporary fixtures.
The fixture rewrites TARGET and the lock path before executing it.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'mualiy-sui-panel.sh'
SOURCE = SCRIPT.read_text()
MOCK = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
args=sys.argv[1:]
tool=pathlib.Path(sys.argv[0]).name
with open(os.environ['MOCK_LOG'],'a') as f: f.write(json.dumps([tool]+args)+'\n')
case=os.environ.get('MOCK_CASE','normal')
if tool=='ss':
    if case=='busy_socket': print('LISTEN 0 4096 127.0.0.1:2095 0.0.0.0:*')
    sys.exit(0)
if tool=='curl':
    if case=='bad_http': sys.exit(22)
    print('Yerel panel HTTP=200')
    sys.exit(0)
if tool!='docker': raise SystemExit(99)
if args[:1]==['version']:
    print('27.5.0' if case=='old_docker' else '29.9.3'); sys.exit(0)
if args==['compose','version']:
    print('Docker Compose version v5.7.1'); sys.exit(0)
if args[:2]==['ps','-aq']:
    if case=='old_project': print('fixture-existing-container')
    sys.exit(0)
if args[:2]==['ps','--format']:
    if case=='busy_docker_range': print('127.0.0.1:2090-2100->2090-2100/tcp')
    elif case=='busy_docker_ipv6': print('[::]:2095->2095/tcp')
    elif case=='exposed_only': print('2095/tcp, 2096/tcp, 8443/tcp')
    else: print('8443/tcp, 0.0.0.0:25565->25565/tcp, [::]:19140-19159->19140-19159/udp')
    sys.exit(0)
if args[:1]==['pull']:
    sys.exit(1 if case=='bad_pull' else 0)
if args[:1]==['compose']:
    assert args[1:3]==['--project-name','mualiy-sui'], args
    f=pathlib.Path(args[args.index('--file')+1]); assert f.is_file(), f
    if 'config' in args and '--quiet' in args: sys.exit(0)
    if 'up' in args:
        assert '--wait' in args and '--wait-timeout' in args, args
        sys.exit(1 if case=='bad_up' else 0)
    if args[-1:] == ['stop']: sys.exit(0)
raise SystemExit('UNEXPECTED MOCK COMMAND: '+repr([tool]+args))
'''

class BootstrapTests(unittest.TestCase):
    def run_case(self, case='normal', mode='--apply', existing_target=False):
        self.assertEqual(os.geteuid(), 0, 'Use sudo -n python3 for isolated fixture tests.')
        with tempfile.TemporaryDirectory(prefix='mualiy-panel-test-') as d:
            root=Path(d); target=root/'installed'; bindir=root/'mockbin';bindir.mkdir()
            for name in ['docker','ss','curl']:
                p=bindir/name;p.write_text(MOCK);p.chmod(0o755)
            source=SOURCE.replace('TARGET=/opt/mualiy-sui\n', f'TARGET={target}\n', 1)
            self.assertNotEqual(source,SOURCE)
            source=source.replace('/run/lock/mualiy-sui-panel.lock',str(root/'install.lock'))
            script=root/'installer.sh';script.write_text(source)
            log=root/'calls.jsonl';log.touch()
            if existing_target: target.mkdir()
            env=dict(os.environ, PATH=str(bindir)+':'+os.environ['PATH'],
                     MOCK_LOG=str(log), MOCK_CASE=case)
            r=subprocess.run(['bash',str(script),mode],env=env,text=True,capture_output=True,timeout=15)
            calls=[json.loads(x) for x in log.read_text().splitlines()]
            files=[str(x.relative_to(target)) for x in target.rglob('*')] if target.exists() else []
            return r,calls,target.exists(),files

    def assert_no_deploy(self,calls):
        self.assertFalse(any(c[:2]==['docker','pull'] for c in calls), calls)
        self.assertFalse(any(c[:2]==['docker','compose'] and 'up' in c for c in calls), calls)

    def test_shell_syntax(self):
        subprocess.run(['bash','-n',str(SCRIPT)],check=True)

    def test_default_check_no_deploy(self):
        r,c,exists,_=self.run_case(mode='--check')
        self.assertEqual(r.returncode,0,r.stderr);self.assertFalse(exists);self.assert_no_deploy(c)

    def test_apply(self):
        r,c,exists,files=self.run_case()
        self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(exists)
        self.assertIn('compose.yaml',files);self.assertIn('.mualiy-managed',files)
        self.assertEqual(sum('up' in a for a in c),1,c)
        self.assertFalse(any(a[-1:] == ['stop'] for a in c),c)

    def test_refuse_existing_directory(self):
        r,c,exists,_=self.run_case(existing_target=True)
        self.assertNotEqual(r.returncode,0);self.assertTrue(exists);self.assert_no_deploy(c)

    def test_socket_collision(self):
        r,c,exists,_=self.run_case('busy_socket')
        self.assertNotEqual(r.returncode,0);self.assertFalse(exists);self.assert_no_deploy(c)

    def test_published_range_collision(self):
        r,c,exists,_=self.run_case('busy_docker_range')
        self.assertNotEqual(r.returncode,0);self.assertFalse(exists);self.assert_no_deploy(c)

    def test_ipv6_published_collision(self):
        r,c,exists,_=self.run_case('busy_docker_ipv6')
        self.assertNotEqual(r.returncode,0);self.assertFalse(exists);self.assert_no_deploy(c)

    def test_exposed_not_published(self):
        r,c,exists,_=self.run_case('exposed_only')
        self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(exists)

    def test_old_engine(self):
        r,c,exists,_=self.run_case('old_docker')
        self.assertNotEqual(r.returncode,0);self.assertFalse(exists);self.assert_no_deploy(c)

    def test_existing_project(self):
        r,c,exists,_=self.run_case('old_project')
        self.assertNotEqual(r.returncode,0);self.assertFalse(exists);self.assert_no_deploy(c)

    def test_pull_failure_no_persistent_install(self):
        r,c,exists,_=self.run_case('bad_pull')
        self.assertNotEqual(r.returncode,0);self.assertFalse(exists)
        self.assertFalse(any('up' in a for a in c))

    def test_health_failure_stops_only_our_project(self):
        r,c,exists,files=self.run_case('bad_http')
        self.assertNotEqual(r.returncode,0);self.assertTrue(exists)
        stops=[a for a in c if a[-1:]==['stop']]
        self.assertEqual(len(stops),1,c);self.assertIn('mualiy-sui',stops[0]);self.assertIn('compose.yaml',files)

    def test_up_failure_stops_only_our_project(self):
        r,c,exists,files=self.run_case('bad_up')
        self.assertNotEqual(r.returncode,0);self.assertTrue(exists)
        self.assertEqual(sum(a[-1:]==['stop'] for a in c),1,c)
        self.assertIn('compose.yaml',files)

    def test_invalid_mode_does_not_deploy(self):
        r,c,exists,_=self.run_case(mode='--invalid')
        self.assertNotEqual(r.returncode,0);self.assertFalse(exists);self.assertEqual(c,[])

if __name__=='__main__':
    unittest.main(verbosity=2)
