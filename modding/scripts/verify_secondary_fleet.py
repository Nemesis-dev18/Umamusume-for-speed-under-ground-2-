"""Exercise staged garment models, parser, solver and the existing runtime hook without NFS."""
import json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
from verify_runtime import ROOT,RUNTIME,CC,FLAGS,WINE,WORK,run
from fleet_carrier import carrier
from fleet_anchors import profiles

def main():
 for test in ('test_secondary_metadata.py','test_secondary_fleet_pack.py'):
  run([sys.executable,'-m','unittest','discover','-s','modding/tests','-p',test])
 rows=[];plan=json.loads((ROOT/'modding/secondary-fleet-plan.json').read_text());anchors=profiles()
 for row in plan['characters']:
  folder=ROOT/row['candidate_folder'];r=run([RUNTIME/'test-build/secondary-test',folder/'model-atlas.umab',folder/'secondary.bin'],capture_output=True,text=True);rows.append({'id':row['id'],'output':r.stdout.strip()})
 run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',RUNTIME/'secondary_stretch_test.c','-lm','-o',RUNTIME/'test-build/secondary-stretch-test'])
 cape=ROOT/'modding/staged-runtime/fleet-secondary/1062';names=json.loads((cape/'model.json').read_text())['bone_names'];mask=cape/'mantle-mask.bin';mask.write_bytes(bytes(int('Mantle' in n) for n in names))
 stretch=run([RUNTIME/'test-build/secondary-stretch-test',cape/'model-atlas.umab',cape/'secondary.bin',mask],capture_output=True,text=True).stdout.strip()
 run([CC,*FLAGS,RUNTIME/'runner_fleet_test.c','-o',RUNTIME/'test-build/secondary-routing-test.exe','-ld3d9','-luser32','-lwinmm','-lm'])
 with tempfile.TemporaryDirectory(prefix='secondary-route-',dir=RUNTIME) as tmp:
  fixture=Path(tmp)
  for row in plan['characters']:
   i=row['id'];source=ROOT/row['candidate_folder'];destination=fixture/'modding/runtime/fleet'/str(i);destination.mkdir(parents=True)
   for old,new in [('model-atlas.umab','model.umab'),('atlas.dds','atlas.dds'),('secondary.bin','secondary.bin')]:shutil.copyfile(source/old,destination/new)
   (destination/'carrier.bin').write_bytes(carrier(i));(destination/'anchors.bin').write_bytes(anchors[i]['bytes'])
  try:
   r=run([WINE,RUNTIME/'test-build/secondary-routing-test.exe',str(fixture.relative_to(ROOT)).replace('/','\\')],env=dict(os.environ,WINEPREFIX=str(WORK/'proton-prefix/pfx'),WINEDEBUG='-all'),capture_output=True,text=True)
  except subprocess.CalledProcessError as error:
   print(error.stdout or '',error.stderr or '',file=sys.stderr);raise
  if not r.stdout.startswith('PASS 7 exact native models'):raise RuntimeError(r.stdout+r.stderr)
 (RUNTIME/'secondary-verification.json').write_text(json.dumps({'cpu_solver':rows,'routing':r.stdout.strip(),'mambo_cape_stretch':stretch,'native_skin_cases':56,'installed':False,'gameplay_verified':False},indent=2)+'\n')
 print(r.stdout,flush=True)
if __name__=='__main__':main()
