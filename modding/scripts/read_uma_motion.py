"""Decode downloaded Unity dense clips and evaluate their original transform hierarchy."""
import json
import math
from pathlib import Path
import zlib
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'modding/uma-steam/bundles'

def vector(value,names):return np.array([value[n] for n in names],dtype=float)
def rotation(q):
    q=np.asarray(q,dtype=float);length=np.linalg.norm(q)
    if not math.isfinite(length) or length<1e-8:raise ValueError('Invalid source quaternion')
    x,y,z,w=q/length
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

class OriginalRig:
    def __init__(self):
        objects=json.loads((DATA/'kitasan-body-rig.json').read_text())
        names={o['path_id']:o['data']['m_Name'] for o in objects if o['type']=='GameObject'}
        transforms={o['path_id']:o['data'] for o in objects if o['type']=='Transform'}
        self.bones=[];self.order=[];self.paths={};self.unresolved=[];active=set()
        def add(key):
            if key in self.order:return self.order.index(key)
            if key in active:raise ValueError('Source hierarchy cycle')
            active.add(key);t=transforms[key];parent=t['m_Father']['m_PathID'];index=add(parent) if parent else -1
            name=names[t['m_GameObject']['m_PathID']];path=self.bones[index]['path']+'/'+name if index>=0 else name
            self.bones.append({'name':name,'path':path,'parent':index,'position':vector(t['m_LocalPosition'],'xyz'),'quaternion':vector(t['m_LocalRotation'],'xyzw'),'scale':vector(t['m_LocalScale'],'xyz')});self.order.append(key);active.remove(key);return len(self.bones)-1
        for key in transforms:add(key)
        self.named={b['name']:i for i,b in enumerate(self.bones)}
        avatar=next(o['data'] for o in objects if o['type']=='Avatar')
        for key,path in avatar['m_TOS']:
            if zlib.crc32(path.encode())!=key:raise ValueError('Avatar path CRC mismatch')
            matches=[i for i,b in enumerate(self.bones) if (b['parent']<0 if not path else b['path']==path or b['path'].endswith('/'+path))]
            if not matches:self.unresolved.append(path);continue
            if len(matches)!=1:raise ValueError(f'Avatar path ambiguous: {path}')
            self.paths[key]=matches[0]
        self.rest_rotation,self.rest_position=self.pose({})

    def pose(self,channels):
        rotations=[];positions=[];scales=[]
        for i,b in enumerate(self.bones):
            p=channels.get((i,1),b['position']);q=channels.get((i,2),b['quaternion']);scale=channels.get((i,3),b['scale']);r=rotation(q);parent=b['parent']
            if not np.isfinite(p).all() or not np.allclose(scale,1,atol=1e-5):raise ValueError('Unsupported translated/nonunit source scale')
            if parent>=0:p=positions[parent]+rotations[parent]@p;r=rotations[parent]@r
            positions.append(p);rotations.append(r);scales.append(scale)
        return np.array(rotations),np.array(positions)

class DenseMotion:
    def __init__(self,name,rig):
        self.name=name;data=json.loads((DATA/(name+'.json')).read_text());muscle=data['m_MuscleClip'];clip=muscle['m_Clip']['data']
        if clip['m_StreamedClip']['curveCount']:raise ValueError('Streamed channels require separate decoding')
        dense=clip['m_DenseClip'];self.rate=dense['m_SampleRate'];self.stop=muscle['m_StopTime'];self.start=muscle['m_StartTime'];self.duration=self.stop-self.start
        self.dense=np.array(dense['m_SampleArray']).reshape(dense['m_FrameCount'],dense['m_CurveCount']);self.constant=np.array(clip['m_ConstantClip']['data']);self.bindings=[];self.unmapped=[];cursor=0
        for b in data['m_ClipBindingConstant']['genericBindings']:
            if b['typeID']!=4 or b['attribute'] not in (1,2,3):raise ValueError('Unsupported transform binding')
            count=4 if b['attribute']==2 else 3
            if b['path'] in rig.paths:self.bindings.append((rig.paths[b['path']],b['attribute'],cursor,count))
            else:self.unmapped.append(b)
            cursor+=count
        if cursor!=self.dense.shape[1]+len(self.constant) or not np.isfinite(self.dense).all() or not np.isfinite(self.constant).all():raise ValueError('Source channel count mismatch')
        if not 0<self.duration<10 or self.stop*self.rate>len(self.dense)-1:raise ValueError('Invalid clip duration')

    def channels(self,phase):
        frame=((phase%1)*self.duration+self.start)*self.rate;a=int(frame);b=min(a+1,len(self.dense)-1);t=frame-a
        first=np.concatenate((self.dense[a],self.constant));second=np.concatenate((self.dense[b],self.constant));result={}
        for bone,attribute,start,count in self.bindings:
            x=first[start:start+count];y=second[start:start+count]
            if attribute==2:
                if x@y<0:y=-y
                value=x*(1-t)+y*t;value/=np.linalg.norm(value)
            else:value=x*(1-t)+y*t
            result[bone,attribute]=value
        return result

if __name__=='__main__':
    rig=OriginalRig()
    for name in ['Hip','Spine','Chest','Arm_L','Elbow_L','Wrist_L','Thigh_L','Knee_L','Ankle_L']:
        if name in rig.named:print(name,rig.rest_position[rig.named[name]])
    for name in ['anm_rac_type03_run02_base','anm_rac_type03_run03_base']:
        clip=DenseMotion(name,rig);r,p=rig.pose(clip.channels(0));print(name,'seconds',clip.duration,'bindings',len(clip.bindings),'bones',len(r));print('posed hips',p[rig.named['Hip']]);print('posed left arm',[(n,p[rig.named[n]].tolist()) for n in ['Arm_L','Elbow_L','Wrist_L'] if n in rig.named])
