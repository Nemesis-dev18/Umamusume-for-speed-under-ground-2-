"""Stage native-resolution PMX geometry, skin and material ranges; never install it."""
import json
import struct
import numpy as np
from inspect_assets import ROOT
from verify_gentildonna_source import verify


def main():
    model,validation=verify()
    out=ROOT/'modding/staged-runtime/gentildonna-source';out.mkdir(parents=True,exist_ok=True)
    axes=np.array([[0,0,-1],[-1,0,0],[0,1,0]],dtype=float)
    assert np.isclose(np.linalg.det(axes),1)
    native=np.array([v.co for v in model.vertices]);scale=1.78/float(np.ptp(native[:,1]))
    positions=native@axes.T*scale
    normals=np.array([v.normal for v in model.vertices])@axes.T
    uv=np.array([v.uv for v in model.vertices]);indices=np.array(model.faces,dtype='<u4')
    mesh=bytearray(struct.pack('<II',len(positions),indices.size));skin=bytearray()
    for i,vertex in enumerate(model.vertices):
        mesh.extend(struct.pack('<8f4B',*positions[i],*normals[i],*uv[i],255,255,255,255))
        weight=vertex.weight;values=[1.] if weight.type==0 else ([weight.weights[0],1-weight.weights[0]] if weight.type==1 else weight.weights)
        ids=[bone if value else 0 for bone,value in zip(weight.bones,values)]
        skin.extend(struct.pack('<4H4f',*(ids+[0]*(4-len(ids))),*(list(values)+[0.]*(4-len(values)))))
    mesh.extend(indices.tobytes())
    bones=[{'name':b.name,'parent':b.parent,'position':(np.array(b.location)@axes.T*scale).tolist()} for b in model.bones]
    ranges=[];start=0
    for material in model.materials:
        ranges.append({'name':material.name,'first_index':start,'index_count':material.vertex_count,'texture_index':material.texture,'double_sided':material.is_double_sided,'diffuse':list(material.diffuse)})
        start+=material.vertex_count
    assert start==indices.size
    (out/'mesh.bin').write_bytes(mesh);(out/'skin.bin').write_bytes(skin)
    (out/'skeleton.json').write_text(json.dumps(bones,ensure_ascii=False,indent=2)+'\n')
    (out/'materials.json').write_text(json.dumps(ranges,ensure_ascii=False,indent=2)+'\n')
    # Verify serialization round-trip before any retargeting or renderer conversion.
    decoded=np.ndarray((len(positions),8),'<f4',mesh,8,strides=(36,4))
    assert np.allclose(decoded[:,:3],positions,atol=1e-6) and np.allclose(decoded[:,3:6],normals,atol=1e-6)
    assert np.array_equal(decoded[:,6:8],uv.astype('<f4'))
    assert np.array_equal(np.frombuffer(mesh,'<u4',indices.size,8+len(positions)*36),indices.ravel())
    assert len(skin)==len(positions)*24
    receipt={'target_height':1.78,'pmx_to_game_scale':scale,'source_sha256':validation['source_sha256'],'installed':False,'runtime_ready':False,'geometry_decimated':False,'textures_resized':False,'material_batches':len(ranges),'axis_determinant':float(np.linalg.det(axes)),'minimum':positions.min(0).tolist(),'maximum':positions.max(0).tolist(),'remaining':['PMX grant/IK handling and retarget validation','per-material native texture renderer','secondary physics conversion and garment collision','independent GPU and gameplay checks']}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
