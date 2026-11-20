"""Review and round-trip one native source without changing its geometry or rig."""
import bpy,hashlib,json,math
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
folder=ROOT/'modding/uma-steam/fleet/1052';out=ROOT/'modding/diagnostics/model-quality/haru';out.mkdir(parents=True,exist_ok=True)
source=folder/'review-eyes.gltf';bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source))
scene=bpy.context.scene;scene.frame_set(0);meshes=[o for o in scene.objects if o.type=='MESH'];rigs=[o for o in scene.objects if o.type=='ARMATURE'];assert meshes and rigs
before={o.name:(len(o.data.vertices),len(o.data.polygons),tuple(v.name for v in o.vertex_groups)) for o in meshes}
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'backend':'Blender CLI '+bpy.app.version_string,'scope':'Native source review; not NFS rendering or installed upgrade','mesh_count':len(meshes),'armatures':len(rigs),'vertices':sum(v[0] for v in before.values()),'materials':[], 'gameplay_verified':False}
for mat in bpy.data.materials:
 if mat.use_nodes:
  bsdf=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
  if bsdf:
   bsdf.inputs['Metallic'].default_value=0;bsdf.inputs['Roughness'].default_value=.65
  report['materials'].append({'name':mat.name,'images':[n.image.name for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]})
graph=bpy.context.evaluated_depsgraph_get();points=[o.matrix_world@Vector(p) for o in meshes for p in o.evaluated_get(graph).bound_box];low=Vector(tuple(min(p[i] for p in points) for i in range(3)));high=Vector(tuple(max(p[i] for p in points) for i in range(3)));center=(low+high)*.5;height=high.z-low.z;assert .8<height<2.5
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.render.resolution_x=480;scene.render.resolution_y=640;scene.render.resolution_percentage=100;scene.view_settings.view_transform='Standard';scene.view_settings.exposure=-1;scene.render.film_transparent=True
scene.world=bpy.data.worlds.new('Quality review world');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
for name,direction,power in [('Key',(-2,-3,3),350),('Fill',(2,-2,1),140),('Rim',(1,2,2),220)]:
 data=bpy.data.lights.new('LGT-'+name,'AREA');data.energy=power;data.size=3;obj=bpy.data.objects.new('LGT-'+name,data);scene.collection.objects.link(obj);obj.location=center+Vector(direction);obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Quality camera');camera=bpy.data.objects.new('Quality camera',data);scene.collection.objects.link(camera);data.type='ORTHO';data.ortho_scale=height*1.22;scene.camera=camera
renders=[]
for label,direction in [('front',(0,-2,.1)),('rear',(0,2,.1))]:
 camera.location=center+Vector(direction)*height;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/(label+'.png'));bpy.ops.render.render(write_still=True)
 if label=='front':
  image=bpy.data.images.load(scene.render.filepath,check_existing=False);pixels=np.array(image.pixels[:]).reshape(image.size[1],image.size[0],4);yy,xx=np.where(pixels[:,:,3]>.5);assert len(xx)>1000
  base=world_to_camera_view(scene,camera,center);right=camera.rotation_euler.to_quaternion()@Vector((1,0,0));up=camera.rotation_euler.to_quaternion()@Vector((0,1,0));px=world_to_camera_view(scene,camera,center+right).x-base.x;py=world_to_camera_view(scene,camera,center+up).y-base.y
  delta=right*((float(xx.min()+xx.max())*.5/image.size[0]-.5)/px)+up*((float(yy.min()+yy.max())*.5/image.size[1]-.5)/py);center+=delta;camera.location+=delta;data.ortho_scale*=max((int(xx.max())-int(xx.min()))/(image.size[0]*.8),(int(yy.max())-int(yy.min()))/(image.size[1]*.8));bpy.data.images.remove(image);bpy.ops.render.render(write_still=True)
 renders.append(label+'.png')
action=bpy.data.actions.get('run')
if action:
 for obj in rigs:
  if not obj.animation_data:obj.animation_data_create()
  for track in obj.animation_data.nla_tracks:track.mute=True
  obj.animation_data.action=action
  if action.slots:obj.animation_data.action_slot=action.slots[0]
 camera.location=center+Vector((1,-2,.1))*height;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
 for i,phase in enumerate((0,.25,.5,.75)):
  frame=float(action.frame_range[0])+(float(action.frame_range[1])-float(action.frame_range[0]))*phase;scene.frame_set(int(frame),subframe=frame-int(frame));scene.render.filepath=str(out/f'run-{i}.png');bpy.ops.render.render(write_still=True);renders.append(f'run-{i}.png')
assert before=={o.name:(len(o.data.vertices),len(o.data.polygons),tuple(v.name for v in o.vertex_groups)) for o in meshes}
report.update(renders=renders,geometry_and_groups_unchanged=True,visual_approved=False,export_accepted=False)
bpy.ops.object.select_all(action='DESELECT')
for obj in [*meshes,*rigs]:obj.select_set(True)
export=out/'haru-quality-review.glb'
bpy.ops.export_scene.gltf(filepath=str(export),export_format='GLB',use_selection=True,export_materials='EXPORT',export_animations=True,export_skins=True,export_normals=True,export_yup=True)
report['review_export']={'path':str(export.relative_to(ROOT)),'bytes':export.stat().st_size,'sha256':hashlib.sha256(export.read_bytes()).hexdigest(),'size_gate_15MiB':export.stat().st_size<=15*1024*1024,'final_game_asset':False}
(out/'review.json').write_text(json.dumps(report,indent=2)+'\n');bpy.ops.wm.save_as_mainfile(filepath=str(out/'haru-quality-review.blend'))
print('PASS source geometry and skin groups preserved; review frames generated, visual acceptance pending',flush=True)
