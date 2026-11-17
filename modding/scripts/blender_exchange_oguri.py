"""Export and round-trip a local skinned exchange model; not a game installation."""
from pathlib import Path
import hashlib
import json
import sys
import bpy
import addon_utils

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'modding/tools/blender_mmd_tools'))
sys.path.insert(0,str(ROOT/'modding/tools/mmd-python-deps'))
addon_utils.enable('mmd_tools',default_set=True)
folder=ROOT/'modding/blender-review/oguri';source=folder/'oguri-source.blend';before=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source));bpy.ops.object.select_all(action='DESELECT')
objects=[obj for obj in bpy.data.objects if obj.type in {'MESH','ARMATURE'}];assert objects
for obj in objects:
    obj.hide_set(False);obj.select_set(True)
    if obj.type=='MESH':
        for modifier in obj.modifiers:
            if modifier.type!='ARMATURE':modifier.show_viewport=modifier.show_render=False
for material in list(bpy.data.materials):
    if not material.use_nodes:continue
    base=material.node_tree.nodes.get('mmd_base_tex');image=base.image if base else None
    diffuse=tuple(material.diffuse_color)
    material.node_tree.nodes.clear();nodes=material.node_tree.nodes;links=material.node_tree.links
    output_node=nodes.new('ShaderNodeOutputMaterial');shader=nodes.new('ShaderNodeBsdfPrincipled');shader.inputs['Base Color'].default_value=diffuse;shader.inputs['Roughness'].default_value=.8
    links.new(shader.outputs['BSDF'],output_node.inputs['Surface'])
    if image:
        texture=nodes.new('ShaderNodeTexImage');texture.image=image;links.new(texture.outputs['Color'],shader.inputs['Base Color']);links.new(texture.outputs['Alpha'],shader.inputs['Alpha'])
output=folder/'oguri-source.glb'
result=bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',use_selection=True,export_animations=False,export_skins=True,export_morph=False,export_apply=False)
assert result=={'FINISHED'} and output.stat().st_size>10000
assert output.read_bytes()[:4]==b'glTF'
bpy.ops.wm.read_factory_settings(use_empty=True)
assert bpy.ops.import_scene.gltf(filepath=str(output))=={'FINISHED'}
meshes=[obj for obj in bpy.data.objects if obj.type=='MESH'];rigs=[obj for obj in bpy.data.objects if obj.type=='ARMATURE']
print('REIMPORT OBJECTS',[(o.name,len(o.data.vertices),[(m.type,m.object.name if m.type=='ARMATURE' and m.object else None) for m in o.modifiers],o.hide_render) for o in meshes],flush=True)
assert meshes and rigs
helpers={bone.custom_shape for rig in rigs for bone in rig.pose.bones if bone.custom_shape}
excluded=[obj for obj in meshes if not any(mod.type=='ARMATURE' for mod in obj.modifiers)]
assert all(obj in helpers for obj in excluded),'Unskinned mesh is not a verified bone display helper'
helper_report=[{'name':obj.name,'vertices':len(obj.data.vertices)} for obj in excluded]
meshes=[obj for obj in meshes if obj not in excluded]
assert meshes
weighted=sum(bool(vertex.groups) for obj in meshes for vertex in obj.data.vertices)
vertices=sum(len(obj.data.vertices) for obj in meshes);print('WEIGHT AUDIT',weighted,vertices,flush=True)
assert any(obj.data.uv_layers for obj in meshes) and bpy.data.images
report={'source_scene_sha256':before,'exchange_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bytes':output.stat().st_size,'excluded_bone_display_helpers':helper_report,'reimport_meshes':len(meshes),'reimport_vertices':vertices,'weighted_vertices':weighted,'unweighted_vertices':vertices-weighted,'weight_roundtrip_passed':weighted==vertices,'rigs':len(rigs),'bones':sum(len(obj.data.bones) for obj in rigs),'images':len(bpy.data.images),'scope':'Exchange model with skins, no morphs, physics or animation; material translation requires visual review; not runtime-ready'}
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(folder/'exchange-roundtrip.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));assert weighted==vertices,'Exchange lost vertex weights; do not use for runtime'
