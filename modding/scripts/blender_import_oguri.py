"""Import the isolated Oguri PMX copy with a pinned MMD Tools reader, without game edits."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import bpy
import addon_utils

ROOT=Path(__file__).resolve().parents[2]
repo=ROOT/'modding/tools/blender_mmd_tools'
revision=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
assert revision=='f1d8a98db5e185cfa73c9b8a8a67fa42d9eb4b14'
sys.path.insert(0,str(repo))
sys.path.insert(0,str(ROOT/'modding/tools/mmd-python-deps'))
addon_utils.enable('mmd_tools',default_set=True)
assert 'mmd_tools' in bpy.context.preferences.addons
sources=list((ROOT/'modding/model-sources/00').rglob('*.pmx'));assert len(sources)==1
source=sources[0];before=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.mmd_tools.import_model(filepath=str(source),scale=.1,types={'MESH','ARMATURE','MORPHS','DISPLAY'},clean_model=False,save_log=False)
meshes=[o for o in bpy.data.objects if o.type=='MESH'];rigs=[o for o in bpy.data.objects if o.type=='ARMATURE']
assert meshes and len(rigs)==1 and len(rigs[0].data.bones)>100
assert sum(len(o.data.vertices) for o in meshes)>30000
missing=[i.filepath for i in bpy.data.images if i.source=='FILE' and i.filepath and not Path(bpy.path.abspath(i.filepath)).is_file()]
assert not missing,missing
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
out=ROOT/'modding/blender-review/oguri';out.mkdir(parents=True,exist_ok=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'oguri-source.blend'))
report={'source_sha256':before,'reader_commit':revision,'mesh_objects':len(meshes),'vertices':sum(len(o.data.vertices) for o in meshes),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),'bones':len(rigs[0].data.bones),'materials':len(bpy.data.materials),'images':len(bpy.data.images),'missing_textures':missing,'scope':'Source import only, no runtime export or game installation'}
(out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
