"""Measure actual garment/native spring-volume overlap without modifying poses."""
import json
import struct
import math
from pathlib import Path
from probe import closest_triangle,closest_capsule_axis


def main():
    here=Path(__file__).resolve().parent;root=here.parents[2]
    topo=json.loads((here/'diamond-topology.json').read_text())
    model=(root/'modding/runtime/fleet/1067/model.umab').read_bytes()
    secondary=(root/'modding/runtime/fleet/1067/secondary.bin').read_bytes()
    nv,_,nb=struct.unpack_from('<3I',model,8)
    magic,version,bones,nodes,colliders,refs=struct.unpack_from('<4s5I',secondary)
    assert magic==b'UMAS' and version==1 and bones==nb
    node_refs={}
    references=struct.unpack_from('<'+'H'*refs,secondary,24+48*nodes+36*colliders)
    for i in range(nodes):
        bone,_,first,count=struct.unpack_from('<4H',secondary,24+48*i)
        node_refs[bone]=set(references[first:first+count])
    parents=[struct.unpack_from('<h',model,40+nv*60+16*b)[0] for b in range(nb)]
    per_vertex={}
    for text,weight in topo['weights'].items():
        v=int(text);allowed=set()
        if weight>0:
            joints=struct.unpack_from('<4H',model,40+nv*36+v*24)
            weights=struct.unpack_from('<4f',model,40+nv*36+v*24+8)
            for bone,w in zip(joints,weights):
                if not w:continue
                while bone>=0 and bone not in node_refs:bone=parents[bone]
                if bone>=0:allowed.update(node_refs[bone])
        per_vertex[v]=allowed
    triangles=topo['triangles'];allowed=[set().union(*(per_vertex[v] for v in tri)) for tri in triangles]
    rows=[]
    for path in sorted((here/'native-poses').glob('*-colliders.json')):
        label=path.name.removesuffix('-colliders.json');volumes=json.loads(path.read_text())
        raw=(here/'native-poses'/f'{label}.umap').read_bytes()
        poses=[struct.unpack_from('<3f',raw,12+36*v) for v in range(nv)]
        hits=[];tested=0;inside_skipped=0
        for t,(ids,refs_for_triangle) in enumerate(zip(triangles,allowed)):
            tri=[poses[v] for v in ids]
            low=[min(p[k] for p in tri) for k in range(3)];high=[max(p[k] for p in tri) for k in range(3)]
            for c in refs_for_triangle:
                volume=volumes[c]
                if volume['kind']&1:inside_skipped+=1;continue
                start=volume['a'];end=volume['b'] if volume['kind']&2 else start
                radius=volume['radius']
                if any(max(start[k],end[k])+radius<low[k] or min(start[k],end[k])-radius>high[k] for k in range(3)):continue
                tested+=1
                if volume['kind']&2:q,bary,axis=closest_capsule_axis(start,end,tri)
                else:q,bary=closest_triangle(start,tri);axis=start
                distance=math.dist(q,axis)
                if distance<radius-1e-6:hits.append({'triangle':t,'collider':c,'penetration_m':radius-distance,'axis_pierces_triangle':distance<1e-9})
        row={'pose':label,'tested_after_bounds':tested,'inside_volume_pairs_excluded':inside_skipped,'overlap_pairs':len(hits),'axis_piercing_pairs':sum(h['axis_pierces_triangle'] for h in hits),'max_penetration_m':max((h['penetration_m'] for h in hits),default=0),'pairs':hits}
        rows.append(row);print(label,{k:v for k,v in row.items() if k not in ('pairs','pose')},flush=True)
    report={'scope':'Overlap with actual active spring volumes using nearest spring-ancestor reference unions per garment triangle; not body mesh ground truth. Inside volumes intentionally excluded. Does not establish visible defect or correct fit.','results':rows,'accepted_for_game':False}
    (here/'diamond-native-contact-audit.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
