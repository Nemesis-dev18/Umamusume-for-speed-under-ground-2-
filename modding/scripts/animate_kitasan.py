"""Author idle/run motion offline from the matched Kitasan rig. Not gameplay."""
import argparse
import json
import math
from pathlib import Path
import struct
import numpy as np
from inspect_assets import ROOT


def ry(angle):
    c,s=math.cos(angle),math.sin(angle)
    return np.array([[c,0,s],[0,1,0],[-s,0,c]])


def rz(angle):
    c,s=math.cos(angle),math.sin(angle)
    return np.array([[c,-s,0],[s,c,0],[0,0,1]])


def align(a,b):
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
    an,bn=np.linalg.norm(a),np.linalg.norm(b)
    if min(an,bn)<1e-9:raise ValueError('Cannot align zero-length limb')
    a=a/an;b=b/bn;c=float(np.clip(a@b,-1,1));v=np.cross(a,b)
    if c>1-1e-10:return np.eye(3)
    if c<-1+1e-10:
        axis=np.cross(a,np.eye(3)[int(np.argmin(np.abs(a)))])
        axis/=np.linalg.norm(axis)
        return 2*np.outer(axis,axis)-np.eye(3)
    k=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    return np.eye(3)+k+k@k/(1+c)


def leg_target(phase,ankle,amount):
    phase=phase%1;stance=.38;stride=.62
    if phase<stance:
        x=stride*.5-stride*phase/stance;height=0;pitch=0
    else:
        u=(phase-stance)/(1-stance);slope=-stride*(1-stance)/stance
        x=(2*u**3-3*u*u+1)*(-stride*.5)+(u**3-2*u*u+u)*slope+(-2*u**3+3*u*u)*(stride*.5)+(u**3-u*u)*slope
        height=.28*math.sin(math.pi*u)**2;pitch=-.25*math.sin(math.pi*u)**2
    target=ankle.copy();target[0]+=amount*x;target[2]+=amount*height
    return target,amount*pitch,phase<stance


class Rig:
    def __init__(self):
        folder=ROOT/'modding/character-source';raw=(folder/'mesh.bin').read_bytes()
        self.vertices,self.index_count=struct.unpack_from('<II',raw)
        if len(raw)!=8+self.vertices*36+self.index_count*4:raise ValueError('Mesh length mismatch')
        self.records=np.ndarray((self.vertices,9),'<f4',raw,8).copy()
        self.bones=json.loads((folder/'skeleton.json').read_text())
        self.rest=np.array([b['position'] for b in self.bones]);self.named={b['name']:i for i,b in enumerate(self.bones)}
        skin=(folder/'skin.bin').read_bytes()
        if len(skin)!=self.vertices*24:raise ValueError('Skin length mismatch')
        self.ids=np.ndarray((self.vertices,4),'<u2',skin,0,strides=(24,2)).copy()
        self.weights=np.ndarray((self.vertices,4),'<f4',skin,8,strides=(24,4)).copy()
        if self.ids.max()>=len(self.bones) or not np.isfinite(self.weights).all() or np.any(self.weights<0) or not np.allclose(self.weights.sum(1),1,atol=1e-5):raise ValueError('Invalid skin weights')
        self.world(np.repeat(np.eye(3)[None],len(self.bones),0),np.zeros_like(self.rest))

    def world(self,local,translation):
        rotations=np.zeros_like(local);positions=np.zeros_like(self.rest);active=set();done=set()
        def solve(i):
            if i in done:return
            if i in active:raise ValueError('Bone parent cycle')
            active.add(i);parent=self.bones[i]['parent']
            if parent<0:rotations[i]=local[i];positions[i]=self.rest[i]+translation[i]
            else:
                if parent>=len(self.bones):raise ValueError('Bone parent out of bounds')
                solve(parent);rotations[i]=rotations[parent]@local[i]
                positions[i]=positions[parent]+rotations[parent]@(self.rest[i]-self.rest[parent]+translation[i])
            active.remove(i);done.add(i)
        for i in range(len(self.bones)):solve(i)
        return rotations,positions

    def pose(self,phase,amount=1):
        if not math.isfinite(phase) or not math.isfinite(amount) or not 0<=amount<=1:raise ValueError('Invalid motion input')
        phase=phase%1;t=2*math.pi*phase
        local=np.repeat(np.eye(3)[None],len(self.bones),0);translation=np.zeros_like(self.rest)
        center=self.named['センター'];translation[center]=[0,-.012*amount*math.cos(t),-.035-.065*amount+(.004+.014*amount)*math.cos(2*t)]
        local[self.named['上半身']]=ry(.03+.22*amount)@rz(.045*amount*math.sin(t))
        local[self.named['上半身2']]=rz(-.07*amount*math.sin(t))
        local[self.named['頭']]=ry(-.08*amount)
        r,p=self.world(local,translation);feet=[]
        for side,offset in [('左',0),('右',.5)]:
            hip,knee,ankle=[self.named[side+name+'D'] for name in ('足','ひざ','足首')]
            target,pitch,stance=leg_target(phase+offset,self.rest[ankle],amount)
            h=p[hip];upper=self.rest[knee]-self.rest[hip];lower=self.rest[ankle]-self.rest[knee]
            a,b=np.linalg.norm(upper),np.linalg.norm(lower);direction=target-h;distance=np.linalg.norm(direction)
            if distance<1e-9:raise ValueError('Foot target coincides with hip')
            distance=min(max(distance,abs(a-b)+1e-5),a+b-1e-5);unit=direction/np.linalg.norm(direction)
            along=(a*a-b*b+distance*distance)/(2*distance);height=math.sqrt(max(0,a*a-along*along))
            bend=np.array([1.,0,0])-unit*unit[0];bend/=max(np.linalg.norm(bend),1e-9)
            k=h+unit*along+bend*height;reachable=h+unit*distance
            parent=self.bones[hip]['parent'];parent_r=r[parent] if parent>=0 else np.eye(3)
            local[hip]=align(upper,parent_r.T@(k-h));hip_r=parent_r@local[hip]
            local[knee]=align(lower,hip_r.T@(reachable-k));knee_r=hip_r@local[knee]
            local[ankle]=knee_r.T@ry(pitch)
            feet.append({'ankle':ankle,'target':target,'reachable':reachable,'stance':stance})
        r,p=self.world(local,translation)
        for side,sign,offset in [('左',-1,0),('右',1,.5)]:
            upper,elbow,wrist=[self.named[side+name] for name in ('腕','ひじ','手首')]
            swing=-math.cos(2*math.pi*(phase+offset))*amount
            upper_rest=self.rest[elbow]-self.rest[upper];lower_rest=self.rest[wrist]-self.rest[elbow]
            desired_upper=np.array([.12*swing,sign*.045,-.235]);desired_upper*=np.linalg.norm(upper_rest)/np.linalg.norm(desired_upper)
            parent=self.bones[upper]['parent'];parent_r=r[parent]
            local[upper]=align(upper_rest,parent_r.T@desired_upper)
            upper_r=parent_r@local[upper]
            run_forearm=np.array([.235,sign*-.025,.12*swing])
            desired_lower=(1-amount)*np.array([.06,sign*-.025,-.225])+amount*run_forearm
            desired_lower*=np.linalg.norm(lower_rest)/np.linalg.norm(desired_lower)
            local[elbow]=align(lower_rest,upper_r.T@desired_lower)
        for side in ('左','右'):
            for finger in ('小指','薬指','中指','人指'):
                joints=[self.named[side+finger+number] for number in '１２３']
                for j,(bone,angle) in enumerate(zip(joints,(.5,.75,.6))):
                    direction=self.rest[joints[j+1]]-self.rest[bone] if j<2 else self.rest[bone]-self.rest[joints[j-1]]
                    direction=direction/np.linalg.norm(direction)
                    palm=np.array([1.,0,0])-direction*direction[0];palm/=np.linalg.norm(palm)
                    angle*=.12+.88*amount
                    local[bone]=align(direction,math.cos(angle)*direction+math.sin(angle)*palm)
            for number,angle in [('１',.2),('２',.3)]:
                bone=self.named[side+'親指'+number];parent=self.bones[bone]['parent']
                direction=self.rest[bone]-self.rest[parent];direction/=np.linalg.norm(direction)
                palm=np.array([1.,0,0])-direction*direction[0];palm/=np.linalg.norm(palm)
                local[bone]=align(direction,math.cos(angle*amount)*direction+math.sin(angle*amount)*palm)
        # Secondary motion is authored, not a substitute for MMD cloth simulation.
        for name,amplitude,lag in [('前髪',.018,.5),('後髪',.035,.8),('左髪ツインテ',.05,1.0),('右髪ツインテ',.05,1.2),('尻尾親',.055,1.4)]:
            if name in self.named:local[self.named[name]]=ry(amplitude*amount*math.sin(2*t-lag))
        r,p=self.world(local,translation);offset=p-np.einsum('bij,bj->bi',r,self.rest)
        return r,offset,p,feet

    def skin(self,rotation,offset):
        positions=np.sum((np.einsum('vkij,vj->vki',rotation[self.ids],self.records[:,:3])+offset[self.ids])*self.weights[:,:,None],axis=1)
        normals=np.sum(np.einsum('vkij,vj->vki',rotation[self.ids],self.records[:,3:6])*self.weights[:,:,None],axis=1)
        normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-9)
        if not np.isfinite(positions).all() or not np.isfinite(normals).all():raise ValueError('Nonfinite skinned mesh')
        return positions,normals


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='animation-offline')
    args=parser.parse_args();relative=Path(args.output)
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('Output must stay in modding')
    rig=Rig();destination=ROOT/'modding'/relative
    for parent in (destination,*destination.parents):
        if parent==ROOT:break
        if parent.is_symlink():raise ValueError('Output symlink excluded')
    destination.mkdir(exist_ok=False);report={'gameplay':False,'runtime_integrated':False,'clips':[]}
    for name,amount,count in [('idle',0.,32),('run',1.,48)]:
        rotations=[];offsets=[];metrics=[]
        for frame in range(count):
            rotation,offset,joints,feet=rig.pose(frame/count,amount);p,n=rig.skin(rotation,offset)
            error=max(float(np.linalg.norm(joints[f['ankle']]-f['target'])) for f in feet)
            if error>.005:raise ValueError('Foot target is outside achievable reach')
            rotations.append(rotation.astype('<f4'));offsets.append(offset.astype('<f4'))
            metrics.append({'min':p.min(0).tolist(),'max':p.max(0).tolist(),'foot_target_error':error})
        np.savez_compressed(destination/f'{name}.npz',rotations=np.array(rotations),offsets=np.array(offsets))
        report['clips'].append({'name':name,'frames':count,'max_foot_target_error':max(m['foot_target_error'] for m in metrics),'frames_bounds':metrics})
    (destination/'motion-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Authored offline idle/run clips; planted-foot IK and finite skin checks passed. Not gameplay.')

if __name__=='__main__':main()
