"""Import the isolated Gentildonna PMX copy with a pinned MMD Tools reader, without game edits."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import bpy
import addon_utils

ROOT=Path(__file__).resolve().parents[2]
repo=ROOT/'modding/tools/blender_mmd_tools'
# The reader is now vendored in the project, not an independent Git checkout.
subprocess.run(['git','-C',str(ROOT),'diff','--exit-code','HEAD','--',str(repo.relative_to(ROOT))],check=True,stdout=subprocess.DEVNULL)
reader_hash=hashlib.sha256()
for file in sorted((repo/'mmd_tools').rglob('*.py')):
    reader_hash.update(str(file.relative_to(repo)).encode());reader_hash.update(file.read_bytes())
revision='vendored-sha256:'+reader_hash.hexdigest()
sys.path.insert(0,str(repo))
sys.path.insert(0,str(ROOT/'modding/tools/mmd-python-deps'))
addon_utils.enable('mmd_tools',default_set=True)
assert 'mmd_tools' in bpy.context.preferences.addons
sources=list((ROOT/'modding/model-sources/gentildonna').rglob('*.pmx'));assert len(sources)==1
source=sources[0];before=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.mmd_tools.import_model(filepath=str(source),scale=.1,types={'MESH','ARMATURE','MORPHS','DISPLAY'},clean_model=False,save_log=False)
meshes=[o for o in bpy.data.objects if o.type=='MESH'];rigs=[o for o in bpy.data.objects if o.type=='ARMATURE']
assert meshes and len(rigs)==1 and len(rigs[0].data.bones)>100
assert 1000<sum(len(o.data.vertices) for o in meshes)<200000
missing=[i.filepath for i in bpy.data.images if i.source=='FILE' and i.filepath and not Path(bpy.path.abspath(i.filepath)).is_file()]
assert not missing,missing
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
out=ROOT/'modding/blender-review/gentildonna';out.mkdir(parents=True,exist_ok=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'gentildonna-source.blend'))
report={'source_sha256':before,'reader_commit':revision,'mesh_objects':len(meshes),'vertices':sum(len(o.data.vertices) for o in meshes),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),'bones':len(rigs[0].data.bones),'materials':len(bpy.data.materials),'images':len(bpy.data.images),'missing_textures':missing,'scope':'Gentildonna import with author permission confirmed by user; no runtime export or game installation','source_file':str(source.relative_to(ROOT))}
(out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
