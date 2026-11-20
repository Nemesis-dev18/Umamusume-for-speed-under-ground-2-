"""Pack local quaternion motion for standalone playback, not the EAGL loader."""
import hashlib
import json
import struct
from pathlib import Path
import numpy as np
from inspect_assets import ROOT


def topology(bones):
    order=[];active=set();done=set()
    def visit(i):
        if i in done:return
        if i in active:raise ValueError('Bone cycle')
        active.add(i);parent=bones[i]['parent']
        if parent>=len(bones):raise ValueError('Invalid parent')
        if parent>=0:visit(parent)
        active.remove(i);done.add(i);order.append(i)
    for i in range(len(bones)):visit(i)
    return np.array(order,dtype=int)


def quaternion(matrix):
    # Eigenvector form is stable near a half-turn; the player uses a separate formula.
    m=matrix
    k=np.array([[m[0,0]-m[1,1]-m[2,2],m[1,0]+m[0,1],m[2,0]+m[0,2],m[2,1]-m[1,2]],
                [m[1,0]+m[0,1],m[1,1]-m[0,0]-m[2,2],m[2,1]+m[1,2],m[0,2]-m[2,0]],
                [m[2,0]+m[0,2],m[2,1]+m[1,2],m[2,2]-m[0,0]-m[1,1],m[1,0]-m[0,1]],
                [m[2,1]-m[1,2],m[0,2]-m[2,0],m[1,0]-m[0,1],np.trace(m)]])
    _,vectors=np.linalg.eigh(k);q=vectors[:,-1]
    return q if q[3]>=0 else -q


def pack(clips_directory=None,source_folder=None):
    manifest=ROOT/'modding/runtime/kitasan.json'
    current=json.loads(manifest.read_text()) if manifest.exists() else {}
    clips_directory=clips_directory or ROOT/current.get('reference_clip_directory','modding/animation-offline-v2')
    clips_directory.resolve().relative_to((ROOT/'modding').resolve())
    folder=Path(source_folder) if source_folder is not None else ROOT/'modding/character-source';folder.resolve().relative_to((ROOT/'modding').resolve());mesh=(folder/'mesh.bin').read_bytes()
    nv,ni=struct.unpack_from('<II',mesh);skin=(folder/'skin.bin').read_bytes()
    bones=json.loads((folder/'skeleton.json').read_text());nb=len(bones)
    if len(mesh)!=8+nv*36+ni*4 or len(skin)!=nv*24:raise ValueError('Source size mismatch')
    ids=np.frombuffer(mesh,'<u4',ni,8+nv*36)
    if ids.max()>=nv or nv>65535 or ni%3:raise ValueError('Invalid triangle indices')
    records=np.frombuffer(mesh,'u1',nv*36,8).reshape(nv,36).copy()
    colors=records[:,32:36].copy();uv=records[:,24:32].copy()
    records[:,24:28]=colors[:,[2,1,0,3]];records[:,28:36]=uv
    order=topology(bones);remap=np.empty(nb,dtype='<u2');remap[order]=np.arange(nb)
    rest=np.array([b['position'] for b in bones]);skeleton=bytearray()
    for i in order:
        parent=bones[i]['parent'];parent=int(remap[parent]) if parent>=0 else -1
        skeleton.extend(struct.pack('<hH3f',parent,0,*rest[i]))
    skin_out=bytearray(skin)
    for i in range(nv):
        old=struct.unpack_from('<4H',skin,i*24)
        if max(old)>=nb:raise ValueError('Invalid skin index')
        struct.pack_into('<4H',skin_out,i*24,*(int(remap[j]) for j in old))
    clips=[];counts=[]
    for name in ('idle','run'):
        with np.load(clips_directory/f'{name}.npz',allow_pickle=False) as clip:
            r=clip['rotations'].astype(float);t=clip['offsets'].astype(float)
            if r.ndim!=4 or r.shape[1:]!=(nb,3,3) or t.shape!=r.shape[:2]+(3,) or not np.isfinite(r).all() or not np.isfinite(t).all():raise ValueError('Invalid motion arrays')
            positions=np.einsum('fbij,bj->fbi',r,rest)+t
            local=np.empty((len(r),nb,7),dtype='<f4')
            for frame in range(len(r)):
                for destination,i in enumerate(order):
                    parent=bones[i]['parent']
                    if parent<0:rotation=r[frame,i];translation=positions[frame,i]-rest[i]
                    else:
                        rotation=r[frame,parent].T@r[frame,i]
                        translation=r[frame,parent].T@(positions[frame,i]-positions[frame,parent])-(rest[i]-rest[parent])
                    left,_,right=np.linalg.svd(rotation);rotation=left@right
                    if np.linalg.det(rotation)<0:raise ValueError('Reflected bone rotation')
                    translation[np.abs(translation)<2e-6]=0
                    local[frame,destination,:4]=quaternion(rotation);local[frame,destination,4:]=translation
            counts.append(len(r));clips.append(local.tobytes())
    indexbytes=ids.astype('<u2').tobytes();padding=b'\0'*((-len(indexbytes))%4)
    header=struct.pack('<4s7I',b'UMAB',2,nv,ni,nb,*counts,0)
    return header+records.tobytes()+bytes(skin_out)+bytes(skeleton)+indexbytes+padding+b''.join(clips)


def main():
    data=pack();output=ROOT/'modding/runtime/kitasan.umab'
    # This is generated authoring data, never an installed game resource.
    output.write_bytes(data)
    report={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'format':'UMAB v2; local quaternions, translations and parent hierarchy; not an EAGL container','game_integrated':False,'reference_clip_directory':json.loads(output.with_suffix('.json').read_text()).get('reference_clip_directory','modding/animation-offline-v2')}
    output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
