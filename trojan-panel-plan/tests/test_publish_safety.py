#!/usr/bin/env python3
"""Offline publication guards; never contacts Docker/systemd or Cloudflare."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('publish_guards',BASE/'mualiy-yayinla.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ORIGINAL_COMMAND=m.command
CID='a'*12
CFG={'name':'mualiy-sui','services':{'panel':{'image':m.PANEL_IMAGE,'user':'10001:10001',
     'ports':[{'target':2095,'published':'2095','host_ip':'127.0.0.1','protocol':'tcp'},
              {'target':2096,'published':'2096','host_ip':'127.0.0.1','protocol':'tcp'}]}}}

class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'.mualiy-managed').write_text('mualiy-sui-loopback-bootstrap-v1\n')
        (self.root/'db').mkdir();(self.root/'cert').mkdir();self.cfg=copy.deepcopy(CFG)
        p=patch.object(m,'ROOT',self.root);p.start();self.addCleanup(p.stop)
        p=patch.object(m,'LIVE',self.root/'private-live');p.start();self.addCleanup(p.stop)
        p=patch.object(m,'compose',side_effect=lambda *a:subprocess.CompletedProcess([],0,json.dumps(self.cfg),''));p.start();self.addCleanup(p.stop)

    def test_expected_config_accepted(self):
        self.assertEqual(m.checked_config()['name'],'mualiy-sui')
    def test_other_service_refused(self):
        self.cfg['services']['minecraft']={}
        with self.assertRaises(m.Stop):m.checked_config()
    def test_public_admin_refused(self):
        self.cfg['services']['panel']['ports'][0]['host_ip']='0.0.0.0'
        with self.assertRaises(m.Stop):m.checked_config()
    def test_unexpected_port_refused(self):
        self.cfg['services']['panel']['ports'].append({'target':443,'published':'443'})
        with self.assertRaises(m.Stop):m.checked_config()
    def test_wrong_trojan_binding_refused(self):
        self.cfg['services']['panel']['ports'].append({'target':8443,'published':'8444','host_ip':'0.0.0.0'})
        with self.assertRaises(m.Stop):m.checked_config()
    def test_symlink_database_refused(self):
        (self.root/'db').rmdir();(self.root/'db').symlink_to(self.root/'cert')
        with self.assertRaises(m.Stop):m.checked_config()
    def test_local_docker_socket_forced(self):
        with patch.dict(os.environ,{'DOCKER_HOST':'tcp://remote.invalid','DOCKER_CONTEXT':'remote','DOCKER_TLS_VERIFY':'1'}):
            with patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','')) as p:
                ORIGINAL_COMMAND(['docker','ps'])
                env=p.call_args.kwargs['env'];self.assertEqual(env['DOCKER_HOST'],'unix:///var/run/docker.sock')
                self.assertNotIn('DOCKER_CONTEXT',env);self.assertNotIn('DOCKER_TLS_VERIFY',env)
    def test_unknown_port_owner_not_stopped(self):
        calls=[]
        def run(args,*a,**kw):
            args=list(map(str,args));calls.append(args)
            if args[:2]==['docker','inspect']:out='{}'
            elif args[:3]==['docker','ps','-q']:out=''
            elif args[:2]==['ss','-H']:out='LISTEN pid=9999'
            elif '--property=ExecStart' in args:out='{ path=/opt/ozgur-vds/sing-box ; }'
            elif '--property=MainPID' in args:out='1111'
            elif args[:2]==['systemctl','cat']:out='[Service]\nExecStart=/opt/ozgur-vds/sing-box run\n'
            else:raise AssertionError('Unexpected destructive call: '+repr(args))
            return subprocess.CompletedProcess(args,0,out,'')
        with patch.object(m,'command',side_effect=run):
            with self.assertRaises(m.Stop):m.free_port_or_stop_old(CID)
        self.assertFalse(any(c[:2]==['systemctl','stop'] for c in calls))
    def test_other_docker_port_not_stopped(self):
        calls=[]
        def run(args,*a,**kw):
            args=list(map(str,args));calls.append(args)
            if args[:3]==['docker','ps','-q']:out='b'*12
            elif args[-1]==CID:out='{}'
            elif args[:2]==['docker','inspect']:out=json.dumps({'443/tcp':[{'HostPort':'8443'}]})
            else:raise AssertionError('Unexpected destructive call')
            return subprocess.CompletedProcess(args,0,out,'')
        with patch.object(m,'command',side_effect=run):
            with self.assertRaises(m.Stop):m.free_port_or_stop_old(CID)
        self.assertFalse(any(c[0]=='systemctl' for c in calls))
    def test_private_write_preserves_destination_on_symlink(self):
        real=self.root/'real';real.write_bytes(b'keep');link=self.root/'alias';link.symlink_to(real)
        with self.assertRaises(m.Stop):m.private_write(link,b'overwrite')
        self.assertEqual(real.read_bytes(),b'keep')
    def test_equal_cert_contents_with_wrong_metadata_are_rewritten(self):
        destination = self.root / 'cert' / 'mualiy-privkey.pem'
        destination.write_bytes(b'fixture-key')
        destination.chmod(0o600)
        self.assertTrue(m.cert_file_needs_rewrite(destination, b'fixture-key'))

    def test_cert_directory_repairs_only_verified_mount_source_metadata(self):
        cert_dir = self.root / 'cert'
        cert_dir.chmod(0o700)
        with patch.object(m.os, 'chown') as chown:
            m.normalize_cert_directory()
        chown.assert_called_once_with(cert_dir, 0, m.PANEL_GID)
        self.assertEqual(cert_dir.stat().st_mode & 0o777, 0o750)

    def test_panel_cert_readability_is_checked_as_panel_user(self):
        with patch.object(m, 'command', return_value=subprocess.CompletedProcess([], 0, '', '')) as command:
            m.ensure_panel_can_read_cert(CID)
        self.assertEqual(command.call_args.args[0], [
            'docker', 'exec', '--user', '10001:10001', CID, 'sh', '-c',
            'test -r /app/cert/mualiy-fullchain.pem && test -r /app/cert/mualiy-privkey.pem',
        ])
        self.assertFalse(command.call_args.kwargs['check'])

    def test_unreadable_panel_cert_stops_before_inbound_api_save(self):
        with patch.object(m, 'command', return_value=subprocess.CompletedProcess([], 1, '', '')):
            with self.assertRaises(m.Stop):
                m.ensure_panel_can_read_cert(CID)

    def test_acme_uses_credential_file_not_secret_argument(self):
        calls=[]
        with patch.object(m,'command',side_effect=lambda a,**kw:calls.append(a)):
            with contextlib.redirect_stdout(io.StringIO()):m.certbot('new','fixture@example.invalid')
        cmd=calls[0];self.assertIn('/run/cloudflare.ini',cmd)
        self.assertFalse(any('dns_cloudflare_api_token=' in str(a) for a in cmd))
    def access_response(self, status, location=''):
        error=m.urllib.error.HTTPError('https://panel.mualiy.net/app/',status,'fixture',{'Location':location},None)
        factory=patch.object(m.urllib.request,'build_opener')
        opener=factory.start();self.addCleanup(factory.stop)
        opener.return_value.open.side_effect=error
        return opener.return_value.open
    def test_access_check_uses_explicit_setup_identity(self):
        request=self.access_response(302,'https://neomualiy.cloudflareaccess.com/cdn-cgi/access/login/panel.mualiy.net')
        with contextlib.redirect_stdout(io.StringIO()):m.check_access()
        self.assertEqual(request.call_args.args[0].get_header('User-agent'),'MualiySetup/1.1')
    def test_access_403_still_refused(self):
        self.access_response(403)
        with self.assertRaises(m.Stop):m.check_access()
    def test_access_arbitrary_login_redirect_still_refused(self):
        self.access_response(302,'https://example.invalid/login')
        with self.assertRaises(m.Stop):m.check_access()
    def test_access_unprotected_200_still_refused(self):
        self.access_response(200)
        with self.assertRaises(m.Stop):m.check_access()
    def test_conflicting_tls_record_not_overwritten(self):
        class FakeAPI:
            def items(self,kind):return [{'id':1,'name':m.TLS_NAME,'server':{'certificate_path':'/other/cert','key_path':'/other/key'}}]
            def add(self,*a):raise AssertionError('must not mutate conflicting record')
        with self.assertRaises(m.Stop):m.configure_api(FakeAPI(),{'client_name':'fixture','trojan_password':'fixture'})

    def test_missing_database_inbound_restarts_only_verified_panel(self):
        class FakeAPI:
            def items(self, kind):
                if kind != 'inbounds':
                    raise AssertionError(kind)
                return []
        calls = []
        with patch.object(m, 'command', side_effect=lambda args, **kw: calls.append(args)), \
             patch.object(m, 'panel_id', return_value=(CID, {})) as panel:
            self.assertTrue(m.reconcile_core_if_missing_inbound(FakeAPI(), CID))
        self.assertEqual(calls, [['docker', 'restart', '-t', '20', CID]])
        panel.assert_called_once_with()

    def test_persisted_database_inbound_does_not_restart_panel(self):
        class FakeAPI:
            def items(self, kind):
                if kind != 'inbounds':
                    raise AssertionError(kind)
                return [{'tag': m.TAG}]
        with patch.object(m, 'command', side_effect=AssertionError('must not restart panel')):
            self.assertFalse(m.reconcile_core_if_missing_inbound(FakeAPI(), CID))

    def test_first_trojan_client_is_created_before_inbound(self):
        class FakeAPI:
            def __init__(self):
                self.events=[];self.clients=[];self.inbounds=[]
                self.tls=[{'id':1,'name':m.TLS_NAME,'server':{
                    'certificate_path':'/app/cert/mualiy-fullchain.pem',
                    'key_path':'/app/cert/mualiy-privkey.pem'}}]
            def items(self,kind):
                return {'tls':self.tls,'clients':self.clients,'inbounds':self.inbounds}[kind]
            def add(self,kind,obj,extra=None):
                self.events.append((kind,extra))
                if kind=='clients':
                    self.clients.append(dict(obj,id=7))
                elif kind=='inbounds':
                    self.assert_init_user(extra)
                    self.inbounds.append(dict(obj,id=9))
                    self.clients[0]['inbounds']=[9]
                else: raise AssertionError(kind)
            def assert_init_user(self,extra):
                if extra != {'initUsers':'7'}: raise AssertionError(extra)
            def request(self,action,data=None):
                if action=='settings': return {'subURI':''}
                if action=='clients?id=7': return {'clients':[self.clients[0]]}
                if action=='save': return None
                raise AssertionError(action)
        api=FakeAPI();state={'client_name':'fixture','trojan_password':'fixture-password'}
        m.configure_api(api,state)
        self.assertEqual(api.events,[('clients',None),('inbounds',{'initUsers':'7'})])
        self.assertEqual(state['inbound_id'],9)
        self.assertEqual(state['tls_id'],1)

if __name__=='__main__':unittest.main(verbosity=2)
