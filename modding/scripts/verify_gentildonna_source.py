"""Validate the complete permitted PMX source before runtime conversion; no game writes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
from inspect_assets import ROOT


def verify():
    manifest=json.loads((ROOT/'modding/blender-review/gentildonna/manifest.json').read_text())
    source=ROOT/manifest['source_file']
    assert hashlib.sha256(source.read_bytes()).hexdigest()==manifest['source_sha256']
    reader=ROOT/'modding/tools/blender_mmd_tools/mmd_tools/core/pmx/__init__.py'
    spec=importlib.util.spec_from_file_location('gentildonna_pmx_reader',reader)
    pmx=importlib.util.module_from_spec(spec);spec.loader.exec_module(pmx)
    model=pmx.load(str(source))
    assert len(model.vertices)==manifest['vertices'] and len(model.faces)==manifest['triangles']
    # Blender adds helper materials; validate the native PMX table separately.
    assert len(model.materials)==35 and len(model.bones)==271
    positions=np.array([v.co for v in model.vertices]);normals=np.array([v.normal for v in model.vertices]);uv=np.array([v.uv for v in model.vertices])
    assert np.isfinite(positions).all() and np.isfinite(normals).all() and np.isfinite(uv).all()
    faces=np.array(model.faces);assert faces.shape==(44672,3) and faces.min()>=0 and faces.max()<len(positions)
    assert sum(m.vertex_count for m in model.materials)==faces.size
    assert all(m.vertex_count>=0 and m.vertex_count%3==0 for m in model.materials)
    for vertex in model.vertices:
        weight=vertex.weight
        assert weight.type in (0,1,2)
        weights=[1.] if weight.type==0 else ([weight.weights[0],1-weight.weights[0]] if weight.type==1 else weight.weights)
        assert len(weights)==len(weight.bones) and np.isfinite(weights).all()
        assert min(weights)>=0 and max(weights)<=1 and abs(sum(weights)-1)<1e-5
        assert all(0<=bone<len(model.bones) for bone,value in zip(weight.bones,weights) if value>0)
    for index in range(len(model.bones)):
        visited=set();current=index
        while current>=0:
            assert current<len(model.bones) and current not in visited,'Invalid bone hierarchy'
            visited.add(current);current=model.bones[current].parent
    textures=[]
    for texture in model.textures:
        path=Path(texture.path)
        if not path.is_absolute():path=ROOT/path
        path=path.resolve();path.relative_to((ROOT/'modding/model-sources/gentildonna').resolve())
        assert path.is_file(),path
        textures.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    edges=positions[faces[:,1]]-positions[faces[:,0]];other=positions[faces[:,2]]-positions[faces[:,0]]
    report={'source_sha256':manifest['source_sha256'],'vertices':len(positions),'triangles':len(faces),'bones':len(model.bones),'rigid_bodies':len(model.rigids),'joints':len(model.joints),'materials':len(model.materials),'textures':textures,'uv_min':uv.min(0).tolist(),'uv_max':uv.max(0).tolist(),'degenerate_triangles':int((np.linalg.norm(np.cross(edges,other),axis=1)<1e-10).sum()),'nonunit_normals':int((abs(np.linalg.norm(normals,axis=1)-1)>1e-3).sum()),'checks':['source digest','complete parser counts','finite geometry and UV','index bounds','material triangle coverage','bone weights and references','acyclic hierarchy','texture containment and presence'],'installed':False,'gameplay_verified':False}
    out=ROOT/'modding/blender-review/gentildonna/source-validation.json'
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='textures'},indent=2))
    return model,report

if __name__=='__main__':verify()
