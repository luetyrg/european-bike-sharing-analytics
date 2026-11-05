"""Start, stop, or initialize only the bike-redash Docker Compose project."""
import argparse
import subprocess
import sys
import shutil
import time
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
docker=shutil.which('docker') or r'C:\Program Files\Docker\Docker\resources\bin\docker.exe'

def compose(*args,input=None):
    subprocess.run([docker,'compose','-f',str(ROOT/'compose.yaml'),*args],input=input,check=True,cwd=ROOT)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['start','stop','setup'])
    p.add_argument('--source',type=Path)
    args=p.parse_args()
    if args.action=='stop':
        compose('stop')
        return
    if args.action=='setup':
        subprocess.run([sys.executable,str(ROOT/'scripts/init_secrets.py')],check=True)
        if args.source:
            subprocess.run([sys.executable,str(ROOT/'scripts/export_marts.py'),'--source',str(args.source)],check=True)
        else:
            subprocess.run([sys.executable,str(ROOT/'scripts/prepare_imports.py')],check=True)
        (ROOT/'private').mkdir(exist_ok=True)
        compose('up','-d','--wait','postgres','redis')
        compose('exec','-T','postgres','psql','-U','redash','-d','redash','-v','ON_ERROR_STOP=1',input=(ROOT/'sql/schema.sql').read_bytes())
        compose('run','--rm','server','create_db')
    compose('up','-d')
    if args.action=='setup':
        deadline=time.monotonic()+120
        while True:
            try:
                with urllib.request.urlopen('http://127.0.0.1:5001/ping',timeout=5) as r:
                    if r.status==200: break
            except Exception:
                if time.monotonic()>deadline: raise
                time.sleep(2)
        compose('exec','-T','server','python','/bootstrap/bootstrap_local.py')
        subprocess.run([sys.executable,str(ROOT/'scripts/build_dashboard.py')],check=True)
        subprocess.run([sys.executable,str(ROOT/'scripts/polish_dashboard.py')],check=True)
    print('Redash: http://localhost:5001')

if __name__=='__main__': main()
