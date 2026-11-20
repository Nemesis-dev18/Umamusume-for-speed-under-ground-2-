"""Exercise all eight staged identities through the real hook in an independent GPU host."""
import json,os,shutil,subprocess
from pathlib import Path
from verify_runtime import ROOT,RUNTIME,CC,FLAGS,WINE,WORK,run
from fleet_carrier import carrier


def main():
 fixture=RUNTIME/'gentildonna-fleet-test';fleet=fixture/'modding/runtime/fleet';fleet.mkdir(parents=True,exist_ok=True)
 for identifier in (1068,1052,1032,1062,1015,1006,1058):
  target=fleet/str(identifier);target.mkdir(exist_ok=True)
  for name in ('model.umab','atlas.dds','secondary.bin','anchors.bin'):shutil.copyfile(ROOT/'modding/runtime/fleet'/str(identifier)/name,target/name)
  (target/'carrier.bin').write_bytes(carrier(identifier))
 shutil.copyfile(ROOT/'modding/staged-runtime/fleet-secondary/1062/secondary.bin',fleet/'1062/secondary.bin')
 target=fleet/'9001';target.mkdir(exist_ok=True)
 for file in (ROOT/'modding/staged-runtime/gentildonna').iterdir():
  if file.suffix in ('.umab','.dds','.bin'):shutil.copyfile(file,target/file.name)
 for name in ('anchors.bin','carrier.bin'):shutil.copyfile(ROOT/'modding/staged-runtime/fleet/9001'/name,target/name)
 run([CC,*FLAGS,RUNTIME/'runner_fleet_test.c','-o',RUNTIME/'test-build/gentildonna-fleet-test.exe','-ld3d9','-luser32','-lwinmm','-lm'])
 try:r=run([WINE,RUNTIME/'test-build/gentildonna-fleet-test.exe',str(fixture.relative_to(ROOT)).replace('/','\\'),'8'],env=dict(os.environ,WINEPREFIX=str(WORK/'proton-prefix/pfx'),WINEDEBUG='-all'),capture_output=True,text=True)
 except subprocess.CalledProcessError as error:print(error.stdout or '',error.stderr or '');raise
 assert r.stdout.startswith('PASS 8 exact native models'),r.stdout+r.stderr
 (fixture/'result.txt').write_text(r.stdout);print(r.stdout)

if __name__=='__main__':main()
