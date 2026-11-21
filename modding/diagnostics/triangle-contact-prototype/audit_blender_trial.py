"""Inspect actual saved cloth panels/attachments; no visual or game acceptance claim."""
import json
import struct
import math
import sys
from pathlib import Path
from mesh import physical_mesh,root_attachment_weights


def strain_metrics(pose,native,edges):
    values=[];absolute=[]
    for i,j in edges:
        rest=math.dist(native[i],native[j])
        if rest>.001:
            length=math.dist(pose[i],pose[j]);values.append(abs(length/rest-1));absolute.append(abs(length-rest))
    values.sort()
    return {'max_edge_length_error_m':max(absolute,default=0),'max_edge_strain':max(values,default=0),'p95_edge_strain':values[int((len(values)-1)*.95)] if values else 0,'edges_above_ten_percent':sum(v>.1 for v in values)}


def trial_mesh(report,folder=None):
    if folder is not None and (folder/'simulation-topology.json').is_file():
        data=json.loads((folder/'simulation-topology.json').read_text());data['render_to_sim']={int(v):p for v,p in data['render_to_sim'].items()}
        count=len(data['sim_roots']);assert count==len(data['pins']) and all(0<=p<count for p in data['render_to_sim'].values()) and all(0<=a<count and 0<=b<count for a,b in data['edges'])
        return data
    here=Path(__file__).resolve().parent;root=here.parents[2]
    roots,mapping,tris,edges,mass=physical_mesh(json.loads((here/'diamond-topology-position-skin.json').read_text()))
    model=(root/'modding/runtime/fleet/1067/model.umab').read_bytes();nv,_,nb=struct.unpack_from('<3I',model,8)
    parents=[struct.unpack_from('<h',model,40+nv*60+b*16)[0] for b in range(nb)]
    source=json.loads((root/'modding/staged-runtime/diamond/secondary.json').read_text())
    cloth={n['bone'] for n in source['spring_nodes'] if 'Skirt' in n['category'] or n['category']=='Sleeve'}
    skins=[(struct.unpack_from('<4H',model,40+nv*36+v*24),struct.unpack_from('<4f',model,40+nv*36+v*24+8)) for v in roots]
    pin=root_attachment_weights(parents,cloth,skins) if report.get('native_root_attachments') else [1-w for w in mass]
    adj=[[] for _ in roots]
    for a,b in edges:adj[a].append(b);adj[b].append(a)
    seen=set();keep=set()
    for v in range(len(roots)):
        if v in seen:continue
        stack=[v];seen.add(v);part=[]
        while stack:
            a=stack.pop();part.append(a)
            for b in adj[a]:
                if b not in seen:seen.add(b);stack.append(b)
        if max(pin[i] for i in part)>0:keep.update(part)
    order=sorted(keep);remap={v:i for i,v in enumerate(order)};sim_edges=[(remap[a],remap[b]) for a,b in edges if a in keep]
    return {'render_to_sim':{v:remap[particle] for v,particle in mapping.items() if particle in keep},'sim_roots':[roots[v] for v in order],'pins':[pin[v] for v in order],'edges':sim_edges,'vertices':nv}


def main(name):
    assert strain_metrics([[0,0,0],[2,0,0]],[[0,0,0],[1,0,0]],[(0,1)])['max_edge_strain']==1
    assert strain_metrics([[1,2,3],[2,2,3]],[[0,0,0],[1,0,0]],[(0,1)])['max_edge_strain']==0
    here=Path(__file__).resolve().parent;root=here.parents[2];base=root/'modding/diagnostics/blender-cloth-trial'
    folder=(base/name).resolve();assert folder.parent==base.resolve()
    report=json.loads((folder/'simulation-report.json').read_text())
    mesh=trial_mesh(report,folder)
    rows=[]
    for record in report['frames']:
        frame=record['frame'];pose=json.loads((folder/f'trial-{frame:03d}.json').read_text());assert len(pose)==len(mesh['sim_roots'])
        raw=(base/f'run-source/run-{(frame-1)%48:03d}.umap').read_bytes()
        native=[struct.unpack_from('<3f',raw,12+36*v) for v in mesh['sim_roots']]
        row={'frame':frame,**strain_metrics(pose,native,mesh['edges']),'max_full_pin_error_m':max((math.dist(pose[i],native[i]) for i,pin in enumerate(mesh['pins']) if pin>=.9999),default=0)}
        rows.append(row)
    result={'scope':'Saved-sample panel strain relative to native skinned panel; maximum pin error checks >=0.9999weights. Does not verify unsampled contacts or natural appearance.','trial':name,'results':rows,'accepted_for_game':False}
    (folder/'panel-quality-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(name,'max_strain',max(r['max_edge_strain'] for r in rows),'max_edge_length_error_m',max(r['max_edge_length_error_m'] for r in rows),'worst_p95',max(r['p95_edge_strain'] for r in rows),'max_full_pin_error',max(r['max_full_pin_error_m'] for r in rows))


if __name__=='__main__':main(sys.argv[1])
