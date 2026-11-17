"""Build review-only glTF with original Steam skins and assembled head/tail prefabs."""
import json,sys,math,sqlite3
from pathlib import Path
import numpy as np
from read_uma_motion import rotation
ROOT=Path(__file__).resolve().parents[2]
MIRROR=np.diag([-1.,1.,1.,1.])


def build(folder,body_scale,mini=False):
    source=json.loads((folder/'raw-model.json').read_text());objects={(o['file'],o['path_id']):o for o in source['objects']};externals={f['file']:f['externals'] for f in source['files']}
    def pointer(file,p):
        target=file if p['m_FileID']==0 else externals[file][p['m_FileID']-1].replace('\\','/').split('/')[-1]
        return target,p['m_PathID']
    neutral={}
    for obj in objects.values():
        if obj['type']!='MonoBehaviour':continue
        for field in ('_eyeTarget','_eyebrowTarget','_mouthTarget','_targetFaces'):
            targets=obj['data'].get(field,[])
            if not targets:continue
            for group in targets[0].get('_faceGroupInfo',[]):
                for trs in group['_trsArray']:neutral[trs['_path']]=trs
    transforms={k:o for k,o in objects.items() if o['type']=='Transform'};names={};parents={};local={};world={};active=set();neutral_applied=[]
    for key,obj in transforms.items():
        data=obj['data'];go=objects[pointer(key[0],data['m_GameObject'])]['data'];names[key]=go['m_Name'];parents[key]=pointer(key[0],data['m_Father']) if data['m_Father']['m_PathID'] else None
        p=np.array([data['m_LocalPosition'][c] for c in 'xyz']);q=np.array([data['m_LocalRotation'][c] for c in 'xyzw']);scale=np.array([data['m_LocalScale'][c] for c in 'xyz'])
        r=rotation(q)
        if names[key] in neutral:
            trs=neutral[names[key]];p=np.array([trs['_position'][c] for c in 'xyz']);scale=np.array([trs['_scale'][c] for c in 'xyz']);x,y,z=np.radians([trs['_rotation'][c] for c in 'xyz'])
            rx=np.array([[1,0,0],[0,math.cos(x),-math.sin(x)],[0,math.sin(x),math.cos(x)]]);ry=np.array([[math.cos(y),0,math.sin(y)],[0,1,0],[-math.sin(y),0,math.cos(y)]]);rz=np.array([[math.cos(z),-math.sin(z),0],[math.sin(z),math.cos(z),0],[0,0,1]])
            r=rz@ry@rx;neutral_applied.append(names[key])
        m=np.eye(4);m[:3,:3]=r@np.diag(scale);m[:3,3]=p;local[key]=m
    def matrix(key):
        if key in world:return world[key]
        if key in active:raise ValueError('Transform cycle')
        active.add(key);parent=parents[key];world[key]=matrix(parent)@local[key] if parent else local[key];active.remove(key);return world[key]
    for key in transforms:matrix(key)
    def root(key):
        while parents[key]:key=parents[key]
        return key
    roots={key for key in transforms if parents[key] is None};body=next(k for k in roots if names[k].startswith('pfb_mbdy' if mini else 'pfb_bdy'));head=next(k for k in roots if names[k].startswith('pfb_mchr' if mini else 'pfb_chr') and (not mini or names[k].endswith('_hair')));tail=None if mini else next(k for k in roots if names[k].startswith('pfb_tail'))
    def named(r,name):
        found=[k for k in transforms if root(k)==r and names[k]==name]
        if len(found)!=1:raise ValueError('Ambiguous attachment '+name)
        return found[0]
    placement={k:np.eye(4) for k in roots};placement[head]=world[named(body,'Neck')]@np.linalg.inv(world[named(head,'Neck')]);
    if tail is not None:placement[tail]=world[named(body,'Hip')]@np.linalg.inv(world[named(tail,'Hip')])
    if mini:
        face=next(k for k in roots if names[k]=='pfb_mchr0001_00_face0');placement[face]=world[named(body,'Neck')]@np.linalg.inv(world[named(face,'Neck')])
    result={'asset':{'version':'2.0','generator':'Local Uma source review'},'scene':0,'scenes':[{'nodes':[]}],'nodes':[],'skins':[],'meshes':[],'materials':[],'images':[],'textures':[],'samplers':[{'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':10497}],'accessors':[],'bufferViews':[],'buffers':[{'uri':'source.bin','byteLength':0}]};blob=bytearray()
    def accessor(array,kind,component=5126):
        dtype={5126:'<f4',5123:'<u2',5125:'<u4'}[component];a=np.ascontiguousarray(array,dtype=dtype)
        if not np.isfinite(a).all():raise ValueError('Nonfinite buffer')
        blob.extend(bytes((-len(blob))%4));start=len(blob);data=a.tobytes();blob.extend(data);view=len(result['bufferViews']);result['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(data)})
        item={'bufferView':view,'componentType':component,'count':len(a),'type':kind}
        if kind=='VEC3' and component==5126:item.update(min=a.min(axis=0).tolist(),max=a.max(axis=0).tolist())
        index=len(result['accessors']);result['accessors'].append(item);return index
    node_index={k:i for i,k in enumerate(transforms)}
    for key,obj in transforms.items():
        m=local[key] if parents[key] else placement[key]@local[key];m=MIRROR@m@MIRROR
        result['nodes'].append({'name':names[key],'matrix':m.T.reshape(-1).tolist(),'children':[]})
    for key,index in node_index.items():
        if parents[key]:result['nodes'][node_index[parents[key]]]['children'].append(index)
        else:result['scenes'][0]['nodes'].append(index)
    texture_index={}
    for texture in source['textures']:
        i=len(result['images']);result['images'].append({'uri':texture['png']});result['textures'].append({'source':i,'sampler':0});texture_index[(texture['file'],texture['path_id'])]=i
    material_index={}
    skin=None
    if mini:
        master=Path('/home/nemesis/.local/share/Steam/steamapps/common/UmamusumePrettyDerby/UmamusumePrettyDerby_Data/Persistent/master/master.mdb')
        with sqlite3.connect(master.as_uri()+'?mode=ro&immutable=1',uri=True) as db:skin=db.execute('SELECT skin FROM chara_data WHERE id=?',(source['id'],)).fetchone()[0]
    for key,obj in objects.items():
        if obj['type']!='Material':continue
        data=obj['data'];name=data['m_Name'];properties=dict(data['m_SavedProperties']['m_TexEnvs']);entry={'name':name,'pbrMetallicRoughness':{'metallicFactor':0,'roughnessFactor':.8},'doubleSided':True}
        texture=None
        if mini:
            wanted=None
            if name.endswith('_face0'):wanted=f'tex_mchr0001_00_face0_{skin}_diff'
            elif name.endswith('_eye'):wanted=f'tex_mchr{source["id"]}_00_eye_diff'
            elif name.endswith(('_mayu_r','_mayu_l')):wanted=f'tex_mchr{source["id"]}_00_mayu_diff'
            elif name.endswith('_mouth'):wanted=f'tex_mchr{source["id"]}_00_mouth_diff'
            elif name.endswith('_cheek'):wanted=f'tex_mchr0001_00_face0_{skin}_cheek0'
            if wanted:
                found=[t for t in source['textures'] if t['name']==wanted]
                if len(found)!=1:raise ValueError('Missing mini facial texture '+wanted)
                texture=texture_index[(found[0]['file'],found[0]['path_id'])]
        if 'tail' in name:
            found=[t for t in source['textures'] if t['name']==f'tex_tail0001_00_{source["id"]}_diff']
            if len(found)==1:texture=texture_index[(found[0]['file'],found[0]['path_id'])]
        if texture is None and properties.get('_MainTex',{}).get('m_Texture',{}).get('m_PathID'):
            texture=texture_index[pointer(key[0],properties['_MainTex']['m_Texture'])]
        if texture is not None:
            texinfo={'index':texture};mapping=properties.get('_MainTex')
            if mapping:
                sx,sy=mapping['m_Scale']['x'],mapping['m_Scale']['y'];ox,oy=mapping['m_Offset']['x'],mapping['m_Offset']['y']
                if (sx,sy,ox,oy)!=(1,1,0,0):
                    result['extensionsUsed']=['KHR_texture_transform'];texinfo['extensions']={'KHR_texture_transform':{'scale':[sx,sy],'offset':[ox,1-sy-oy]}}
            entry['pbrMetallicRoughness']['baseColorTexture']=texinfo
        # shortcut: source toon/mask shaders need a separate NFS material pass; this is a diffuse preview.
        if any(token in name for token in ('hair','tail','eye','mayu','cheek')):entry.update(alphaMode='MASK',alphaCutoff=.4)
        if mini and name.endswith('_mouth'):entry.update(alphaMode='MASK',alphaCutoff=.4)
        material_index[key]=len(result['materials']);result['materials'].append(entry)
    mesh_records={(m['file'],m['path_id']):m for m in source['meshes']};go_transform={pointer(k[0],o['data']['m_GameObject']):k for k,o in transforms.items()}
    exported_vertices=0;unbound=[]
    for key,obj in objects.items():
        if obj['type'] not in (('SkinnedMeshRenderer','MeshRenderer') if mini else ('SkinnedMeshRenderer',)) or not obj['data']['m_Enabled']:continue
        data=obj['data'];node=go_transform[pointer(key[0],data['m_GameObject'])]
        if mini and names[node]=='M_Cheek':continue
        ancestor=node;enabled=True
        while ancestor:
            go=objects[pointer(ancestor[0],transforms[ancestor]['data']['m_GameObject'])]['data'];enabled &= bool(go['m_IsActive']);ancestor=parents[ancestor]
        if not enabled:continue
        mesh_pointer=data.get('m_Mesh')
        if mesh_pointer is None:
            filters=[o for k,o in objects.items() if o['type']=='MeshFilter' and pointer(k[0],o['data']['m_GameObject'])==pointer(key[0],data['m_GameObject'])]
            if len(filters)!=1:raise ValueError('Static renderer mesh filter ambiguous')
            mesh_pointer=filters[0]['data']['m_Mesh']
        record=mesh_records[pointer(key[0],mesh_pointer)];arrays=np.load(folder/record['archive']);p=arrays['positions'].copy();n=arrays['normals'].copy();uv=arrays['uv'].copy();p[:,0]*=-1;n[:,0]*=-1;uv[:,1]=1-uv[:,1]
        skin_index=None
        if obj['type']=='SkinnedMeshRenderer':
            if 'weights' not in arrays:raise ValueError('Skinned renderer without skin')
            attributes={'POSITION':accessor(p,'VEC3'),'NORMAL':accessor(n,'VEC3'),'TEXCOORD_0':accessor(uv,'VEC2'),'JOINTS_0':accessor(arrays['bones'],'VEC4',5123),'WEIGHTS_0':accessor(arrays['weights'],'VEC4')}
            joints=[node_index[pointer(key[0],b)] for b in data['m_Bones']]
            if int(arrays['bones'][arrays['weights']>0].max())>=len(joints) or len(arrays['bind_poses'])!=len(joints):raise ValueError('Skin joint count mismatch')
            bind=np.array([(MIRROR@m@MIRROR).T.reshape(-1) for m in arrays['bind_poses']]);skin={'joints':joints,'inverseBindMatrices':accessor(bind,'MAT4')};skin_index=len(result['skins']);result['skins'].append(skin)
        else:attributes={'POSITION':accessor(p,'VEC3'),'NORMAL':accessor(n,'VEC3'),'TEXCOORD_0':accessor(uv,'VEC2')}
        primitives=[]
        for material in np.unique(arrays['material']):
            if int(material)>=len(data['m_Materials']):
                unbound.append({'mesh':record['name'],'submesh':int(material)});continue
            triangles=arrays['triangles'][arrays['material']==material][:,::-1].reshape(-1,1)
            material_key=pointer(key[0],data['m_Materials'][int(material)]);primitive_attributes=attributes
            primitives.append({'attributes':primitive_attributes,'indices':accessor(triangles,'SCALAR',5125),'material':material_index[material_key]})
        mesh_index=len(result['meshes']);result['meshes'].append({'name':record['name'],'primitives':primitives});result['nodes'][node_index[node]].update(mesh=mesh_index);exported_vertices+=len(p)
        if skin_index is not None:result['nodes'][node_index[node]]['skin']=skin_index
    if not 0<exported_vertices<65536 or len(result['skins'])<(2 if mini else 3):raise ValueError('Incomplete character')
    if not mini and not neutral_applied:raise ValueError('Missing native facial neutral pose')
    scale_node=len(result['nodes']);result['nodes'].append({'name':'CharacterScale','scale':[body_scale]*3,'children':result['scenes'][0]['nodes']});result['scenes'][0]['nodes']=[scale_node]
    result['buffers'][0]['byteLength']=len(blob);(folder/'source.bin').write_bytes(blob);(folder/'source.gltf').write_text(json.dumps(result,allow_nan=False)+'\n')
    (folder/'assembly-report.json').write_text(json.dumps({'name':source['name'],'vertices':exported_vertices,'skins':len(result['skins']),'head_attachment':'Neck rest transform','tail_attachment':None if mini else 'Hip rest transform','game_integrated':False,'visual_approved':False,'unbound_submeshes_skipped':unbound,'native_neutral_transforms':len(neutral_applied),'body_scale':body_scale,'eye_depth_pass_required':True},indent=2)+'\n')
    print(source['name'],exported_vertices,'visible vertices;',len(result['skins']),'skins assembled',flush=True)


def main():
    mini='--mini' in sys.argv[1:]
    for c in json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters']:build(ROOT/'modding/uma-steam'/('mini-fleet' if mini else 'fleet')/str(c['id']),1 if mini else c['body_scale'],mini)

if __name__=='__main__':main()
