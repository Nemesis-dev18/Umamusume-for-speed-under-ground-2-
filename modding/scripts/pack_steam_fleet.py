"""Stage native glTF skins as UMAB motion; never install or edit game resources."""
import json,struct,hashlib
from pathlib import Path
import numpy as np
from read_uma_motion import rotation
from pack_motion import quaternion
ROOT=Path(__file__).resolve().parents[2]
AXES=np.array([[0.,0.,1.],[-1.,0.,0.],[0.,1.,0.]])


class NativeSkin:
    def __init__(self,folder,secondary=False):
        self.folder=folder;self.g=json.loads((folder/'source.gltf').read_text());self.blob=(folder/'source.bin').read_bytes()
        if len(self.g['buffers'])!=1 or self.g['buffers'][0]['byteLength']!=len(self.blob):raise ValueError('Source buffer length mismatch')
        self.parents={}
        for i,n in enumerate(self.g['nodes']):
            for child in n.get('children',[]):
                if child in self.parents:raise ValueError('Multiple node parents')
                self.parents[child]=i
        self.order=[];active=set();done=set()
        def visit(i):
            if i in done:return
            if i in active:raise ValueError('Node cycle')
            active.add(i)
            if i in self.parents:visit(self.parents[i])
            active.remove(i);done.add(i);self.order.append(i)
        for i in range(len(self.g['nodes'])):visit(i)
        self.rest=self.world()
        self.animations={a['name']:a for a in self.g['animations']}
        self.animated={c['target']['node'] for a in self.animations.values() for c in a['channels']}
        self.secondary_nodes=set()
        if secondary:
            inventory=json.loads((ROOT/'modding/uma-steam/secondary-native/structural-summary.json').read_text())
            native=next(c for c in inventory if c['id']==int(folder.name))
            names={n['_boneName'] for a in native['assets'] if a['logical'].endswith('_cloth00') and '_bust_' not in a['logical'] for n in a['nodes'] if '_Bust' not in n['_boneName'] and '_Ear' not in n['_boneName']}
            self.secondary_nodes={i for i,n in enumerate(self.g['nodes']) if n.get('name') in names}
            if {self.g['nodes'][i]['name'] for i in self.secondary_nodes}!=names:raise ValueError('Unresolved secondary joint names')
        self.driven=self.animated|self.secondary_nodes
        needed=set(self.driven)
        for i in list(needed):
            while i in self.parents:i=self.parents[i];needed.add(i)
        self.bone_order=[i for i in self.order if i in needed]
        if not 0<len(self.bone_order)<=512:raise ValueError('Unsupported joint budget')
        self.remap={i:j for j,i in enumerate(self.bone_order)}

    def moving_parent(self,i):
        while i not in self.driven and i in self.parents:i=self.parents[i]
        if i not in self.remap:raise ValueError('Unrepresented static root')
        return i

    def array(self,index):
        a=self.g['accessors'][index];v=self.g['bufferViews'][a['bufferView']]
        if 'sparse' in a or v.get('byteStride') or v.get('buffer',0):raise ValueError('Unsupported accessor layout')
        width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];dtype={5126:'<f4',5123:'<u2',5125:'<u4'}[a['componentType']]
        offset=v.get('byteOffset',0)+a.get('byteOffset',0);length=a['count']*width*np.dtype(dtype).itemsize
        if offset<0 or offset+length>len(self.blob) or a.get('byteOffset',0)+length>v['byteLength']:raise ValueError('Accessor outside buffer')
        result=np.frombuffer(self.blob,dtype,count=a['count']*width,offset=offset).reshape(-1,width)
        if not np.isfinite(result).all():raise ValueError('Nonfinite accessor')
        return result

    def world(self,overrides=None):
        result={};overrides=overrides or {}
        for i in self.order:
            n=self.g['nodes'][i]
            if 'matrix' in n:
                if i in overrides:raise ValueError('Animated matrix node')
                local=np.array(n['matrix']).reshape(4,4).T
            else:
                values={k:n.get(k,default) for k,default in [('translation',[0,0,0]),('rotation',[0,0,0,1]),('scale',[1,1,1])]};values.update(overrides.get(i,{}))
                local=np.eye(4);local[:3,:3]=rotation(np.array(values['rotation']))@np.diag(values['scale']);local[:3,3]=values['translation']
            result[i]=result[self.parents[i]]@local if i in self.parents else local
        return result

    def pose(self,label,frame):
        animation=self.animations[label];overrides={}
        for channel in animation['channels']:
            s=animation['samplers'][channel['sampler']]
            if s.get('interpolation','LINEAR')!='LINEAR':raise ValueError('Unsupported animation interpolation')
            values=self.array(s['output']);overrides.setdefault(channel['target']['node'],{})[channel['target']['path']]=values[frame]
        return self.world(overrides)

    def primitives(self):
        for i in self.order:
            n=self.g['nodes'][i]
            if 'mesh' not in n:continue
            skin=self.g['skins'][n['skin']];ibm=self.array(skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
            for p in self.g['meshes'][n['mesh']]['primitives']:
                a={k:self.array(v) for k,v in p['attributes'].items()};ids=self.array(p['indices']).reshape(-1)
                bind=np.array([self.rest[j]@b for j,b in zip(skin['joints'],ibm)]);matrices=(bind[a['JOINTS_0']]*a['WEIGHTS_0'][:,:,None,None]).sum(1)
                points=np.einsum('nij,nj->ni',matrices[:,:3,:3],a['POSITION'])+matrices[:,:3,3];triangles=ids.reshape(-1,3);area=np.linalg.norm(np.cross(points[triangles[:,1]]-points[triangles[:,0]],points[triangles[:,2]]-points[triangles[:,0]]),axis=1);hidden=area<1e-14
                for index in np.flatnonzero(hidden):
                    tri=triangles[index];ancestors={self.moving_parent(skin['joints'][int(j)]) for v in tri for j,w in zip(a['JOINTS_0'][v],a['WEIGHTS_0'][v]) if w>0}
                    if len(ancestors)!=1:
                        if self.secondary_nodes:hidden[index]=False
                        else:raise ValueError('Degenerate triangle may open during animation')
                ids=triangles[~hidden].reshape(-1)
                if not len(ids):continue
                used,inverse=np.unique(ids,return_inverse=True)
                yield {'node':i,'material':p['material'],'attributes':{k:v[used] for k,v in a.items()},'indices':inverse,'joints':skin['joints'],'ibm':ibm,'static_degenerate_triangles_removed':int(hidden.sum())}

    def deform(self,p,world):
        a=p['attributes'];matrices=np.array([world[j]@b for j,b in zip(p['joints'],p['ibm'])]);weighted=matrices[a['JOINTS_0']]*a['WEIGHTS_0'][:,:,None,None]
        matrix=weighted.sum(axis=1);positions=np.einsum('nij,nj->ni',matrix[:,:3,:3],a['POSITION'])+matrix[:,:3,3]
        normals=np.einsum('nij,nj->ni',matrix[:,:3,:3],a['NORMAL']);length=np.linalg.norm(normals,axis=1)
        if np.min(length)<1e-8 or not np.isfinite(positions).all():raise ValueError('Invalid deformed surface')
        normals/=length[:,None]
        return positions,normals


def pack(folder,secondary=False,output=None):
    source=NativeSkin(folder,secondary);primitives=list(source.primitives());nb=len(source.bone_order)
    rest=np.array([AXES@source.rest[i][:3,3] for i in source.bone_order]);records=[];skins=[];indices=[];groups=[];offset=0
    for p in primitives:
        a=p['attributes'];positions,normals=source.deform(p,source.rest);positions=positions@AXES.T;normals=normals@AXES.T
        # Static facial corrections can include zero scale. Bake them before merging influences with identical animated ancestry.
        bind=np.array([source.rest[j]@b for j,b in zip(p['joints'],p['ibm'])]);moving=[source.moving_parent(j) for j in p['joints']]
        merged_bones=np.zeros((len(positions),4),dtype='<u2');merged_weights=np.zeros((len(positions),4),dtype='<f4')
        for v in range(len(positions)):
            contributions={}
            for joint,weight in zip(a['JOINTS_0'][v],a['WEIGHTS_0'][v]):
                if not weight:continue
                ancestor=moving[int(joint)];entry=contributions.setdefault(ancestor,[0.,np.zeros(3)])
                entry[0]+=weight;entry[1]+=weight*(bind[joint][:3,:3]@a['POSITION'][v]+bind[joint][:3,3])
            for k,(ancestor,(weight,point)) in enumerate(contributions.items()):
                if not np.allclose(AXES@(point/weight),positions[v],atol=2e-5):raise ValueError('Different animated influences require separate bind positions')
                merged_bones[v,k]=source.remap[ancestor];merged_weights[v,k]=weight
        material=source.g['materials'][p['material']];uv=a['TEXCOORD_0'].copy();tex=material['pbrMetallicRoughness'].get('baseColorTexture')
        if tex:
            transform=tex.get('extensions',{}).get('KHR_texture_transform',{});uv=uv*np.array(transform.get('scale',[1,1]))+np.array(transform.get('offset',[0,0]))
        first=len(indices);local_indices=p['indices'].reshape(-1,3)[:,::-1].reshape(-1)+offset;indices.extend(local_indices.tolist())
        group={'material':material['name'],'first_index':first,'index_count':len(local_indices),'first_vertex':offset,'vertex_count':len(positions),'texture':tex['index'] if tex else None,'eye_depth_off':material['name'].endswith('_eye'),'static_degenerate_triangles_removed':p['static_degenerate_triangles_removed']};groups.append(group)
        for v in range(len(positions)):records.append(struct.pack('<6f4B2f',*positions[v],*normals[v],255,255,255,255,*uv[v]))
        for b,w in zip(merged_bones,merged_weights):skins.append(struct.pack('<4H4f',*b,*w))
        offset+=len(positions)
    if not 0<offset<65536:raise ValueError('16-bit vertex limit')
    skeleton=b''.join(struct.pack('<hH3f',source.remap[source.parents[i]] if i in source.parents else -1,0,*rest[j]) for j,i in enumerate(source.bone_order))
    clips=[];reports=[]
    for label in ('idle','run'):
        animation=source.animations[label];times=source.array(animation['samplers'][0]['input'])[:,0]
        if len(times)<3 or not np.allclose(np.diff(times),np.diff(times)[0],rtol=1e-4) or times[0]!=0:raise ValueError('Nonuniform clip samples')
        frames=len(times)-1;poses=[]
        for frame in range(frames):
            world=source.pose(label,frame);deltas=[];positions=[]
            for i in source.bone_order:
                delta=world[i]@np.linalg.inv(source.rest[i]);r=AXES@delta[:3,:3]@AXES.T
                if not np.allclose(r.T@r,np.eye(3),atol=2e-4) or np.linalg.det(r)<.999:raise ValueError('Nonrigid skin animation')
                deltas.append(r);positions.append(AXES@world[i][:3,3])
            pose=[]
            for j,i in enumerate(source.bone_order):
                parent=source.remap[source.parents[i]] if i in source.parents else -1
                r=deltas[j] if parent<0 else deltas[parent].T@deltas[j]
                t=positions[j]-rest[j] if parent<0 else deltas[parent].T@(positions[j]-positions[parent])-(rest[j]-rest[parent])
                pose.append([*quaternion(r),*t])
            poses.append(pose)
        data=np.asarray(poses,dtype='<f4')
        if not np.isfinite(data).all() or np.max(np.abs(data))>10:raise ValueError('Runtime clip range')
        clips.append(data.tobytes());reports.append({'name':label,'frames':frames,'seconds':float(times[-1]),'duplicate_endpoint_removed':True})
    index_data=np.asarray(indices,dtype='<u2').tobytes();header=struct.pack('<4s7I2f',b'UMAB',3,offset,len(indices),nb,*(r['frames'] for r in reports),0,*(r['seconds'] for r in reports))
    data=header+b''.join(records)+b''.join(skins)+skeleton+index_data+bytes((-len(index_data))%4)+b''.join(clips)
    output=Path(output) if output is not None else folder/'runtime';output.resolve().relative_to(ROOT.resolve());output.mkdir(parents=True,exist_ok=True);(output/'model.umab').write_bytes(data)
    report={'id':int(folder.name),'vertices':offset,'indices':len(indices),'bones':nb,'clips':reports,'groups':groups,'sha256':hashlib.sha256(data).hexdigest(),'source_sha256':hashlib.sha256((folder/'source.gltf').read_bytes()).hexdigest(),'source_buffer_sha256':hashlib.sha256(source.blob).hexdigest(),'game_integrated':False,'atlas_pending':True,'eye_depth_pass_pending':True}
    if secondary:report.update(secondary_retained=True,bone_names=[source.g['nodes'][i].get('name','') for i in source.bone_order],secondary_bone_indices=[source.remap[i] for i in source.bone_order if i in source.secondary_nodes])
    (output/'model.json').write_text(json.dumps(report,indent=2)+'\n');print(folder.name,offset,len(indices),nb,flush=True)
    return source,primitives,report


def main():
    for c in json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters']:pack(ROOT/'modding/uma-steam/fleet'/str(c['id']))

if __name__=='__main__':main()
