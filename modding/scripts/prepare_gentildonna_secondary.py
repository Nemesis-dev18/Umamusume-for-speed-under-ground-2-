"""Adapt the permitted PMX dynamic bone chains to bounded local runtime springs."""
import json,math,struct
import numpy as np
from inspect_assets import ROOT
from pack_motion import topology
from verify_gentildonna_source import verify


def main():
 model,_=verify();folder=ROOT/'modding/staged-runtime/gentildonna';source=ROOT/'modding/staged-runtime/gentildonna-source';bones=json.loads((source/'skeleton.json').read_text());order=topology(bones);remap={int(i):j for j,i in enumerate(order)};named={b['name']:i for i,b in enumerate(bones)};rest=np.array([b['position'] for b in bones]);colliders=[];ratio=json.loads((source/'receipt.json').read_text())['pmx_to_game_scale']/.1
 def capsule(a,b,radius):
  i,j=named[a],named[b];colliders.append((remap[i],remap[j],2,0,*rest[i],*rest[j],radius*ratio))
 capsule('下半身','上半身2',.16)
 for side in ('左','右'):
  capsule(side+'足',side+'ひざ',.10);capsule(side+'ひざ',side+'足首',.075)
 dynamic={r.bone for r in model.rigids if r.mode!=0 and r.bone>=0 and any(t in bones[r.bone]['name'] for t in ('髪','リボン','スカート','尻尾','袖'))}
 angular={model.rigids[j.dest_rigid].bone:max(abs(v) for v in (*j.minimum_rotation,*j.maximum_rotation)) for j in model.joints if 0<=j.dest_rigid<len(model.rigids)}
 records=[];references=[];names=[]
 for i in order:
  if i not in dynamic:continue
  children=[j for j in dynamic if bones[j]['parent']==i]
  tip=rest[children[0]]-rest[i] if len(children)==1 else rest[i]-rest[bones[i]['parent']]
  length=float(np.linalg.norm(tip))
  if not .001<length<.6:continue
  name=bones[i]['name'];tail='尻尾' in name;skirt='スカート' in name
  cone=min(math.radians(10 if skirt else 8 if tail else 6),max(math.radians(3),angular.get(i,math.radians(15))))
  refs=list(range(len(colliders))) if skirt else [0];first=len(references);references+=refs
  records.append((remap[int(i)],256,first,len(refs),*tip,2.2 if tail else 2.8,1.1 if tail else 1.3,.3 if tail else .6,.008*ratio,cone,.00015,.6 if tail else .55));names.append(name)
 assert records and len(records)<512 and len(references)<4096
 data=struct.pack('<4s5I',b'UMAS',1,len(bones),len(records),len(colliders),len(references))+b''.join(struct.pack('<4H10f',*r) for r in records)+b''.join(struct.pack('<4H7f',*c) for c in colliders)+struct.pack('<'+'H'*len(references),*references);data+=bytes((-len(data))%4)
 (folder/'secondary.bin').write_bytes(data);(folder/'secondary.json').write_text(json.dumps({'nodes':names,'colliders':len(colliders),'approximation':'Bounded dynamic PMX bone chains; not the MMD rigid body solver','installed':False},ensure_ascii=False,indent=2)+'\n');print('Prepared',len(records),'secondary chains')

if __name__=='__main__':main()
