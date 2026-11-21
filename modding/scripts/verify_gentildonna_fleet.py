"""Exercise all eight staged identities through the real hook in an independent GPU host."""
import json,os,shutil,subprocess
from pathlib import Path
from verify_runtime import ROOT,RUNTIME,CC,FLAGS,WINE,WORK,run
from fleet_carrier import carrier


def main(include_diamond=False,body_contacts=False):
 fixture=RUNTIME/('crossover-nine-test' if include_diamond else 'gentildonna-fleet-test');fleet=fixture/'modding/runtime/fleet';fleet.mkdir(parents=True,exist_ok=True)
 for identifier in (1068,1052,1032,1062,1015,1006,1058):
  target=fleet/str(identifier);target.mkdir(exist_ok=True)
  for name in ('model.umab','atlas.dds','secondary.bin','anchors.bin'):shutil.copyfile(ROOT/'modding/runtime/fleet'/str(identifier)/name,target/name)
  (target/'carrier.bin').write_bytes(carrier(identifier))
 shutil.copyfile(ROOT/'modding/staged-runtime/fleet-secondary/1062/secondary.bin',fleet/'1062/secondary.bin')
 target=fleet/'9001';target.mkdir(exist_ok=True)
 for file in (ROOT/'modding/staged-runtime/gentildonna').iterdir():
  if file.suffix in ('.umab','.dds','.bin'):shutil.copyfile(file,target/file.name)
 for name in ('anchors.bin','carrier.bin'):shutil.copyfile(ROOT/'modding/staged-runtime/fleet/9001'/name,target/name)
 if include_diamond:
  target=fleet/'1067';target.mkdir(exist_ok=True)
  for name in ('model.umab','atlas.dds','secondary.bin'):shutil.copyfile(ROOT/'modding/staged-runtime/diamond'/name,target/name)
  for name in ('anchors.bin','carrier.bin'):shutil.copyfile(ROOT/'modding/staged-runtime/fleet/1067'/name,target/name)
 shutil.copyfile(ROOT/'modding/runtime/fleet/9001/secondary.bin',fleet/'9001/secondary.bin')
 count=9 if include_diamond else 8
 identifiers=(1068,1052,1032,1062,1015,1006,1058,9001)+((1067,) if include_diamond else ())
 for identifier in identifiers:
  original=ROOT/('modding/staged-runtime/body-contact' if body_contacts else 'modding/runtime/fleet')/str(identifier)/'body.umac';copy=fleet/str(identifier)/'body.umac'
  if original.exists():shutil.copyfile(original,copy)
  else:copy.unlink(missing_ok=True)
 run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',RUNTIME/'foot_sparks_asset_test.c','-o',RUNTIME/'test-build/foot-sparks-asset-test','-lm'])
 for identifier in identifiers:
  asset=fleet/str(identifier);run([RUNTIME/'test-build/foot-sparks-asset-test',asset/'model.umab',asset/'secondary.bin'])
 run([CC,*FLAGS,RUNTIME/'runner_fleet_test.c','-o',RUNTIME/'test-build/gentildonna-fleet-test.exe','-ld3d9','-luser32','-lwinmm','-lm'])
 try:r=run([WINE,RUNTIME/'test-build/gentildonna-fleet-test.exe',str(fixture.relative_to(ROOT)).replace('/','\\'),str(count)],env=dict(os.environ,WINEPREFIX=str(WORK/'proton-prefix/pfx'),WINEDEBUG='-all'),capture_output=True,text=True)
 except subprocess.CalledProcessError as error:print(error.stdout or '',error.stderr or '');raise
 assert r.stdout.startswith(f'PASS {count} exact native models'),r.stdout+r.stderr
 (fixture/'result.txt').write_text(r.stdout);print(r.stdout)

if __name__=='__main__':main()
