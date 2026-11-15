"""Compare the C player to Python hierarchy/skinning without starting the game."""
import argparse
import json
import struct
import subprocess
import numpy as np
from animate_kitasan import Rig
from pack_motion import topology
from inspect_assets import ROOT


def blend_quaternions(a,b,t):
    dot=(a*b).sum(-1,keepdims=True);b=np.where(dot<0,-b,b)
    value=a+(b-a)*t
    return value/np.linalg.norm(value,axis=-1,keepdims=True)


def interpolate(clip,phase):
    phase=float(np.float32(phase));position=(phase-np.floor(phase))*len(clip)
    a=int(position);b=(a+1)%len(clip);t=np.float32(position-a)
    out=clip[a]+(clip[b]-clip[a])*t
    out[:,:4]=blend_quaternions(clip[a,:,:4],clip[b,:,:4],t)
    return out


def rotation_matrix(quaternions):
    x,y,z,w=quaternions.T
    r=np.empty((len(x),3,3),dtype=float)
    r[:,0,0]=1-2*(y*y+z*z);r[:,0,1]=2*(x*y-z*w);r[:,0,2]=2*(x*z+y*w)
    r[:,1,0]=2*(x*y+z*w);r[:,1,1]=1-2*(x*x+z*z);r[:,1,2]=2*(y*z-x*w)
    r[:,2,0]=2*(x*z-y*w);r[:,2,1]=2*(y*z+x*w);r[:,2,2]=1-2*(x*x+y*y)
    return r


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--asset',default='modding/runtime/kitasan.umab');parser.add_argument('--clips');args=parser.parse_args()
    asset_path=(ROOT/args.asset).resolve()
    manifest=json.loads(asset_path.with_suffix('.json').read_text()) if asset_path.with_suffix('.json').exists() else {}
    clips_path=(ROOT/(args.clips or manifest.get('reference_clip_directory','modding/animation-offline-v2'))).resolve()
    for path in (asset_path,clips_path):path.relative_to((ROOT/'modding').resolve())
    reference_clips={}
    for name in ('idle','run'):
        with np.load(clips_path/(name+'.npz'),allow_pickle=False) as clip:reference_clips[name]=(clip['rotations'].copy(),clip['offsets'].copy())
    build=ROOT/'modding/runtime/test-build';build.mkdir(exist_ok=True)
    rig=Rig();order=topology(rig.bones);data=asset_path.read_bytes()
    _,version,nv,ni,nb,idle_count,run_count,_=struct.unpack_from('<4s7I',data)
    if version!=2 or nv!=rig.vertices or nb!=len(rig.bones):raise ValueError('Playback format mismatch')
    offset=32+nv*60+nb*16+((ni*2+3)//4)*4
    idle=np.frombuffer(data,'<f4',idle_count*nb*7,offset).reshape(idle_count,nb,7);offset+=idle.nbytes
    run=np.frombuffer(data,'<f4',run_count*nb*7,offset).reshape(run_count,nb,7)
    cases=[(0,0,0),(0,.25,1),(.0625,.1875,.5),(.031,.079,.3),(-1,-1,1),(1,1,0)];floor=[]
    with (build/'reference.bin').open('wb') as f:
        f.write(struct.pack('<I',len(cases)))
        for ip,rp,blend in cases:
            blend=np.float32(blend);a=interpolate(idle,ip);b=interpolate(run,rp);mixed=a+(b-a)*blend
            mixed[:,:4]=blend_quaternions(a[:,:4],b[:,:4],blend)
            local=np.empty((nb,3,3));translation=np.empty((nb,3));local[order]=rotation_matrix(mixed[:,:4]);translation[order]=mixed[:,4:]
            rotation,positions=rig.world(local,translation);offsets=positions-np.einsum('bij,bj->bi',rotation,rig.rest)
            p,n=rig.skin(rotation,offsets);floor.append(float(p[:,2].min()))
            if blend in (0,1):
                reference_r,reference_t=reference_clips['run' if blend else 'idle'];phase=(rp if blend else ip)%1;key=phase*len(reference_r)
                if abs(key-round(key))>1e-5:raise ValueError('Reference check requires exact key phase')
                original_r,original_t=reference_r[int(round(key))%len(reference_r)],reference_t[int(round(key))%len(reference_t)];original_p,original_n=rig.skin(original_r,original_t)
                if not np.allclose(p,original_p,atol=1e-5) or not np.allclose(n,original_n,atol=1e-5):raise ValueError('Packed key pose differs from authored motion')
            for bone in range(nb):
                parent=rig.bones[bone]['parent']
                if parent>=0 and np.linalg.norm(translation[bone])<1e-6:
                    if abs(np.linalg.norm(positions[bone]-positions[parent])-np.linalg.norm(rig.rest[bone]-rig.rest[parent]))>1e-5:raise ValueError('Blending stretched a bone')
            p[:,2]+=max(0,-.0001-float(p[:,2].min()))
            values=np.column_stack((p,n)).astype('<f4');f.write(struct.pack('<3f',ip,rp,blend));f.write(values.tobytes())
    executable=build/'motion_test'
    subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',str(ROOT/'modding/runtime/motion_test.c'),'-o',str(executable),'-lm'],check=True,cwd=ROOT)
    result=subprocess.run([str(executable),str(asset_path)],check=True,capture_output=True,text=True,cwd=ROOT)
    report={'standalone_test':result.stdout.strip(),'key_poses_match_reference_clips':True,'reference_clip_directory':str(clips_path.relative_to(ROOT)),'asset':str(asset_path.relative_to(ROOT)),'blended_bone_lengths_checked':True,'surface_min_z_before_root_correction_by_case':floor,'grounded_transition_poses_checked':240,'support_plane_tolerance_m':.000101,'game_launched':False,'game_integrated':False}
    (build/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(result.stdout,end='');print('Surface min z before root correction:',floor)

if __name__=='__main__':main()
