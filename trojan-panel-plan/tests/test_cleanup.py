#!/usr/bin/env python3
"""Offline old-service cleanup tests. No real systemctl/Docker commands run."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'mualiy-eski-servis-temizle.py'
spec = importlib.util.spec_from_file_location('retire_native_fixture', SCRIPT)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ORIGINAL_RUN = m.run
CID = 'c' * 64
OTHER = 'e' * 64

class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='mualiy-cleanup-test-')
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.old_umask = os.umask(0o077); self.addCleanup(os.umask,self.old_umask)
        self.panel = self.root/'opt/mualiy-sui'
        (self.panel/'db').mkdir(parents=True)
        self.secret = self.panel/'db/s-ui.db'; self.secret.write_bytes(b'new-panel-fixture-do-not-change')
        self.system = (self.root/'etc/systemd/system',self.root/'run/systemd/system')
        self.vendor = (self.root/'usr/lib/systemd/system',self.root/'lib/systemd/system')
        for p in self.system + self.vendor: p.mkdir(parents=True)
        self.old = tuple(self.root/str(p).lstrip('/') for p in m.OLD_DATA)
        for p in self.old:
            if p.name == 's-ui' and p.parent.name == 'bin':
                p.parent.mkdir(parents=True,exist_ok=True);p.write_text('old-cli-fixture')
            else:
                p.mkdir(parents=True,exist_ok=True);(p/'old-data').write_bytes(b'old-fixture')
        self.proc = self.root/'proc';self.proc.mkdir()
        self.backups = self.root/'root-backups';self.backups.mkdir()
        self.units={u:{'LoadState':'not-found','ActiveState':'inactive','UnitFileState':'','FragmentPath':''} for u in m.UNITS}
        unit='ozgur-trojan.service';f=self.system[0]/unit;f.write_text('old native unit fixture')
        self.units[unit]={'LoadState':'loaded','ActiveState':'active','UnitFileState':'disabled','FragmentPath':str(f)}
        self.helper={'LoadState':'not-found','ActiveState':'inactive','UnitFileState':'','FragmentPath':''}
        self.case='normal';self.calls=[];self.starters={};self.unit_contents={}
        for name,value in [('PANEL_ROOT',self.panel),('SYSTEM_DIRS',self.system),('VENDOR_DIRS',self.vendor),
                           ('OLD_DATA',self.old),('PROC_ROOT',self.proc),('BACKUP_ROOT',self.backups)]:
            p=patch.object(m,name,value);p.start();self.addCleanup(p.stop)
        p=patch.object(m.os,'geteuid',return_value=0);p.start();self.addCleanup(p.stop)
        p=patch.object(m,'run',side_effect=self.runner);p.start();self.addCleanup(p.stop)

    def result(self,args,stdout='',code=0,check=True):
        if code and check: raise m.Refuse('fixture command failure')
        return subprocess.CompletedProcess(args,code,stdout,'')

    def mounts(self,cid):
        if cid==CID:
            src=self.root/'unexpected-db' if self.case=='wrong_db' else self.panel/'db'
            return [{'Source':str(src),'Destination':'/app/db','Type':'bind'}]
        src=self.old[0]/'minecraft' if self.case=='old_is_mounted' else self.root/'crafty-data'
        return [{'Source':str(src),'Destination':'/crafty','Type':'bind'}]

    def runner(self,args,check=True):
        args=[str(a) for a in args];self.calls.append(args)
        if args[:2]==['docker','ps'] and args[2] in ('-q','-aq'):
            if '--filter' in args:return self.result(args, '' if self.case=='missing_panel' else CID+'\n')
            return self.result(args,CID+'\n'+OTHER+'\n')
        if args[:3]==['docker','inspect','--format']:
            fmt=args[3];ids=args[4:]
            if fmt=='{{json .State}}':
                return self.result(args,json.dumps({'Running':True,'Health':{'Status':'unhealthy' if self.case=='unhealthy' else 'healthy'}}))
            if fmt=='{{json .Mounts}}':
                return self.result(args,'\n'.join(json.dumps(self.mounts(cid)) for cid in ids))
        if args[:2]==['systemctl','show']:
            unit=args[2]
            info=self.helper if unit=='ozgur-zapret.service' else self.units[unit]
            if '--property=ExecStart' in args:
                binary = self.old[3]/'sui' if unit in ('s-ui.service','s.ui.service') else self.old[0]/'sing-box'
                text=self.starters.get(unit,'{ path='+str(binary)+' ; argv[]='+str(binary)+' run ; ignore_errors=no ; }')
                return self.result(args,text)
            return self.result(args,'\n'.join(k+'='+v for k,v in info.items())+'\n')
        if args[:2]==['systemctl','cat']:
            return self.result(args,self.unit_contents.get(args[2],'# fixture unit and drop-ins\n[Service]\n'))
        if args[:2]==['systemctl','stop']:
            if self.case=='stop_fails':return self.result(args,code=1,check=check)
            self.units[args[2]]['ActiveState']='inactive';return self.result(args)
        if args[:2]==['systemctl','disable']:
            self.units[args[2]]['UnitFileState']='disabled'
            for base in self.system:
                for parent in base.glob('*.wants'):
                    p=parent/args[2]
                    if os.path.lexists(p):p.unlink()
            return self.result(args)
        if args==['systemctl','daemon-reload']:
            for u,info in self.units.items():
                if not any(os.path.lexists(p/u) for p in self.system):
                    info.update(LoadState='not-found',ActiveState='inactive',UnitFileState='',FragmentPath='')
            return self.result(args)
        if args[:2]==['systemctl','reset-failed']:return self.result(args)
        if args[:2]==['mv','--']:
            src,dst=map(Path,args[2:]);self.assertIn(self.root,src.parents);self.assertIn(self.backups,dst.parents)
            if self.case=='move_fails':return self.result(args,code=1,check=check)
            shutil.move(str(src),str(dst));return self.result(args)
        if args[:3]==['ss','-H','-lntp']:
            return self.result(args,'LISTEN other-owner-8443' if self.case=='other_listener' else '')
        raise AssertionError('Unexpected/unscoped command: '+repr(args))

    def execute(self,apply=False):
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            return m.execute(apply)

    def assert_panel_kept(self):
        self.assertEqual(self.secret.read_bytes(),b'new-panel-fixture-do-not-change')
        self.assertFalse(any(c[:2] in (['docker','stop'],['docker','rm'],['docker','compose']) for c in self.calls))
        for c in self.calls:
            if c[:2] in (['systemctl','stop'],['systemctl','disable'],['systemctl','reset-failed']):
                self.assertIn(c[2],m.UNITS)

    def test_check_only(self):
        self.assertIsNone(self.execute(False));self.assertTrue(self.old[0].exists())
        self.assertFalse(list(self.backups.iterdir()));self.assertFalse(any(c[:2]==['systemctl','stop'] for c in self.calls));self.assert_panel_kept()

    def test_apply_archives_old_and_keeps_panel(self):
        backup=self.execute(True);self.assertTrue(backup.is_dir())
        self.assertFalse(self.old[0].exists());self.assertEqual(backup.stat().st_mode & 0o777,0o700)
        data=json.loads((backup/'manifest.json').read_text());self.assertIn(str(self.old[0]),data['moved_paths'])
        self.assertTrue((backup/'files'/str(self.old[0]).lstrip('/')/'old-data').is_file())
        snapshot=backup/'ozgur-trojan.service.snapshot.txt'
        self.assertTrue(snapshot.is_file());self.assertEqual(snapshot.stat().st_mode & 0o777,0o600)
        self.assertEqual(self.units['ozgur-trojan.service']['LoadState'],'not-found');self.assert_panel_kept()

    def test_missing_new_panel_aborts_before_stop(self):
        self.case='missing_panel'
        with self.assertRaises(m.Refuse):self.execute(True)
        self.assertFalse(any(c[:2]==['systemctl','stop'] for c in self.calls));self.assertTrue(self.old[0].exists());self.assert_panel_kept()

    def test_unhealthy_panel_aborts(self):
        self.case='unhealthy'
        with self.assertRaises(m.Refuse):self.execute(True)
        self.assertFalse(list(self.backups.iterdir()));self.assert_panel_kept()

    def test_wrong_database_aborts(self):
        self.case='wrong_db'
        with self.assertRaises(m.Refuse):self.execute(True)
        self.assertTrue(self.old[0].exists());self.assert_panel_kept()

    def test_other_container_mount_guard(self):
        self.case='old_is_mounted'
        with self.assertRaises(m.Refuse):self.execute(True)
        self.assertFalse(any(c[:2]==['systemctl','stop'] for c in self.calls));self.assert_panel_kept()

    def test_old_custom_zapret_dependency_aborts(self):
        self.helper.update(LoadState='loaded',ActiveState='inactive')
        with self.assertRaises(m.Refuse):self.execute(True)
        self.assertFalse(any(c[:2]==['systemctl','stop'] for c in self.calls));self.assert_panel_kept()

    def test_vendor_unit_guard(self):
        (self.vendor[0]/'sing-box.service').write_text('package-owned fixture')
        with self.assertRaises(m.Refuse):self.execute(True)
        self.assertFalse(any(c[:2]==['systemctl','stop'] for c in self.calls));self.assert_panel_kept()

    def test_new_panel_wrapper_guard(self):
        self.starters['ozgur-trojan.service']='docker compose -f '+str(self.panel/'compose.yaml')+' up'
        with self.assertRaises(m.Refuse):self.execute(True)
        self.assertFalse(any(c[:2]==['systemctl','stop'] for c in self.calls));self.assert_panel_kept()

    def test_unknown_execstart_guard(self):
        self.starters['ozgur-trojan.service']='{ path=/home/neo/unknown-wrapper.sh ; argv[]=/home/neo/unknown-wrapper.sh ; }'
        with self.assertRaises(m.Refuse):self.execute(True)
        self.assertFalse(any(c[:2]==['systemctl','stop'] for c in self.calls));self.assert_panel_kept()

    def test_panel_reference_in_dropin_guard(self):
        self.unit_contents['ozgur-trojan.service']='[Service]\nExecStop=/usr/bin/docker stop '+CID+'\n'
        with self.assertRaises(m.Refuse):self.execute(True)
        self.assertFalse(any(c[:2]==['systemctl','stop'] for c in self.calls));self.assert_panel_kept()

    def test_unrelated_docker_stop_in_unit_guard(self):
        self.unit_contents['ozgur-trojan.service']='[Service]\nExecStop=/usr/bin/docker stop another-container\n'
        with self.assertRaises(m.Refuse):self.execute(True)
        self.assertFalse(any(c[:2]==['systemctl','stop'] for c in self.calls));self.assert_panel_kept()

    def test_s_dot_ui_variant_is_in_scope(self):
        unit='s.ui.service';f=self.system[0]/unit;f.write_text('old sui fixture')
        self.units[unit]={'LoadState':'loaded','ActiveState':'active','UnitFileState':'disabled','FragmentPath':str(f)}
        self.execute(True);self.assertIn(['systemctl','stop',unit],self.calls);self.assertFalse(f.exists());self.assert_panel_kept()

    def test_nonstandard_fragment_guard(self):
        self.units['ozgur-trojan.service']['FragmentPath']=str(self.root/'somewhere/unknown.service')
        with self.assertRaises(m.Refuse):self.execute(True)
        self.assertTrue(self.old[0].exists());self.assert_panel_kept()

    def test_disable_enabled_old_unit(self):
        self.units['ozgur-trojan.service']['UnitFileState']='enabled'
        wants=self.system[0]/'multi-user.target.wants';wants.mkdir()
        (wants/'ozgur-trojan.service').symlink_to(self.system[0]/'ozgur-trojan.service')
        self.execute(True)
        self.assertIn(['systemctl','disable','ozgur-trojan.service'],self.calls);self.assert_panel_kept()

    def test_other_process_guard_after_stop(self):
        p=self.proc/'12345';p.mkdir();(p/'exe').symlink_to(self.old[0]/'sing-box');(p/'cwd').symlink_to(self.root)
        (p/'cmdline').write_bytes(b'fixture\0')
        with self.assertRaises(m.Refuse):self.execute(True)
        self.assertTrue(self.old[0].exists());self.assertEqual(self.units['ozgur-trojan.service']['ActiveState'],'inactive');self.assert_panel_kept()

    def test_stop_failure_preserves_files(self):
        self.case='stop_fails'
        with self.assertRaises(m.Refuse):self.execute(True)
        self.assertTrue(self.old[0].exists());self.assert_panel_kept()

    def test_move_failure_preserves_archive_and_panel(self):
        self.case='move_fails'
        with self.assertRaises(m.Refuse):self.execute(True)
        self.assertTrue(list(self.backups.iterdir()));self.assert_panel_kept()

    def test_another_8443_listener_not_killed(self):
        self.case='other_listener';self.execute(True);self.assert_panel_kept()
        self.assertFalse(any(c[0] in ('kill','pkill','killall') for c in self.calls))

    def test_real_run_forces_local_docker_without_real_execution(self):
        with patch.dict(os.environ,{'DOCKER_CONTEXT':'remote-fixture','DOCKER_HOST':'tcp://remote.invalid','DOCKER_TLS_VERIFY':'1'}):
            with patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','')) as process:
                ORIGINAL_RUN(['docker','ps'])
                env=process.call_args.kwargs['env']
                self.assertEqual(env['DOCKER_HOST'],'unix:///var/run/docker.sock')
                self.assertNotIn('DOCKER_CONTEXT',env);self.assertNotIn('DOCKER_TLS_VERIFY',env)

if __name__=='__main__':unittest.main(verbosity=2)
