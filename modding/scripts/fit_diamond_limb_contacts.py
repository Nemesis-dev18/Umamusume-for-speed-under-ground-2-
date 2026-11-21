"""Fit experimental limb-only collision radii from the native rest mesh. No game writes."""
import json
import hashlib
import struct
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def radial_sample(point,a,b):
    line=[b[k]-a[k] for k in range(3)];length=sum(v*v for v in line)
    assert length>1e-12
    t=sum((point[k]-a[k])*line[k] for k in range(3))/length
    return t,math.sqrt(sum((point[k]-a[k]-t*line[k])**2 for k in range(3)))


def main():
    assert radial_sample([.05,0,.5],[0,0,0],[0,0,1])==(.5,.05)
    model=(ROOT/'modding/runtime/fleet/1067/model.umab').read_bytes();nv,ni,nb=struct.unpack_from('<3I',model,8)
    meta=json.loads((ROOT/'modding/staged-runtime/diamond/model.json').read_text());names=meta['bone_names']
    secondary=json.loads((ROOT/'modding/staged-runtime/diamond/secondary.json').read_text())
    parents=[struct.unpack_from('<h',model,40+nv*60+b*16)[0] for b in range(nb)]
    joints=[struct.unpack_from('<3f',model,44+nv*60+b*16) for b in range(nb)]
    dynamic={n['bone'] for n in secondary['spring_nodes']}
    for b in range(nb):
        if parents[b] in dynamic:dynamic.add(b)
    body={v for group in meta['groups'] if group['material'].startswith('mtl_bdy') for v in range(group['first_vertex'],group['first_vertex']+group['vertex_count'])}
    skins=[(struct.unpack_from('<4H',model,40+nv*36+v*24),struct.unpack_from('<4f',model,40+nv*36+v*24+8)) for v in range(nv)]
    points=[struct.unpack_from('<3f',model,40+v*36) for v in range(nv)]
    anatomical={i for i,name in enumerate(names) if name in {part+'_'+side for part in ('Arm','Elbow','Wrist','Thigh','Knee','Ankle') for side in ('L','R')}}
    mapped=[]
    for bone in range(nb):
        ancestor=bone
        while ancestor>=0 and ancestor not in anatomical:ancestor=parents[ancestor]
        mapped.append(ancestor)
    contacts=[];unfitted=[]
    for side in ('L','R'):
        for start,end in (('Arm','Elbow'),('Elbow','Wrist'),('Thigh','Knee'),('Knee','Ankle')):
            a,b=names.index(start+'_'+side),names.index(end+'_'+side);samples=[]
            for v in body:
                bones,weights=skins[v]
                if sum(w for bone,w in zip(bones,weights) if bone in dynamic)>.05:continue
                if sum(w for bone,w in zip(bones,weights) if mapped[bone] in (a,b))<.5:continue
                t,radius=radial_sample(points[v],joints[a],joints[b])
                if .1<=t<=.9:samples.append((radius,v))
            if len(samples)<8:
                unfitted.append({'name':start+'-'+end+'_'+side,'samples':len(samples),'reason':'Insufficient non-spring-weighted body-material samples in axial interior; no guessed radius'});continue
            samples.sort();radius=samples[int(.9*(len(samples)-1))][0]
            assert .005<radius<.2,(start,end,side,radius)
            contacts.append({'name':start+'-'+end+'_'+side,'bone_a':a,'bone_b':b,'a':joints[a],'b':joints[b],'radius':radius,'sample_count':len(samples),'minimum_sample_radius':samples[0][0],'maximum_sample_radius':samples[-1][0],'fit':'90th percentile radial distance; axial range .1-.9; body-material vertices, >=50%segment influence and <=5%spring influence'})
    out=ROOT/'modding/diagnostics/blender-cloth-trial/limb-contacts-fit.json'
    out.write_text(json.dumps({'scope':'Experimental arm/leg envelopes only, not full anatomy. Does not validate containment, torso/hands/feet or cloth collision. No active body.umac created.','source_model_sha256':hashlib.sha256(model).hexdigest(),'contacts':contacts,'unfitted':unfitted,'accepted_for_game':False},indent=2)+'\n')
    print('Unfitted:',unfitted)
    print(json.dumps([{'name':c['name'],'radius_m':c['radius'],'samples':c['sample_count']} for c in contacts],indent=2))


if __name__=='__main__':main()
