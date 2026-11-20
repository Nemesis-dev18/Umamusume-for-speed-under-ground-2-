"""Prepare backups and atomically install the exact verified local character package."""
import argparse,datetime,hashlib,json,os,shutil,subprocess
from pathlib import Path
from inspect_assets import ROOT
PLAN=ROOT/'modding/gentildonna-install-plan.json'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def game_closed():
 if subprocess.run(['pgrep','-i','-x','SPEED2.EXE'],stdout=subprocess.DEVNULL).returncode==0:raise RuntimeError('Close the test game before installing')

def prepare():
 game_closed();pairs=[];source=ROOT/'modding/staged-runtime/gentildonna';geometry=ROOT/'modding/staged-runtime/fleet/9001'
 for name in ('model.umab','secondary.bin','atlas.dds','materials.bin',*(f'material-{i:02}.dds' for i in range(10))):pairs.append((source/name,'modding/runtime/fleet/9001/'+name))
 for name in ('anchors.bin','carrier.bin'):pairs.append((geometry/name,'modding/runtime/fleet/9001/'+name))
 pairs += [(geometry/'GEOMETRY.BIN','CARS/350Z/GEOMETRY.BIN'),(source/'TEXTURES.BIN','CARS/350Z/TEXTURES.BIN'),(ROOT/'modding/staged-runtime/fleet-secondary/1062/secondary.bin','modding/runtime/fleet/1062/secondary.bin')]
 menu=json.loads((ROOT/'modding/staged-runtime/gentildonna-menu/plan.json').read_text())
 for item in menu['files']:
  assert digest(ROOT/item['target'])==item['before_sha256'] and digest(ROOT/item['candidate'])==item['after_sha256']
  pairs.append((ROOT/item['candidate'],item['target']))
 pairs.append((ROOT/'modding/runtime/UmaRunner.asi','scripts/UmaRunner.asi'))
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S');backup=ROOT/'modding/backups'/('before-gentildonna-'+stamp);backup.mkdir(exist_ok=False)
 rows=[]
 for src,name in pairs:
  target=ROOT/name;src.resolve().relative_to(ROOT.resolve());target.resolve().relative_to(ROOT.resolve())
  assert not any(p.is_symlink() for p in (target,*target.parents))
  old=digest(target) if target.exists() else None;copy=backup/(name+'.bak')
  if old is not None:copy.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(target,copy);assert digest(copy)==old
  rows.append({'target':name,'candidate':str(src.relative_to(ROOT)),'before':old,'after':digest(src),'bytes':src.stat().st_size,'backup':str(copy.relative_to(ROOT)) if old else None})
 geometry_report=json.loads((geometry/'geometry.json').read_text());assert digest(ROOT/'CARS/350Z/GEOMETRY.BIN')==geometry_report['before_sha256']
 shadow_report=json.loads((source/'shadow.json').read_text());assert digest(ROOT/'CARS/350Z/TEXTURES.BIN')==shadow_report['before_sha256']
 PLAN.write_text(json.dumps({'backup_root':str(backup.relative_to(ROOT)),'files':rows,'installed':False,'gameplay_verified':False},indent=2)+'\n');print('Prepared',len(rows),'files and exact backups:',backup)

def install():
 game_closed();plan=json.loads(PLAN.read_text());assert not plan['installed'];checkpoint=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 for row in plan['files']:
  target=ROOT/row['target'];assert (digest(target) if target.exists() else None)==row['before'];assert digest(ROOT/row['candidate'])==row['after']
  if row['backup']:
   assert digest(ROOT/row['backup'])==row['before'];subprocess.run(['git','ls-files','--error-unmatch','--',row['backup']],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
 changed=[];temporary=None
 try:
  for row in plan['files']:
   target=ROOT/row['target'];target.parent.mkdir(parents=True,exist_ok=True);tmp=target.with_name(target.name+'.gentildonna.tmp')
   with tmp.open('xb') as f:
    temporary=tmp;f.write((ROOT/row['candidate']).read_bytes());f.flush();os.fsync(f.fileno())
   assert digest(tmp)==row['after'];os.replace(tmp,target);temporary=None;changed.append(row);assert digest(target)==row['after']
 except BaseException:
  if temporary is not None:temporary.unlink(missing_ok=True)
  for row in reversed(changed):
   target=ROOT/row['target']
   if row['backup']:shutil.copyfile(ROOT/row['backup'],target)
   else:target.unlink()
  raise
 plan.update(installed=True,checkpoint=checkpoint);PLAN.write_text(json.dumps(plan,indent=2)+'\n');print('Installed and verified',len(changed),'files; no game launch')

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','install'));args=parser.parse_args();prepare() if args.action=='prepare' else install()
