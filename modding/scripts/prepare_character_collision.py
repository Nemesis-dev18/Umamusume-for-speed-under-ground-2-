"""Stage an affine rescale of all Corolla collision hulls; preserve topology and layout."""
import hashlib
import json
import struct
import numpy as np
from inspect_assets import ROOT,chunks,flatten
from extract_assets import skip_words,payload

LOWER=np.array([-.35,-.29,.05])
UPPER=np.array([.65,.29,1.95])

def prepare(source,slot='COROLLA',lower=LOWER,upper=UPPER):
    lower=np.asarray(lower,dtype=float);upper=np.asarray(upper,dtype=float)
    if lower.shape!=(3,) or upper.shape!=(3,) or not np.isfinite([lower,upper]).all() or np.any(upper<=lower):raise ValueError('Invalid character collision bounds')
    tree=chunks(source);container=[n for n in flatten(tree) if n['id']=='0x80034020']
    if len(container)!=1:raise ValueError('Expected one native collision container')
    children=container[0]['children'];out=bytearray(source);groups=[];allowed=[]
    if len(children)%3:raise ValueError('Incomplete collision hull group')
    for i in range(0,len(children),3):
        header,points,indices=children[i:i+3]
        if [n['id'] for n in (header,points,indices)]!=['0x00039200','0x00039201','0x00039202']:raise ValueError('Unexpected hull layout')
        raw=payload(source,header);start=skip_words(raw)
        version_a,version_b,_,_,_,count=struct.unpack_from('<6I',raw,start)
        name=raw[start+28:start+60].split(b'\0',1)[0].decode('ascii')
        if (version_a,version_b)!=(3,3) or not name.startswith(slot+'_') or not name.endswith('_CV') or count<4 or points['size']!=count*48:raise ValueError('Unexpected vehicle hull header')
        vertices=[]
        for vertex in range(count):
            at=points['payload']+vertex*48
            if struct.unpack_from('<2I',source,at)!=(3,3):raise ValueError('Unsupported collision point record')
            vertices.append(struct.unpack_from('<3f',source,at+16))
        vertices=np.array(vertices);minimum=vertices.min(0);maximum=vertices.max(0)
        if not np.isfinite(vertices).all() or np.any(maximum-minimum<.01):raise ValueError('Degenerate collision hull')
        replacement=lower+(vertices-minimum)/(maximum-minimum)*(upper-lower)
        for vertex,value in enumerate(replacement):
            at=points['payload']+vertex*48+16;struct.pack_into('<3f',out,at,*value);allowed.append({'offset':at,'bytes':12})
        groups.append({'name':name,'vertices':count,'old_minimum':minimum.tolist(),'old_maximum':maximum.tolist(),'new_minimum':lower.tolist(),'new_maximum':upper.tolist(),'scale':((upper-lower)/(maximum-minimum)).tolist()})
    expected={'COROLLA':5,'240SX':5,'MIATA':5,'FOCUS':5,'PEUGOT':5,'PEUGOT106':1,'CORSA':1,'350Z':5,'CELICA':1,'LANCEREVO8':5}
    if slot not in expected or len(groups)!=expected[slot] or chunks(out)!=tree:raise ValueError('Unexpected hull count or container layout changed')
    return bytes(out),groups,allowed

def main():
    path=ROOT/'CARS/COROLLA/GEOMETRY.BIN';backup=path.with_name('GEOMETRY.BIN.before-character-collision.bak')
    source=(backup if backup.exists() else path).read_bytes();candidate,groups,allowed=prepare(source)
    stage=ROOT/'modding/staged-runtime/GEOMETRY-character-collision.BIN';stage.write_bytes(candidate)
    plan={'target':str(path.relative_to(ROOT)),'candidate':str(stage.relative_to(ROOT)),'before_sha256':hashlib.sha256(source).hexdigest(),'after_sha256':hashlib.sha256(candidate).hexdigest(),'bytes':len(candidate),'groups':groups,'changed_ranges':allowed,'topology_and_layout_preserved':True,'installed':False,'limits':'Static convex hull approximation, not a ragdoll. Wheel suspension/mass/handling unchanged; gameplay stability and clearance pending.'}
    (ROOT/'modding/character-collision-plan.json').write_text(json.dumps(plan,indent=2)+'\n');print('Staged',len(groups),'hulls;',len(allowed),'vertex records;',plan['after_sha256'])

if __name__=='__main__':main()
