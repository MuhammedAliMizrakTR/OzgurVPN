#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import download
import vds

class SafetyTests(unittest.TestCase):
    def test_endpoint_global_only(self):
        self.assertEqual(vds.endpoint(' 8.8.8.8 '),'8.8.8.8')
        for value in ('example.com','127.0.0.1','10.1.1.1','100.64.0.1','::1','224.0.0.1','1.2.3.4;id'):
            with self.subTest(value=value), self.assertRaises(ValueError):vds.endpoint(value)

    def test_port_preserves_web(self):
        self.assertEqual(vds.checked_port(8443),8443)
        for value in (80,443,0,65536,-1):
            with self.assertRaises(ValueError):vds.checked_port(value)

    def test_install_requires_explicit_apply_before_root_or_side_effect(self):
        with patch('vds.require_root',side_effect=AssertionError('must not execute')):
            with self.assertRaises(ValueError):vds.install('8.8.8.8',8443)
            with self.assertRaises(ValueError):vds.install_zapret()
            with self.assertRaises(ValueError):vds.set_profile('disorder')

    def test_private_file_umask_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'test'
            old=os.umask(0o077)
            try:download.private_new(p,b'public test',0o644)
            finally:os.umask(old)
            self.assertEqual(p.stat().st_mode & 0o777,0o644)
            with self.assertRaises(FileExistsError):download.private_new(p,b'changed')
            self.assertEqual(p.read_bytes(),b'public test')

    def test_no_symlink_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'target';p.write_text('old');link=Path(t)/'link';link.symlink_to(p)
            with self.assertRaises(OSError):download.private_new(link,'new')
            self.assertEqual(p.read_text(),'old')

    def test_guard_existing_path(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):vds.guard_new([Path(t)])
            p=Path(t)/'broken';p.symlink_to('/nonexistent-test-path')
            with self.assertRaises(ValueError):vds.guard_new([p])

    def test_download_hash_mismatch_rejected(self):
        class R:
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self,_):return b'invalid'
        with patch('download.urllib.request.urlopen',return_value=R()):
            with self.assertRaises(ValueError):download.blob('https://example.com/','0'*64)

    def test_download_size_limit(self):
        class R:
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self,_):return b'12345'
        with patch('download.urllib.request.urlopen',return_value=R()):
            with self.assertRaises(ValueError):download.blob('https://example.com/',hashlib.sha256(b'12345').hexdigest(),4)

    def test_tun_all_traffic_no_direct_or_split_apps(self):
        c=vds.client_config('8.8.8.8',8443,'unit-only','CERT')
        i=c['inbounds'][0]
        self.assertEqual(i['type'],'tun')
        self.assertTrue(i['auto_route']);self.assertTrue(i['strict_route'])
        self.assertEqual(i['dns_mode'],'hijack')
        self.assertEqual(len(i['address']),2)
        self.assertNotIn('include_package',i);self.assertNotIn('exclude_package',i)
        self.assertEqual([o['type'] for o in c['outbounds']],['trojan'])
        self.assertNotIn('network',c['outbounds'][0])
        self.assertEqual(c['route']['final'],'trojan-out')

    def test_tls_verified_no_insecure(self):
        c=vds.client_config('8.8.8.8',8443,'unit-only','CERT')
        tls=c['outbounds'][0]['tls']
        self.assertFalse(tls['insecure']);self.assertEqual(tls['server_name'],'8.8.8.8')
        self.assertIn('certificate',tls);self.assertNotIn('certificate_sha256',tls)

    def test_dns_tunneled_and_ipv6_deliberately_denied(self):
        c=vds.client_config('8.8.8.8',8443,'unit-only','CERT')
        self.assertEqual(c['dns']['servers'][0]['detour'],'trojan-out')
        self.assertTrue(any(r.get('ip_version')==6 and r['action']=='reject' for r in c['route']['rules']))
        self.assertEqual(c['dns']['rules'][0]['query_type'],['AAAA'])
        self.assertEqual(c['dns']['servers'][0]['tls']['server_name'],'cloudflare-dns.com')

    def test_server_denies_lan_metadata_smtp_ipv6(self):
        c=vds.server_config('unit-only',8443,'cert','key')
        r=c['route']['rules'];networks=[ipaddress.ip_network(x) for x in vds.BLOCKED]
        for target in ('127.0.0.1','169.254.169.254','192.168.1.1','100.100.100.200','10.0.0.1'):
            self.assertTrue(any(ipaddress.ip_address(target) in n for n in networks))
        self.assertTrue(any(x.get('port')==[25,465,587] and x['action']=='reject' for x in r))
        self.assertEqual(c['inbounds'][0]['users'][0]['password'],'unit-only')
        self.assertNotIn('network',c['inbounds'][0])

    def test_firewall_scope_no_flush_ssh_or_global_route(self):
        text=vds.nft_rules(123,124)
        self.assertIn('meta skuid 123',text)
        self.assertIn('tcp dport 443',text)
        self.assertIn('queue num 61234 bypass',text)
        self.assertIn('priority srcnat + 1',text)
        self.assertNotIn('flush',text);self.assertNotIn('dport 22',text)
        self.assertNotIn('drop',text);self.assertNotIn('udp dport',text)
        for uid in (0,-1,'123; delete table'):
            with self.assertRaises(ValueError):vds.nft_rules(uid,124)

    def test_units_dedicated_identity_and_key_isolation(self):
        s=vds.trojan_unit();z=vds.zapret_unit()
        self.assertIn('User=ozgur-trojan',s)
        self.assertIn('CapabilityBoundingSet=\n',s)
        self.assertIn('InaccessiblePaths=/etc/ozgur-vds',z)
        self.assertIn('--user=ozgur-zapret',z)
        self.assertIn('ExecStopPost=-/usr/bin/python3',z)
        self.assertNotIn('cloudflared',s+z)

    def test_zapret_profiles_allowlist_not_shell_text(self):
        a=vds.zapret_args('/opt/test','/etc/test','split')
        self.assertIn('--lua-desync=multisplit:pos=1,midsld',a)
        self.assertIn('--lua-desync=multidisorder:pos=1,midsld',vds.zapret_args('/opt/test','/etc/test','disorder'))
        with self.assertRaises(ValueError):vds.zapret_args('/a','/b','$(id)')

    def test_existing_service_account_not_reused(self):
        with patch('vds.pwd.getpwnam',return_value=object()), patch('vds.run',side_effect=AssertionError('must not execute')):
            with self.assertRaises(ValueError):vds.user_create('ozgur-trojan')

    def test_versions_locked(self):
        self.assertEqual(download.LOCK['sing_box']['version'],'1.14.4')
        self.assertEqual(download.LOCK['zapret2']['version'],'1.0.7')
        self.assertEqual(len(download.LOCK['zapret2']['sha256']),64)
        self.assertEqual(len(download.LOCK['zapret2']['binary_sha256']),64)

if __name__=='__main__':unittest.main(verbosity=2)
