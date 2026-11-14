"""Retarget an original local Uma race clip to the existing PMX mesh, without game writes."""
import json
from pathlib import Path
import numpy as np
from animate_kitasan import Rig,align
from read_uma_motion import OriginalRig,DenseMotion
from pack_motion import topology
from inspect_assets import ROOT

class UmaRetarget:
    def __init__(self,clip='anm_rac_type03_run02_base'):
        self.target=Rig();self.source=OriginalRig();self.clip=DenseMotion(clip,self.source);self.order=topology(self.target.bones)
        self.axes=np.array([[0,0,1],[1,0,0],[0,1,0]],dtype=float)
        ratios=[]
        for target,source in [('左足D','Thigh_L'),('右足D','Thigh_R'),('左腕','Arm_L'),('右腕','Arm_R')]:
            end_target=target.replace('足D','ひざD').replace('腕','ひじ');end_source=source.replace('Thigh','Knee').replace('Arm','Elbow')
            ratios.append(np.linalg.norm(self.target.rest[self.target.named[end_target]]-self.target.rest[self.target.named[target]])/np.linalg.norm(self.source.rest_position[self.source.named[end_source]]-self.source.rest_position[self.source.named[source]]))
        self.scale=float(np.median(ratios))
        self.orientation={'腰':'Hip','上半身':'Waist','上半身2':'Chest','首':'Neck','頭':'Head'}
        for side,suffix in [('左','L'),('右','R')]:self.orientation[side+'肩']='Shoulder_'+suffix
        self.limbs=[]
        for side,suffix in [('左','L'),('右','R')]:
            for start,end,sstart,send in [('足D','ひざD','Thigh','Knee'),('ひざD','足首D','Knee','Ankle'),('足首D','足先EX','Ankle','Toe'),('腕','ひじ','Arm','Elbow'),('ひじ','手首','Elbow','Wrist'),('手首','中指１','Wrist','Middle_01')]:
                self.limbs.append((self.target.named[side+start],self.target.named[side+end],self.source.named[sstart+'_'+suffix],self.source.named[send+'_'+suffix]))

    def source_rotation(self,sr,index):
        return self.axes@(sr[index]@self.source.rest_rotation[index].T)@self.axes.T

    @staticmethod
    def hand_frame(primary,across):
        x=primary/np.linalg.norm(primary);y=across-x*(x@across);y/=np.linalg.norm(y)
        return np.column_stack((x,y,np.cross(x,y)))

    def pose(self,phase,amount=1):
        if amount==0:return self.target.pose(phase,0)
        if amount!=1:raise ValueError('Blend in the runtime local-quaternion player')
        target=self.target;source=self.source;sr,sp=source.pose(self.clip.channels(phase));desired={}
        # Preserve the existing authored fist/secondary motion, replacing all primary body poses.
        old_r,_,_,_=target.pose(phase,1);local=np.empty_like(old_r)
        for i,bone in enumerate(target.bones):local[i]=old_r[i] if bone['parent']<0 else old_r[bone['parent']].T@old_r[i]
        for name in ('全ての親','センター','グルーブ','下半身'):
            if name in target.named:local[target.named[name]]=np.eye(3)
        for name,sname in self.orientation.items():
            i=source.named[sname];desired[target.named[name]]=self.source_rotation(sr,i)
        for start,end,sstart,send in self.limbs:
            rest=target.rest[end]-target.rest[start];source_rest=self.axes@(source.rest_position[send]-source.rest_position[sstart])
            goal=self.source_rotation(sr,sstart)@align(rest,source_rest)
            desired[start]=align(goal@rest,self.axes@(sp[send]-sp[sstart]))@goal
        for side,suffix in [('左','L'),('右','R')]:
            wrist=target.named[side+'手首'];sw=source.named['Wrist_'+suffix]
            hand=target.rest[target.named[side+'中指１']]-target.rest[wrist];across=target.rest[target.named[side+'小指１']]-target.rest[target.named[side+'人指１']]
            sh=self.axes@(sp[source.named['Middle_01_'+suffix]]-sp[sw]);sa=self.axes@(sp[source.named['Pinky_01_'+suffix]]-sp[source.named['Index_01_'+suffix]])
            desired[wrist]=self.hand_frame(sh,sa)@self.hand_frame(hand,across).T
            for target_name,source_name,numbers in [('親指','Thumb','０１２'),('人指','Index','１２３'),('中指','Middle','１２３'),('薬指','Ring','１２３'),('小指','Pinky','１２３')]:
                for j,number in enumerate(numbers):
                    bone=target.named[side+target_name+number];sb=source.named[f'{source_name}_{j+1:02d}_{suffix}']
                    if j<2:
                        next_bone=target.named[side+target_name+numbers[j+1]];next_sb=source.named[f'{source_name}_{j+2:02d}_{suffix}'];rest=target.rest[next_bone]-target.rest[bone];srdir=self.axes@(source.rest_position[next_sb]-source.rest_position[sb]);posed=self.axes@(sp[next_sb]-sp[sb])
                    else:
                        parent=target.bones[bone]['parent'];sparent=source.bones[sb]['parent'];rest=target.rest[bone]-target.rest[parent];srdir=self.axes@(source.rest_position[sb]-source.rest_position[sparent]);posed=None
                    goal=self.source_rotation(sr,sb)@align(rest,srdir)
                    desired[bone]=align(goal@rest,posed)@goal if posed is not None else goal
        rotation=np.zeros_like(local);positions=np.zeros_like(target.rest);translation=np.zeros_like(target.rest)
        hip=source.named['Hip'];translation[target.named['センター']]=self.axes@(sp[hip]-source.rest_position[hip])*self.scale
        for i in self.order:
            parent=target.bones[i]['parent'];pr=rotation[parent] if parent>=0 else np.eye(3)
            if i in desired:local[i]=pr.T@desired[i]
            rotation[i]=pr@local[i]
            positions[i]=target.rest[i]+translation[i] if parent<0 else positions[parent]+pr@(target.rest[i]-target.rest[parent]+translation[i])
        offset=positions-np.einsum('bij,bj->bi',rotation,target.rest)
        mesh,_=target.skin(rotation,offset);rise=max(0,-.0001-float(mesh[:,2].min()));offset[:,2]+=rise;positions[:,2]+=rise
        return rotation,offset,positions,[]

def main():
    retarget=UmaRetarget();out=ROOT/'modding/animation-steam-retarget';out.mkdir(exist_ok=False);bounds=[]
    for name,amount,count in [('idle',0,32),('run',1,48)]:
        rotations=[];offsets=[]
        for frame in range(count):
            r,t,p,_=retarget.pose(frame/count,amount);mesh,normals=retarget.target.skin(r,t)
            if not np.isfinite(mesh).all() or abs(np.linalg.det(r)-1).max()>1e-5:raise ValueError('Invalid retargeted pose')
            rotations.append(r.astype('<f4'));offsets.append(t.astype('<f4'));bounds.append([mesh.min(0).tolist(),mesh.max(0).tolist()])
        np.savez_compressed(out/(name+'.npz'),rotations=np.array(rotations),offsets=np.array(offsets))
    report={'source_clip':retarget.clip.name,'source_duration':retarget.clip.duration,'source_character':1068,'source_race_style':3,'limb_scale_median':retarget.scale,'mapped_core_limb_pairs':len(retarget.limbs),'unmapped_source_bindings':len(retarget.clip.unmapped),'unmapped_policy':'Source bindings absent from body-prefab hierarchy are excluded; primary limb bindings resolved','secondary_motion':'Authored hair/tail local curves; source palms and 30 finger bones retargeted','minimum':np.array(bounds)[:,0].min(0).tolist(),'maximum':np.array(bounds)[:,1].max(0).tolist(),'installed':False}
    (out/'retarget-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
