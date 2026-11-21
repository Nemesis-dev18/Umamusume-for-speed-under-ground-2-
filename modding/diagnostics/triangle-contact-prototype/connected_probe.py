"""Controlled sphere contact on actual connected Diamond garment; no game writes."""
import json
import math
import struct
import time
from pathlib import Path
from mesh import physical_mesh
from probe import contact,closest_triangle,sub,dot


def main(iterations=100):
    here=Path(__file__).resolve().parent;root=here.parents[2]
    topology=json.loads((here/'diamond-topology.json').read_text())
    roots,mapping,triangles,edges,mass=physical_mesh(topology)
    rows=[]
    for label in ('rest','frame-060','frame-120'):
        raw=(root/f'modding/diagnostics/diamond-intersections/installed/{label}.umap').read_bytes()
        particles=[list(struct.unpack_from('<3f',raw,12+36*v)) for v in roots]
        original=[p[:] for p in particles]
        def area(tri):
            if min(mass[v] for v in tri)<.8:return -1
            a,b,c=(particles[v] for v in tri);ab,ac=sub(b,a),sub(c,a)
            n=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
            return dot(n,n)
        selected=max(triangles,key=area)
        assert area(selected)>1e-12
        a,b,c=(particles[v] for v in selected);ab,ac=sub(b,a),sub(c,a)
        n=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
        length=math.sqrt(dot(n,n));n=[v/length for v in n]
        center=[(a[k]+b[k]+c[k])/3-.003*n[k] for k in range(3)]
        radius=.008
        lengths=[math.dist(particles[i],particles[j]) for i,j in edges]
        initial,_=closest_triangle(center,[particles[v] for v in selected])
        initial_penetration=radius-math.dist(initial,center)
        begin=time.monotonic()
        for _ in range(iterations):
            for (i,j),rest in zip(edges,lengths):
                weight=mass[i]+mass[j]
                if not weight or rest<1e-8:continue
                delta=sub(particles[j],particles[i]);length=math.sqrt(dot(delta,delta))
                if length<1e-12:continue
                correction=(length-rest)/(length*weight)
                for k in range(3):
                    particles[i][k]+=mass[i]*correction*delta[k]
                    particles[j][k]-=mass[j]*correction*delta[k]
            contact([particles[v] for v in selected],[mass[v] for v in selected],center,radius)
        elapsed=time.monotonic()-begin
        point,_=closest_triangle(center,[particles[v] for v in selected])
        pinned=max((math.dist(original[i],p) for i,p in enumerate(particles) if mass[i]==0),default=0)
        strain=max(abs(math.dist(particles[i],particles[j])/rest-1) for (i,j),rest in zip(edges,lengths) if rest>1e-8)
        row={'pose':label,'initial_penetration_m':initial_penetration,'remaining_penetration_m':max(0,radius-math.dist(point,center)),'max_edge_strain':strain,'pinned_displacement_m':pinned,'max_displacement_m':max(math.dist(a,b) for a,b in zip(original,particles)),'offline_python_seconds':elapsed}
        assert pinned==0 and all(math.isfinite(x) for p in particles for x in p)
        rows.append(row);print(json.dumps(row),flush=True)
    report={'scope':'Controlled single-sphere/single-contact perturbation on actual garment topology; does not test native body fitting, complete collisions, temporal animation, normals, rendering or runtime speed.','iterations':iterations,'results':rows,'accepted_for_game':False}
    (here/f'diamond-connected-probe-{iterations}-report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--iterations',type=int,choices=(16,24,100),default=100)
    main(parser.parse_args().iterations)
