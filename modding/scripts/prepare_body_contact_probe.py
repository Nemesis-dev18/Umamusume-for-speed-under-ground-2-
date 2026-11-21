"""Build a read-only model-derived anatomy probe; no game installation."""
from pathlib import Path
import json,struct,sys
ROOT=Path(__file__).resolve().parents[2]
def main(identifier=1032):
 out=ROOT/'modding/diagnostics/body-contact';out.mkdir(exist_ok=True);model=ROOT/f'modding/runtime/fleet/{identifier}/model.umab';model=model if model.exists() else ROOT/'modding/staged-runtime/diamond/model.umab';asset=model.read_bytes();nv,ni,nb=struct.unpack_from('<3I',asset,8)
 parents=[struct.unpack_from('<h',asset,40+nv*60+i*16)[0] for i in range(nb)];mask=bytearray(nb)
 if identifier==9001:
  from pack_motion import topology
  bones=json.loads((ROOT/'modding/staged-runtime/gentildonna-source/skeleton.json').read_text());order=topology(bones);names=[bones[i]['name'] for i in order];assert len(names)==nb
  physics=(ROOT/'modding/runtime/fleet/9001/secondary.bin').read_bytes();spring_names=json.loads((ROOT/'modding/staged-runtime/gentildonna/secondary.json').read_text())['nodes']
  for i,name in enumerate(spring_names):
   if 'スカート' in name or '袖' in name:mask[struct.unpack_from('<H',physics,24+i*48)[0]]=1
 else:
  folder=ROOT/f'modding/staged-runtime/fleet-secondary/{identifier}';folder=folder if folder.exists() else ROOT/'modding/staged-runtime/diamond';report=json.loads((folder/'model.json').read_text());names=report['bone_names'];assert len(names)==nb
  meta=json.loads((folder/'secondary.json').read_text())
  for node in meta['spring_nodes']:
   if 'Skirt' in node['category'] or node['category'] in ('Jacket','Mantle','Sleeve','Hood'):mask[node['bone']]=1
 for i,p in enumerate(parents):assert -1<=p<i
 for i,p in enumerate(parents):
  if p>=0 and mask[p]:mask[i]=1
 def body_prefab(i):
  if identifier==9001:return True
  while i>=0:
   if names[i].startswith('pfb_'):return names[i].startswith('pfb_bdy')
   i=parents[i]
  return False
 def bone(name):
  if identifier==9001:
   aliases={'Hip':'下半身','Chest':'上半身2','Arm_L':'左腕','Elbow_L':'左ひじ','Wrist_L':'左手首','Knee_L':'左ひざ','Ankle_L':'左足首','Arm_R':'右腕','Elbow_R':'右ひじ','Wrist_R':'右手首','Knee_R':'右ひざ','Ankle_R':'右足首'};name=aliases[name]
  matches=[i for i,n in enumerate(names) if n==name and body_prefab(i)];assert len(matches)==1,(name,matches)
  return matches[0]
 records=[(bone('Hip'),bone('Chest'),.12)]
 for side in ['L','R']:
  knee=bone('Knee_'+side);records.extend([(parents[knee],knee,.075),(knee,bone('Ankle_'+side),.055),(bone('Arm_'+side),bone('Elbow_'+side),.045),(bone('Elbow_'+side),bone('Wrist_'+side),.035),(bone('Wrist_'+side),bone('Wrist_'+side),.045)])
 assert sum(mask)>0 and all(0<=a<nb and 0<=b<nb for a,b,_ in records)
 staged=ROOT/f'modding/staged-runtime/body-contact/{identifier}';staged.mkdir(parents=True,exist_ok=True);encoded=struct.pack('<4s4I',b'UMAC',1,nb,nv,len(records))+mask+bytes((-nb)%4)+b''.join(struct.pack('<2Hf',*row) for row in records);(staged/'body.umac').write_bytes(encoded)
 (out/f'{identifier}-mask.bin').write_bytes(mask);(out/f'{identifier}-anatomy.bin').write_bytes(b''.join(struct.pack('<2Hf',*row) for row in records));(out/f'{identifier}-anatomy.json').write_text(json.dumps({'scope':'Uninstalled proxy-collision prototype; not exact body mesh','garment_bones':sum(mask),'capsules':[{'from':names[a],'to':names[b],'radius':r} for a,b,r in records]},indent=2)+'\n');print(identifier,'prototype:',sum(mask),'garment bones;',len(records),'body/limb capsules')
if __name__=='__main__':main(int(sys.argv[1]) if len(sys.argv)>1 else 1032)
