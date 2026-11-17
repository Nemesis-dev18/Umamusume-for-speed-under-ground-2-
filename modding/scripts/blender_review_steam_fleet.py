"""Import original Steam review glTFs and render one reference view per character."""
import bpy,json,math,hashlib,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];fleet=json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())
baked='--baked-eyes' in sys.argv
for character in fleet['characters']:
    folder=ROOT/'modding/uma-steam/fleet'/str(character['id']);input_path=folder/('review-eyes.gltf' if baked else 'source.gltf');prefix='review-eyes' if baked else 'review';bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(input_path))
    scene=bpy.context.scene;scene.frame_set(0);scene.render.engine='CYCLES';scene.cycles.samples=24;scene.render.resolution_x=640;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('Review world');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.12,.14,.18,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
    scene.view_settings.view_transform='Standard';scene.render.film_transparent=True
    helpers={bone.custom_shape for obj in scene.objects if obj.type=='ARMATURE' for bone in obj.pose.bones if bone.custom_shape}
    points=[];graph=bpy.context.evaluated_depsgraph_get()
    for obj in scene.objects:
        if obj.type=='MESH' and obj not in helpers:
            evaluated=obj.evaluated_get(graph);points.extend(obj.matrix_world@Vector(p) for p in evaluated.bound_box)
    if not points:raise ValueError('No visible character mesh')
    low=Vector(tuple(min(p[i] for p in points) for i in range(3)));high=Vector(tuple(max(p[i] for p in points) for i in range(3)));center=(low+high)/2;height=high.z-low.z
    if not .8<height<2.5:raise ValueError('Unexpected assembled character height')
    bpy.ops.object.camera_add(location=center+Vector((height*.15,-height*2,height*.15)));camera=bpy.context.object;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=height*1.2;scene.camera=camera
    for name,offset,power,size in [('Key',(-2,-3,4),350,3),('Fill',(2,-2,2),180,3),('Rim',(0,2,3),250,2)]:
        bpy.ops.object.light_add(type='AREA',location=center+Vector(offset));lamp=bpy.context.object;lamp.name=name;lamp.data.energy=power;lamp.data.shape='DISK';lamp.data.size=size;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
    if not baked:bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(folder/'review.blend'))
    scene.render.filepath=str(folder/(prefix+'.png'));bpy.ops.render.render(write_still=True)
    report={'name':character['name'],'bounds_min':list(low),'bounds_max':list(high),'height':height,'mesh_count':sum(o.type=='MESH' and o not in helpers for o in scene.objects),'armatures':sum(o.type=='ARMATURE' for o in scene.objects),'rendered':True,'visual_approved':False,'game_integrated':False}
    report['gltf_sha256']=hashlib.sha256(input_path.read_bytes()).hexdigest();report['buffer_sha256']=hashlib.sha256((folder/'source.bin').read_bytes()).hexdigest()
    for obj in scene.objects:
        if obj.type=='ARMATURE' and obj.animation_data:
            for track in obj.animation_data.nla_tracks:track.mute=True
            action=bpy.data.actions.get('run')
            if action:
                obj.animation_data.action=action
                if action.slots:obj.animation_data.action_slot=action.slots[0]
    frame=float(bpy.data.actions['run'].frame_range[1])*.25;scene.frame_set(int(frame),subframe=frame-int(frame));scene.render.filepath=str(folder/(prefix+'-run.png'));bpy.ops.render.render(write_still=True)
    report['native_idle_and_run_rendered']=True;report['eye_depth_material_pending']=not baked
    (folder/('blender-eyes-review.json' if baked else 'blender-review.json')).write_text(json.dumps(report,indent=2)+'\n');print('REVIEW_RENDERED',character['name'],flush=True)
