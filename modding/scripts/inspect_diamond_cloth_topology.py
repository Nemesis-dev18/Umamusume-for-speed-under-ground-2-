"""Read native Diamond garment topology; report seams without changing runtime meshes."""
import json
import struct
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def components(vertices,edges):
 parent={v:v for v in vertices}
 def find(v):
  while parent[v]!=v:
   parent[v]=parent[parent[v]];v=parent[v]
  return v
 for a,b in edges:
  a,b=find(a),find(b)
  if a!=b:parent[b]=a
 return sorted(Counter(find(v) for v in vertices).values(),reverse=True)


def main():
 assert components({0,1,2,3},[(0,1),(1,2)])==[3,1]
 assert components({0,1,2,3},[(0,1),(1,2),(2,3)])==[4]
 data=(ROOT/'modding/runtime/fleet/1067/model.umab').read_bytes()
 assert data[:4]==b'UMAB' and struct.unpack_from('<I',data,4)[0]==3
 nv,ni,nb=struct.unpack_from('<3I',data,8)
 index=struct.unpack_from('<'+'H'*ni,data,40+nv*60+nb*16)
 spring=json.loads((ROOT/'modding/staged-runtime/diamond/secondary.json').read_text())
 meta=json.loads((ROOT/'modding/staged-runtime/diamond/model.json').read_text())
 mask=bytearray(nb)
 for node in spring['spring_nodes']:
  if 'Skirt' in node['category'] or node['category']=='Sleeve':mask[node['bone']]=1
 for b in range(nb):
  parent=struct.unpack_from('<h',data,40+nv*60+b*16)[0]
  if parent>=0 and mask[parent]:mask[b]=1
 weights=[];keys=[]
 for v in range(nv):
  at=40+nv*36+v*24
  bones=struct.unpack_from('<4H',data,at);values=struct.unpack_from('<4f',data,at+8)
  weights.append(sum(w for b,w in zip(bones,values) if mask[b]))
  # Exact normal/position/skin identity excludes opposing layers and different skeletal attachments.
  keys.append(data[40+v*36:40+v*36+24]+data[at:at+24])
 triangles=[]
 for group in meta['groups']:
  if not group['material'].startswith('mtl_bdy'):continue
  for t in range(group['first_index'],group['first_index']+group['index_count'],3):
   ids=tuple(index[t:t+3])
   if len(set(ids))==3 and max(weights[v] for v in ids)>=.5:triangles.append(ids)
 vertices={v for tri in triangles for v in tri}
 edges={tuple(sorted((tri[i],tri[(i+1)%3]))) for tri in triangles for i in range(3)}
 counts=Counter(tuple(sorted((tri[i],tri[(i+1)%3]))) for tri in triangles for i in range(3))
 boundary={v for edge,count in counts.items() if count==1 for v in edge}
 buckets={}
 for v in sorted(vertices):buckets.setdefault(keys[v],[]).append(v)
 seams=[ids for ids in buckets.values() if len(ids)>1]
 links=[(ids[0],v) for ids in seams for v in ids[1:]]
 report={'scope':'Garment skin-weight selection only. Exact coincident position/normal/skin pairs are candidate seams, not approved welds; source material/layer intent still needs visual review.',
 'vertices':len(vertices),'triangles':len(triangles),'edges':len(edges),'boundary_vertices':len(boundary),'fully_pinned_vertices':sum(weights[v]==0 for v in vertices),'components_before':components(vertices,edges),'candidate_seam_groups':len(seams),'candidate_seam_links':len(links),'components_with_candidate_seams':components(vertices,list(edges)+links)}
 out=ROOT/'modding/diagnostics/triangle-contact-prototype'
 (out/'diamond-topology-report.json').write_text(json.dumps(report,indent=2)+'\n')
 (out/'diamond-topology.json').write_text(json.dumps({'triangles':triangles,'weights':{v:weights[v] for v in sorted(vertices)},'candidate_seams':seams},separators=(',',':'))+'\n')
 print(json.dumps(report))

if __name__=='__main__':main()
