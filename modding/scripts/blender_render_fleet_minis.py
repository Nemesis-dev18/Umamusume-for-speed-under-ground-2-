"""Render native mini models for badge review, without touching game resources."""
import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
for character in json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters']:
    folder=ROOT/'modding/uma-steam/mini-fleet'/str(character['id']);bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(folder/'source.gltf'))
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.view_settings.view_transform='Standard'
    scene.world=bpy.data.worlds.new('Mini review');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7
    helpers={b.custom_shape for o in scene.objects if o.type=='ARMATURE' for b in o.pose.bones if b.custom_shape};points=[];graph=bpy.context.evaluated_depsgraph_get()
    for o in scene.objects:
        if o.type=='MESH' and o not in helpers:
            evaluated=o.evaluated_get(graph);points.extend(o.matrix_world@Vector(p) for p in evaluated.bound_box)
    if not points:raise ValueError('Missing mini geometry')
    low=Vector(tuple(min(p[i] for p in points) for i in range(3)));high=Vector(tuple(max(p[i] for p in points) for i in range(3)));center=(low+high)/2;size=max(high-low)
    if not .1<size<5:raise ValueError('Implausible mini bounds')
    bpy.ops.object.camera_add(location=center+Vector((size*.12,-size*3,size*.1)));camera=bpy.context.object;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=size*1.14;scene.camera=camera
    for offset,power in [((-2,-3,3),160),((2,-1,2),90)]:
        bpy.ops.object.light_add(type='AREA',location=center+Vector(offset));lamp=bpy.context.object;lamp.data.energy=power;lamp.data.size=3;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(folder/'badge-review.png');bpy.ops.render.render(write_still=True)
    report={'id':character['id'],'source_gltf_sha256':hashlib.sha256((folder/'source.gltf').read_bytes()).hexdigest(),'bounds_min':list(low),'bounds_max':list(high),'rendered':True,'visual_approved':False,'installed':False}
    (folder/'badge-review.json').write_text(json.dumps(report,indent=2)+'\n');print('MINI_RENDERED',character['name'],flush=True)
