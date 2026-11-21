"""Compare true garment/body crossings on matched native and simulated poses."""
import json
import struct
import sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'modding/diagnostics/blender-cloth-trial'
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,str(ROOT/'modding/diagnostics/triangle-contact-prototype'))
import blender_diamond_intersections as source
from audit_blender_trial import trial_mesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def crossing_count(vertices,garments,body,body_labels,pinned):
    left=BVHTree.FromPolygons(vertices,garments,all_triangles=True)
    right=BVHTree.FromPolygons(vertices,body,all_triangles=True)
    count=0;regions=Counter();fixed=0
    for i,j in left.overlap(right):
        a,b=garments[i],body[j]
        if set(a).intersection(b):continue
        if source.crossing([vertices[v] for v in a],[vertices[v] for v in b]):
            count+=1;regions[body_labels[j]]+=1;fixed+=all(v in pinned for v in a)
    return {'pairs':count,'by_body_bone':dict(regions),'fully_pinned_garment_pairs':fixed}


def main(name):
    folder=(BASE/name).resolve();assert folder.parent==BASE.resolve()
    report=json.loads((folder/'simulation-report.json').read_text());mesh=trial_mesh(report,folder)
    garments=[ids for _,ids in source.sets['garment']];body=[]
    for group in source.meta['groups']:
        if not group['material'].startswith('mtl_bdy'):continue
        for t in range(group['first_index']//3,(group['first_index']+group['index_count'])//3):
            ids=source.triangles[t]
            if len(set(ids))==3 and max(source.weights[v] for v in ids)<=.05:body.append(ids)
    assert body and garments
    body_labels=[]
    for tri in body:
        influences=Counter()
        for v in tri:
            bones=struct.unpack_from('<4H',source.model,40+source.nv*36+v*24);weights=struct.unpack_from('<4f',source.model,40+source.nv*36+v*24+8)
            for b,w in zip(bones,weights):influences[b]+=w
        body_labels.append(source.meta['bone_names'][influences.most_common(1)[0][0]])
    pinned={v for v,p in mesh['render_to_sim'].items() if mesh['pins'][p]>=.9999}
    rows=[]
    for record in report['frames']:
        frame=record['frame'];data=(BASE/f'run-source/run-{(frame-1)%48:03d}.umap').read_bytes();assert struct.unpack_from('<4s2I',data)==(b'UMAP',1,mesh['vertices'])
        native=[Vector(struct.unpack_from('<3f',data,12+v*36)) for v in range(mesh['vertices'])]
        trial=json.loads((folder/f'trial-{frame:03d}.json').read_text());assert len(trial)==len(mesh['sim_roots'])
        changed=[p.copy() for p in native]
        for v,particle in mesh['render_to_sim'].items():changed[v]=Vector(trial[particle])
        baseline=crossing_count(native,garments,body,body_labels,pinned);current=crossing_count(changed,garments,body,body_labels,pinned)
        row={'frame':frame,'native_crossing_pairs':baseline['pairs'],'trial_crossing_pairs':current['pairs'],'native_details':baseline,'trial_details':current}
        rows.append(row);print(frame,'native',baseline['pairs'],'trial',current['pairs'],'fixed',current['fully_pinned_garment_pairs'],flush=True)
    result={'scope':'Matched exact noncoplanar body/garment triangle crossings on saved frames only; excludes tangencies/shared-index neighbors. Does not verify cloth self-contact, hair/tail, normals or motion aesthetics.','results':rows,'accepted_for_game':False}
    (folder/'actual-body-crossings.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    assert '--' in sys.argv
    main(sys.argv[sys.argv.index('--')+1])
