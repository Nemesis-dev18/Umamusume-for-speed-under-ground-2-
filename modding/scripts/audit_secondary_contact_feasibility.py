"""Prove individually unreachable spring contacts; ignores cones, so findings are conservative."""
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def unreachable_margin(node,volume):
    origin=node['origin'];a=volume['a'];b=volume['b'];line=[b[k]-a[k] for k in range(3)];length=sum(x*x for x in line)
    t=max(0,min(1,sum((origin[k]-a[k])*line[k] for k in range(3))/length)) if volume['kind']&2 and length>1e-12 else 0
    distance=math.sqrt(sum((origin[k]-a[k]-t*line[k])**2 for k in range(3)))
    link=node['tip_length'];radius=max(0,volume['radius']-node['particle_radius']) if volume['kind']&1 else volume['radius']+node['particle_radius']
    if volume['kind']&1:
        minimum=max(0,distance-link) if volume['kind']&2 else abs(distance-link)
        return max(0,minimum-radius)
    return max(0,radius-distance-link)


def main():
    n={'origin':[0,0,0],'tip_length':.1,'particle_radius':0}
    c={'a':[0,0,0],'b':[0,0,1],'radius':.2,'kind':0}
    assert abs(unreachable_margin(n,c)-.1)<1e-12
    assert abs(unreachable_margin(n,dict(c,kind=2))-.1)<1e-12
    assert unreachable_margin(n,dict(c,a=[1,0,0],b=[1,0,1]))==0
    assert abs(unreachable_margin(dict(n,tip_length=.3),dict(c,kind=1))-.1)<1e-12
    names=json.loads((ROOT/'modding/staged-runtime/diamond/model.json').read_text())['bone_names']
    base=ROOT/'modding/diagnostics/secondary-feasibility';rows=[]
    for variant in ('active','native-refs'):
        for p in sorted((base/variant).glob('*-spring-origins.json')):
            label=p.name.removesuffix('-spring-origins.json');nodes=json.loads(p.read_text());volumes=json.loads((p.parent/(label+'-colliders.json')).read_text());hits=[]
            for node in nodes:
                for index in node['colliders']:
                    margin=unreachable_margin(node,volumes[index])
                    if margin>1e-5:hits.append({'bone':node['bone'],'name':names[node['bone']],'collider':index,'unreachable_margin_m':margin})
            row={'variant':variant,'pose':label,'proven_unreachable_contacts':len(hits),'hits':hits};rows.append(row)
            print(variant,label,len(hits),flush=True)
    report={'scope':'Individual full-link sphere reachability versus actual aligned runtime colliders. Capsule outside uses conservative Lipschitz bound, inside uses lower bound. Angular limits, simultaneous-contact conflicts and surface mesh are not evaluated. A positive margin proves that contact and link length cannot both hold; zero does not prove feasibility.','results':rows}
    (base/'reachability-report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
