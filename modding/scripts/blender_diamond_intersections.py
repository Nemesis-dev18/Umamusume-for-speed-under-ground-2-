"""Measure non-coplanar hair/garment/tail crossings in actual runtime pose snapshots."""
import json,struct
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri
ROOT=Path(__file__).resolve().parents[2]

def crossing(a,b):
 for source,target in ((a,b),(b,a)):
  for i in range(3):
   start=source[i];delta=source[(i+1)%3]-start;length=delta.length_squared
   if length<1e-14:continue
   point=intersect_ray_tri(*target,delta,start,True)
   if point is not None and 1e-5<(point-start).dot(delta)/length<1-1e-5:return True
 return False

a=[Vector(v) for v in [(0,0,0),(1,0,0),(0,1,0)]]
assert crossing(a,[Vector(v) for v in [(.25,.2,-1),(.25,.2,1),(.25,.8,1)]])
assert not crossing(a,[Vector(v) for v in [(5,.2,-1),(5,.2,1),(5,.8,1)]])
assert not crossing(a,[Vector(v) for v in [(.25,.2,0),(.25,.2,1),(.25,.8,1)]])
model=(ROOT/'modding/runtime/fleet/1067/model.umab').read_bytes();nv,ni,nb=struct.unpack_from('<3I',model,8);assert model[:4]==b'UMAB' and struct.unpack_from('<I',model,4)[0]==3
indices=struct.unpack_from('<'+'H'*ni,model,40+nv*60+nb*16);triangles=[tuple(indices[i:i+3]) for i in range(0,ni,3)];meta=json.loads((ROOT/'modding/staged-runtime/diamond/model.json').read_text());spring=json.loads((ROOT/'modding/staged-runtime/diamond/secondary.json').read_text())
mask=bytearray(nb)
for node in spring['spring_nodes']:
 if 'Skirt' in node['category'] or node['category']=='Sleeve':mask[node['bone']]=1
for b in range(nb):
 parent=struct.unpack_from('<h',model,40+nv*60+b*16)[0]
 if parent>=0 and mask[parent]:mask[b]=1
weights=[]
for v in range(nv):
 bones=struct.unpack_from('<4H',model,40+nv*36+v*24);values=struct.unpack_from('<4f',model,40+nv*36+v*24+8);weights.append(sum(w for b,w in zip(bones,values) if mask[b]))
sets={'hair':[],'garment':[],'tail':[]}
for group in meta['groups']:
 name=group['material'];category='hair' if name.endswith('_hair') else 'tail' if name.startswith('mtl_tail') else 'garment' if name.startswith('mtl_bdy') else None
 if category:
  for t in range(group['first_index']//3,(group['first_index']+group['index_count'])//3):
   ids=triangles[t]
   if len(set(ids))<3 or (category=='garment' and max(weights[v] for v in ids)<.5):continue
   sets[category].append((t,ids))
out=ROOT/'modding/diagnostics/diamond-intersections'
def main(variants=('installed','native-contacts'),report_name='intersection-report.json'):
 results=[]
 for variant in variants:
  for file in sorted((out/variant).glob('*.umap')):
   data=file.read_bytes();assert struct.unpack_from('<4s2I',data)==(b'UMAP',1,nv) and len(data)==12+nv*36;vertices=[Vector(struct.unpack_from('<3f',data,12+v*36)) for v in range(nv)];trees={k:BVHTree.FromPolygons(vertices,[ids for _,ids in group],all_triangles=True,epsilon=0) for k,group in sets.items()};row={'variant':variant,'pose':file.stem,'crossings':{}}
   for left,right in (('hair','garment'),('hair','tail'),('garment','tail')):
    hits=[]
    for i,j in trees[left].overlap(trees[right]):
     lt,li=sets[left][i];rt,ri=sets[right][j]
     if crossing([vertices[v] for v in li],[vertices[v] for v in ri]):hits.append([lt,rt])
    row['crossings'][left+'-'+right]={'pairs':len(hits),'triangle_pairs':hits}
   results.append(row);print(variant,file.stem,{k:v['pairs'] for k,v in row['crossings'].items()},flush=True)
 report={'scope':'Runtime skinned/secondary/surface poses; BVH broad phase plus edge/triangle geometric test. Excludes coplanar overlaps, exact tangencies, root/world collision response, and unsampled frames; no claim of zero clipping.','triangles':{k:len(v) for k,v in sets.items()},'results':results};(out/report_name).write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':
 import sys
 if '--' in sys.argv:
  assert sys.argv[sys.argv.index('--')+1:]==['wind-probe'];main(('wind-probe',),'wind-probe-report.json')
 else:main()
