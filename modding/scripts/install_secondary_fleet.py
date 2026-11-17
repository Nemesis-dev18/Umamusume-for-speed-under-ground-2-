"""Install verified seven-model secondary rigs with a dedicated Git checkpoint and rollback."""
import hashlib,json,os,shutil,subprocess
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 os.chdir(ROOT)
 if subprocess.run(['pgrep','-x','SPEED2.EXE'],capture_output=True).returncode==0:raise RuntimeError('Close NFS before installing')
 plan=json.loads((ROOT/'modding/secondary-fleet-plan.json').read_text());verified=json.loads((ROOT/'modding/runtime/secondary-verification.json').read_text())
 if len(verified['cpu_solver'])!=7 or verified['native_skin_cases']!=56:raise RuntimeError('Incomplete staged tests')
 sources=[]
 for row in plan['characters']:
  source=ROOT/row['candidate_folder'];destination=ROOT/'modding/runtime/fleet'/str(row['id'])
  for name,digest in row['sha256'].items():
   if sha(source/name)!=digest:raise RuntimeError('Staged model changed since packing')
  if (source/'atlas.dds').read_bytes()!=(destination/'atlas.dds').read_bytes():raise RuntimeError('Atlas changed')
  sources.extend([(source/'model-atlas.umab',destination/'model.umab'),(source/'secondary.bin',destination/'secondary.bin')])
 module=ROOT/'modding/runtime/UmaRunner.asi';runtime=json.loads((ROOT/'modding/runtime/verification.json').read_text())
 if sha(module)!=runtime['sha256']['UmaRunner.asi']:raise RuntimeError('Module changed since verification')
 sources.append((module,ROOT/'scripts/UmaRunner.asi'))
 backup=ROOT/'modding/backups'/('before-secondary-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True);rows=[]
 for source,target in sources:
  relative=target.relative_to(ROOT);saved=backup/relative
  if target.exists():saved.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(target,saved)
  rows.append({'path':str(relative),'before':sha(target) if target.exists() else None,'after':sha(source),'bytes':source.stat().st_size})
 receipt={'backup':str(backup.relative_to(ROOT)),'files':rows,'installed':False,'gameplay_verified':False}
 (backup/'manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
 subprocess.run(['git','add','--',str(backup.relative_to(ROOT))],check=True)
 subprocess.run(['git','commit','-m','Checkpoint current seven-character runtime before garment physics','--',str(backup.relative_to(ROOT))],check=True)
 receipt['checkpoint']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
 try:
  for (source,target),row in zip(sources,rows):
   temp=target.with_name(target.name+'.secondary.tmp');shutil.copyfile(source,temp);os.replace(temp,target)
   if sha(target)!=row['after']:raise RuntimeError('Installed hash mismatch')
 except BaseException:
  for row in rows:
   target=ROOT/row['path'];saved=backup/row['path']
   if row['before'] is None:target.unlink(missing_ok=True)
   else:shutil.copyfile(saved,target)
  raise
 receipt['installed']=True;(ROOT/'modding/secondary-installed.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'checkpoint':receipt['checkpoint'],'files':len(rows),'installed':True,'gameplay_verified':False}))
if __name__=='__main__':main()
