#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional local live relay check; contacts three public HTTPS sites.
This is not the target VDS or Android acceptance test. No firewall/systemd changes.
Usage: python3 test_internet.py --core /path/to/sing-box
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import vds


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]


def main(core):
    results=[];processes=[];logs=[]
    with tempfile.TemporaryDirectory(prefix='ozgur-live-relay-') as d:
        path=Path(d);path.chmod(0o700)
        cert,key=vds.make_cert(path,'8.8.8.8')
        sp=free_port();cp=free_port()
        while cp==sp:cp=free_port()
        password=os.urandom(32).hex()
        server=vds.server_config(password,sp,cert,key,'127.0.0.1')
        client=vds.client_config('8.8.8.8',sp,password,cert.read_text(),False,cp)
        client['outbounds'][0]['server']='127.0.0.1'
        try:
            for name,config in [('server',server),('client',client)]:
                f=path/(name+'.json');vds.dump(f,config)
                log=(path/(name+'.log')).open('w');logs.append(log)
                p=subprocess.Popen([core,'run','-c',str(f)],stdout=log,stderr=log);processes.append(p)
            end=time.monotonic()+5
            while time.monotonic()<end:
                if any(p.poll() is not None for p in processes):raise RuntimeError('Local core exited.')
                try:
                    with socket.create_connection(('127.0.0.1',cp),timeout=.2):break
                except OSError:time.sleep(.05)
            else:raise TimeoutError('Local core not ready.')
            targets=[('discord','https://discord.com/api/v10/gateway'),
                     ('roblox','https://games.roblox.com/v1/games?universeIds=1'),
                     ('wattpad','https://www.wattpad.com/')]
            for name,url in targets:
                r=subprocess.run(['curl','--disable','--noproxy','','--proxy',f'socks5h://127.0.0.1:{cp}',
                    '--proto','=https','--silent','--show-error','--max-time','20','--max-filesize','524288',
                    '--output','/dev/null','--write-out','HTTP=%{http_code} TLS=%{ssl_verify_result}',url],
                    capture_output=True,text=True,timeout=25)
                results.append({'target':name,'curl_exit':r.returncode,'result':r.stdout,'error':r.stderr.strip()})
        finally:
            for p in processes:
                p.terminate()
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.kill();p.wait()
            for log in logs:log.close()
    print(json.dumps({'environment':'machine running this script, NOT automatically the user VDS',
                     'zapret':False,'results':results},indent=2))
    return int(any(x['curl_exit']!=0 or x['result']!='HTTP=200 TLS=0' for x in results))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--core',required=True)
    raise SystemExit(main(p.parse_args().core))
