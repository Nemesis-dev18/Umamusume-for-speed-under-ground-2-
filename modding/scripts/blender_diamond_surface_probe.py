"""Uninstalled mesh-contact experiment; measure separation and distortion before runtime work."""
import json,struct,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'modding/scripts'))
from blender_diamond_intersections import crossing,model,nv,nb,sets,spring,out

def contacts(vertices,left,right):
 a=BVHTree.FromPolygons(vertices,[ids for _,ids in left],all_triangles=True);b=BVHTree.FromPolygons(vertices,[ids for _,ids in right],all_triangles=True)
 return [(i,j) for i,j in a.overlap(b) if crossing([vertices[v] for v in left[i][1]],[vertices[v] for v in right[j][1]])]

dynamic=bytearray(nb)
for node in spring['spring_nodes']:
 if node['category'] in ('Hair','Tail'):dynamic[node['bone']]=1
for b in range(nb):
 p=struct.unpack_from('<h',model,40+nv*60+b*16)[0]
 if p>=0 and dynamic[p]:dynamic[b]=1
weights=[]
for v in range(nv):
 bones=struct.unpack_from('<4H',model,40+nv*36+v*24);values=struct.unpack_from('<4f',model,40+nv*36+v*24+8);weights.append(sum(w for b,w in zip(bones,values) if dynamic[b]))
rest=[Vector(struct.unpack_from('<3f',model,40+v*36)) for v in range(nv)]
edges=sorted({tuple(sorted((u,v))) for name in ('hair','tail') for _,tri in sets[name] for u,v in zip(tri,tri[1:]+tri[:1])})
report=[];folder=out/'surface-probe-constrained';folder.mkdir(exist_ok=True)
for frame in ('frame-030','frame-060','frame-120'):
 data=(out/'installed'/(frame+'.umap')).read_bytes();vertices=[Vector(struct.unpack_from('<3f',data,12+v*36)) for v in range(nv)];base=[v.copy() for v in vertices];normals=[Vector(struct.unpack_from('<3f',data,24+v*36)) for v in range(nv)];pairs=(('hair','garment'),('tail','garment'),('hair','tail'));before={a+'-'+b:len(contacts(vertices,sets[a],sets[b])) for a,b in pairs};touched=set()
 lengths=[(base[u]-base[v]).length for u,v in edges]
 for iteration in range(16):
  for relax in range(2):
   for (u,v),length in zip(edges,lengths):
    wu=weights[u] if weights[u]>=.5 else 0;wv=weights[v] if weights[v]>=.5 else 0
    if wu+wv==0 or length<.001:continue
    delta=vertices[v]-vertices[u];current=delta.length
    if current<1e-8 or .98*length<=current<=1.02*length:continue
    target=min(length*1.02,max(length*.98,current));move=delta*(.8*(current-target)/(current*(wu+wv)));vertices[u]+=move*wu;vertices[v]-=move*wv

  for left,right in pairs:
   a,b=sets[left],sets[right];hits=contacts(vertices,a,b);candidates={v for i,j in hits for v in a[i][1] if weights[v]>=.5}
   tree=BVHTree.FromPolygons(vertices,[ids for _,ids in b],all_triangles=True)
   for v in candidates:
    point,normal,index,distance=tree.find_nearest(vertices[v])
    if point is None or distance>.08:continue
    ids=b[index][1];origin=rest[ids[0]];reference=(rest[ids[1]]-origin).cross(rest[ids[2]]-origin)
    if (rest[v]-origin).dot(reference)<0:normal=-normal
    signed=(vertices[v]-point).dot(normal)
    if signed<.003:vertices[v]+=normal*(.003-signed);touched.add(v)
 after={a+'-'+b:len(contacts(vertices,sets[a],sets[b])) for a,b in pairs};edges={tuple(sorted((u,v))) for name in ('hair','tail') for _,tri in sets[name] for u,v in zip(tri,tri[1:]+tri[:1])};edge_change=max(abs((vertices[u]-vertices[v]).length-(base[u]-base[v]).length) for u,v in edges);shift=max((a-b).length for a,b in zip(vertices,base));assert all(vertices[v]==base[v] for v in range(nv) if weights[v]<.5)
 result=bytearray(data)
 for v,p in enumerate(vertices):struct.pack_into('<3f',result,12+v*36,*p)
 (folder/(frame+'.umap')).write_bytes(result);row={'frame':frame,'before_pairs':before,'after_pairs':after,'changed_vertices':len(touched),'maximum_displacement_m':shift,'maximum_edge_length_change_m':edge_change,'pinned_vertices_unchanged':True,'normals_recomputed':False};report.append(row);print(json.dumps(row),flush=True)
(folder/'report.json').write_text(json.dumps({'installed':False,'accepted':False,'scope':'Offline reference-side surface projection with edge-length constraints; updated normals, temporal continuity and game performance still unvalidated. Do not install these snapshots.','results':report},indent=2)+'\n')
