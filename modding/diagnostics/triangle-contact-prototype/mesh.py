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



def root_attachment_weights(parents,cloth_nodes,skins):
    controls=[]
    for bone,parent in enumerate(parents):
        assert -1<=parent<bone
        ancestor=bone
        while ancestor>=0 and ancestor not in cloth_nodes:ancestor=parents[ancestor]
        controls.append(ancestor<0 or parents[ancestor] not in cloth_nodes)
    result=[]
    for bones,weights in skins:
        assert len(bones)==len(weights) and all(0<=b<len(parents) for b in bones)
        assert all(math.isfinite(w) and 0<=w<=1 for w in weights) and abs(sum(weights)-1)<1e-4
        result.append(sum(w for b,w in zip(bones,weights) if controls[b]))
    return result



def proximal_attachment_weights(parents,cloth_nodes,skins,points,origins,tips,edges):
    root_attachment_weights(parents,cloth_nodes,skins)
    assert len(points)==len(skins)
    adj=[set() for _ in points]
    for a,b in edges:
        assert 0<=a<len(points) and 0<=b<len(points)
        adj[a].add(b);adj[b].add(a)
    component={}
    for v in range(len(points)):
        if v in component:continue
        stack=[v];component[v]=v
        while stack:
            a=stack.pop()
            for b in adj[a]:
                if b not in component:component[b]=v;stack.append(b)
    result=[];contributions=[];groups={}
    for v,(bones,weights) in enumerate(skins):
        body=0;root_weights={}
        for b,w in zip(bones,weights):
            ancestor=b
            while ancestor>=0 and ancestor not in cloth_nodes:ancestor=parents[ancestor]
            if ancestor<0:body+=w
            elif parents[ancestor] not in cloth_nodes and w>0:
                root_weights[ancestor]=root_weights.get(ancestor,0)+w
        result.append(body);contributions.append(root_weights)
        for root in root_weights:
            tip=tips[root];squared=sum(x*x for x in tip);assert squared>1e-12
            axial=sum((points[v][k]-origins[root][k])*tip[k] for k in range(3))/squared
            assert math.isfinite(axial)
            groups.setdefault((component[v],root),[]).append((axial,v))
    factors={}
    for (_,root),values in groups.items():
        minimum=min(t for t,_ in values);members={v for _,v in values}
        seeds={v for t,v in values if t<=minimum+1e-6}
        attached=seeds|{b for a in seeds for b in adj[a] if b in members}
        fade={b for a in attached for b in adj[a] if b in members}-attached
        for v in attached:factors[v,root]=1
        for v in fade:factors[v,root]=.5
    for v,weights in enumerate(contributions):
        result[v]=min(1.,result[v]+sum(w*factors.get((v,root),0) for root,w in weights.items()))
    return result


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
