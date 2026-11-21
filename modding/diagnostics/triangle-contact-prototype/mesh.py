"""Offline physical seam map; never rewrites rendered vertices or game assets."""
import json
import struct
import math
from pathlib import Path


def physical_mesh(topology):
    weights={int(v):w for v,w in topology['weights'].items()}
    representative={v:v for v in weights}
    for group in topology['candidate_seams']:
        assert group and len(set(group))==len(group)
        root=min(group)
        for v in group:
            assert v in weights and representative[v]==v
            assert weights[v]==weights[root]
            representative[v]=root
    roots=sorted(set(representative.values()))
    index={v:i for i,v in enumerate(roots)}
    mapping={v:index[root] for v,root in representative.items()}
    triangles=[tuple(mapping[v] for v in tri) for tri in topology['triangles']]
    assert all(len(set(tri))==3 for tri in triangles)
    edges=sorted({tuple(sorted((tri[i],tri[(i+1)%3]))) for tri in triangles for i in range(3)})
    return roots,mapping,triangles,edges,[weights[v] for v in roots]


def main():
    here=Path(__file__).resolve().parent
    root=here.parents[2]
    topology=json.loads((here/'diamond-topology.json').read_text())
    roots,mapping,triangles,edges,mass=physical_mesh(topology)
    rows=[]
    for file in sorted((root/'modding/diagnostics/diamond-intersections/installed').glob('*.umap')):
        data=file.read_bytes()
        magic,version,count=struct.unpack_from('<4s2I',data)
        assert magic==b'UMAP' and version==1 and len(data)==12+36*count
        poses=[struct.unpack_from('<3f',data,12+36*v) for v in range(count)]
        particles=[poses[v] for v in roots]
        error=max(math.dist(poses[v],particles[p]) for v,p in mapping.items())
        assert error==0
        rows.append({'pose':file.stem,'expand_error_m':error})
    assert len(rows)>=8
    report={'scope':'Experimental exact seam map only; no contact or garment quality claim. Native rendered topology is unchanged.',
            'render_vertices':len(mapping),'physical_particles':len(roots),'triangles':len(triangles),'physical_edges':len(edges),'fully_pinned_particles':sum(w==0 for w in mass),'poses':rows}
    (here/'diamond-physical-mesh.json').write_text(json.dumps({'render_to_particle':mapping,'representatives':roots,'triangles':triangles,'edges':edges,'inverse_mass':mass},separators=(',',':'))+'\n')
    (here/'diamond-physical-mesh-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    main()
