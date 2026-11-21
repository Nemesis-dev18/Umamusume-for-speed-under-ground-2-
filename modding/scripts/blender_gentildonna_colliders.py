"""Convert permitted PMX fixed spheres/capsules using MMD Tools' Blender axis convention."""
import contextlib,hashlib,io,json,struct,sys
from pathlib import Path
import bpy
from mathutils import Euler,Matrix,Vector
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'modding/scripts'))
from verify_gentildonna_source import verify
from pack_motion import topology

with contextlib.redirect_stdout(io.StringIO()):model,validation=verify()
source=ROOT/'modding/staged-runtime/gentildonna-source';bones=json.loads((source/'skeleton.json').read_text());order=topology(bones);remap={int(i):j for j,i in enumerate(order)}
scale=json.loads((source/'receipt.json').read_text())['pmx_to_game_scale'];axes=Matrix(((0,-1,0),(-1,0,0),(0,0,1)))
fixed=[r for r in model.rigids if r.mode==0 and r.bone>=0];assert len(fixed)==21 and all(r.type in (0,2) for r in fixed)
colliders=[];details=[]
for r in fixed:
 loc=Vector((r.location[0],r.location[2],r.location[1]))*scale
 rotation=Euler((-r.rotation[0],-r.rotation[2],-r.rotation[1]),'YXZ').to_matrix()
 half=r.size[1]*scale*.5 if r.type==2 else 0
 a=axes@(loc+rotation@Vector((0,0,-half)));b=axes@(loc+rotation@Vector((0,0,half)));radius=r.size[0]*scale
 assert 0<radius<.2 and all(abs(v)<3 for v in (*a,*b))
 colliders.append((remap[r.bone],remap[r.bone],2 if r.type==2 else 0,0,*a,*b,radius));details.append({'name':r.name,'bone':r.bone,'runtime_bone':remap[r.bone],'group':r.collision_group_number,'mask':hex(r.collision_group_mask),'a':list(a),'b':list(b),'radius':radius})
active=ROOT/'modding/runtime/fleet/9001/secondary.bin';original=active.read_bytes();magic,version,nb,nn,nc,nr=struct.unpack_from('<4s5I',original);assert (magic,version,nb,nn,nc)==(b'UMAS',1,len(bones),123,5)
nodes=[];references=[];associations=[]
for i in range(nn):
 row=list(struct.unpack_from('<4H10f',original,24+i*48));bone=int(order[row[0]]);matches=[r for r in model.rigids if r.mode!=0 and r.bone==bone];assert len(matches)==1;rigid=matches[0]
 selected=[j for j,r in enumerate(fixed) if rigid.collision_group_mask&(1<<r.collision_group_number) and r.collision_group_mask&(1<<rigid.collision_group_number)]
 row[2]=len(references);row[3]=len(selected);references.extend(selected);nodes.append(row);associations.append({'bone':bones[bone]['name'],'rigid':rigid.name,'colliders':[fixed[j].name for j in selected]})
assert len(references)<=4096
data=struct.pack('<4s5I',b'UMAS',1,nb,nn,len(colliders),len(references))+b''.join(struct.pack('<4H10f',*r) for r in nodes)+b''.join(struct.pack('<4H7f',*c) for c in colliders)+struct.pack('<'+'H'*len(references),*references);data+=bytes((-len(data))%4)
folder=ROOT/'modding/staged-runtime/gentildonna-native-colliders';folder.mkdir(exist_ok=True);(folder/'secondary.bin').write_bytes(data)
report={'backend':'Blender '+bpy.app.version_string,'source_sha256':validation['source_sha256'],'before_sha256':hashlib.sha256(original).hexdigest(),'after_sha256':hashlib.sha256(data).hexdigest(),'colliders':details,'associations':associations,'bytes':len(data),'installed':False,'gameplay_verified':False,'scope':'Preserve installed springs/cloth flags; replace generic body capsules and blanket references with original PMX fixed shapes and mutual collision masks. Not full MMD rigid-body simulation.'};(folder/'plan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('PASS',len(colliders),'source fixed colliders;',len(references),'native allowed references;',len(data),'bytes; staged only')
