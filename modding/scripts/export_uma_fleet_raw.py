"""Export cached Unity meshes, skin weights, material references and textures for Blender review."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'modding/uma-steam'
sys.path.insert(0,str(WORK/'python-deps'))
import numpy as np
import UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler


def main():
    fleet=json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())
    for character in fleet['characters']:
        folder=WORK/'fleet'/str(character['id']);inventory=json.loads((folder/'source-inventory.json').read_text())
        env=UnityPy.load(*(str(WORK/'fleet-bundles'/(h+'.unity3d')) for h in inventory['dependencies']))
        (folder/'meshes').mkdir(exist_ok=True);(folder/'textures').mkdir(exist_ok=True)
        objects=[];meshes=[];textures=[]
        for obj in env.objects:
            kind=obj.type.name;file=str(obj.assets_file.name);key=str(obj.path_id)
            if kind in {'Transform','GameObject','Avatar','Animator','SkinnedMeshRenderer','MeshFilter','MeshRenderer','Material','MonoBehaviour'}:
                objects.append(dict(file=file,path_id=obj.path_id,type=kind,data=obj.read_typetree()))
            elif kind=='Mesh':
                source=obj.read();handler=MeshHandler(source);handler.process()
                p=np.asarray(handler.m_Vertices,dtype=np.float32);n=np.asarray(handler.m_Normals,dtype=np.float32)[:,:3];uv=np.asarray(handler.m_UV0,dtype=np.float32)
                triangles=[];materials=[]
                for index,submesh in enumerate(handler.get_triangles()):
                    submesh=np.asarray(submesh,dtype=np.uint32).reshape(-1,3);triangles.extend(submesh);materials.extend([index]*len(submesh))
                t=np.asarray(triangles,dtype=np.uint32).reshape(-1,3)
                if not 0<len(p)<=65535 or p.shape!=(len(p),3) or n.shape!=p.shape or uv.shape!=(len(p),2) or not len(t) or int(t.max())>=len(p):raise ValueError('Mesh outside supported bounds')
                if not all(np.isfinite(a).all() for a in (p,n,uv)):raise ValueError('Nonfinite vertex data')
                arrays=dict(positions=p,normals=n,uv=uv,triangles=t,material=np.array(materials,dtype=np.uint16))
                skin=handler.m_BoneWeights is not None
                if skin:
                    weights=np.asarray(handler.m_BoneWeights,dtype=np.float32);bones=np.asarray(handler.m_BoneIndices,dtype=np.int32)
                    if weights.shape!=(len(p),4) or bones.shape!=weights.shape or not np.isfinite(weights).all() or np.min(weights)<0 or np.max(abs(weights.sum(axis=1)-1))>.01:raise ValueError('Invalid source skin')
                    bind=obj.read_typetree().get('m_BindPose',[])
                    if not bind or np.max(bones[weights>0])>=len(bind):raise ValueError('Skin references missing bind pose')
                    arrays.update(weights=weights,bones=bones,bind_poses=np.array([[[m[f'e{r}{c}'] for c in range(4)] for r in range(4)] for m in bind],dtype=np.float32))
                path=folder/'meshes'/(key+'.npz');np.savez_compressed(path,**arrays)
                meshes.append(dict(file=file,path_id=obj.path_id,name=source.m_Name,vertices=len(p),triangles=len(t),skinned=skin,archive=str(path.relative_to(folder))))
            elif kind=='Texture2D':
                texture=obj.read();name=re.sub(r'[^A-Za-z0-9_.-]','_',texture.m_Name);path=folder/'textures'/(name+'_'+key+'.png')
                image=texture.image;image.save(path)
                textures.append(dict(file=file,path_id=obj.path_id,name=texture.m_Name,width=image.width,height=image.height,png=str(path.relative_to(folder))))
        files=[]
        for asset in env.assets:
            files.append(dict(file=str(asset.name),externals=[str(e.path) for e in asset.externals]))
        report=dict(id=character['id'],name=character['name'],nfs_slot=character['nfs_slot'],coordinates='Original Unity mesh local coordinates; no game-axis conversion yet',files=files,objects=objects,meshes=meshes,textures=textures,game_integrated=False)
        (folder/'raw-model.json').write_text(json.dumps(report,ensure_ascii=False,allow_nan=False)+'\n')
        print(character['name'],sum(m['vertices'] for m in meshes),'raw vertices;',len(objects),'hierarchy/material records',flush=True)

if __name__=='__main__':main()
