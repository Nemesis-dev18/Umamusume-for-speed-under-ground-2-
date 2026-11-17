"""Attach native head/tail rigs and add original local idle/run clips to review glTFs."""
import json,zlib
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from pack_motion import quaternion
from read_uma_motion import DenseMotion,rotation
ROOT=Path(__file__).resolve().parents[2]


def animate(folder):
    path=folder/'source.gltf';g=json.loads(path.read_text());blob=bytearray((folder/'source.bin').read_bytes())
    if g.get('animations'):raise ValueError('Regenerate base glTF before adding clips')
    nodes=g['nodes'];parents={c:i for i,n in enumerate(nodes) for c in n.get('children',[])}
    local={i:(np.array(n['matrix']).reshape(4,4).T if 'matrix' in n else np.diag([*n.get('scale',[1,1,1]),1])) for i,n in enumerate(nodes)}
    world={}
    def matrix(i):
        if i not in world:world[i]=matrix(parents[i])@local[i] if i in parents else local[i]
        return world[i]
    for i in range(len(nodes)):matrix(i)
    body=next(i for i,n in enumerate(nodes) if n['name'].startswith('pfb_bdy'));head=next(i for i,n in enumerate(nodes) if n['name'].startswith('pfb_chr'));tail=next(i for i,n in enumerate(nodes) if n['name'].startswith('pfb_tail'))
    def descendants(root):
        result={};stack=[(root,'')]
        while stack:
            i,name=stack.pop()
            if name in result:raise ValueError('Duplicate native joint path')
            result[name]=i
            stack.extend((c,name+'/'+nodes[c]['name'] if name else nodes[c]['name']) for c in nodes[i].get('children',[]))
        return result
    body_paths=descendants(body);head_paths=descendants(head);tail_paths=descendants(tail)
    def named(paths,name):
        matches=[i for i in paths.values() if nodes[i]['name']==name]
        if len(matches)!=1:raise ValueError('Ambiguous attachment joint '+name)
        return matches[0]
    for child,parent in [(head,named(body_paths,'Neck')),(tail,named(body_paths,'Hip'))]:
        nodes[parents[child]]['children'].remove(child);nodes[parent].setdefault('children',[]).append(child);parents[child]=parent
        local[child]=np.linalg.inv(world[parent])@world[child];nodes[child]['matrix']=local[child].T.reshape(-1).tolist()
    for skin in g['skins']:skin['skeleton']=body
    mapping={zlib.crc32(p.encode()):i for p,i in body_paths.items()}
    if len(mapping)!=len(body_paths):raise ValueError('Native path CRC collision')
    hip_path=next(p for p,i in body_paths.items() if i==named(body_paths,'Hip'))
    for p,i in tail_paths.items():
        if p.startswith('Hip/'):
            key=zlib.crc32((hip_path+p[3:]).encode());mapping.setdefault(key,i)
    aliases={named(body_paths,'Head'):[named(head_paths,'Head')]}
    tail_ctrl=[i for i in body_paths.values() if nodes[i]['name']=='Tail_Ctrl']
    if tail_ctrl:aliases[tail_ctrl[0]]=[named(tail_paths,'Tail_Ctrl')]
    def decompose(i):
        m=local[i];scale=np.linalg.norm(m[:3,:3],axis=0)
        if np.min(scale)<1e-6:raise ValueError('Singular animated rest transform')
        r=m[:3,:3]/scale
        if np.linalg.det(r)<.99 or not np.allclose(r.T@r,np.eye(3),atol=1e-4):raise ValueError('Nonrigid animated rest orientation')
        return m[:3,3].copy(),quaternion(r),scale
    rest={i:decompose(i) for i in set(mapping.values())|{j for a in aliases.values() for j in a}}
    def accessor(a,kind):
        a=np.ascontiguousarray(a,dtype='<f4')
        if not np.isfinite(a).all():raise ValueError('Nonfinite motion')
        blob.extend(bytes((-len(blob))%4));at=len(blob);blob.extend(a.tobytes());view=len(g['bufferViews']);g['bufferViews'].append({'buffer':0,'byteOffset':at,'byteLength':a.nbytes})
        item={'bufferView':view,'componentType':5126,'count':len(a),'type':kind}
        if kind=='SCALAR':item.update(min=[float(a.min())],max=[float(a.max())])
        index=len(g['accessors']);g['accessors'].append(item);return index
    reports=[];g['animations']=[]
    for label,name,clips,count in [('idle',next((folder/'motions').glob('*idle01_loop.json')).stem,folder/'motions',32),('run','anm_rac_type03_run02_base',None,48)]:
        clip=DenseMotion(name,SimpleNamespace(paths=mapping),clips);samples=[clip.channels(i/count) for i in range(count+1)];tracks={}
        for frame,channels in enumerate(samples):
            for (node,attribute),value in channels.items():
                if attribute==1:value=value*np.array([-1,1,1])
                elif attribute==2:value=value*np.array([1,-1,-1,1])
                elif attribute==3 and not np.allclose(value,1,atol=1e-5):raise ValueError('Animated scale needs runtime support')
                tracks.setdefault((node,attribute),[]).append(value)
                for alias in aliases.get(node,[]):
                    if attribute==1:v=rest[alias][0]+value-rest[node][0]
                    elif attribute==2:v=quaternion(rotation(rest[alias][1])@rotation(rest[node][1]).T@rotation(value))
                    else:v=value
                    tracks.setdefault((alias,attribute),[]).append(v)
        animation={'name':label,'channels':[],'samplers':[]};times=accessor(np.linspace(0,clip.duration,count+1).reshape(-1,1),'SCALAR')
        for (node,attribute),values in tracks.items():
            values=np.array(values)
            if len(values)!=count+1:raise ValueError('Incomplete motion track')
            if attribute==2:
                for j in range(1,len(values)):
                    if values[j-1]@values[j]<0:values[j]*=-1
            if 'matrix' in nodes[node]:
                p,q,s=decompose(node);nodes[node].pop('matrix');nodes[node].update(translation=p.tolist(),rotation=q.tolist(),scale=s.tolist())
            output=accessor(values,'VEC4' if attribute==2 else 'VEC3');index=len(animation['samplers']);animation['samplers'].append({'input':times,'output':output,'interpolation':'LINEAR'});animation['channels'].append({'sampler':index,'target':{'node':node,'path':{1:'translation',2:'rotation',3:'scale'}[attribute]}})
        g['animations'].append(animation);reports.append({'clip':label,'seconds':clip.duration,'tracks':len(tracks),'unmapped_bindings':len(clip.unmapped),'samples':count+1})
    g['buffers'][0]['byteLength']=len(blob);(folder/'source.bin').write_bytes(blob);path.write_text(json.dumps(g,allow_nan=False)+'\n');(folder/'animation-review.json').write_text(json.dumps({'clips':reports,'head_tail_rigs_attached':True,'game_integrated':False},indent=2)+'\n')
    print(folder.name,reports,flush=True)


def main():
    for c in json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters']:animate(ROOT/'modding/uma-steam/fleet'/str(c['id']))

if __name__=='__main__':main()
