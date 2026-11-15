"""Render the imported source scene for visual review, without changing the source rig."""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
folder=ROOT/'modding/blender-review/oguri'
bpy.ops.wm.open_mainfile(filepath=str(folder/'oguri-source.blend'))
points=[o.matrix_world@Vector(point) for o in bpy.data.objects if o.type=='MESH' for point in o.bound_box]
assert points
low=Vector(tuple(min(p[i] for p in points) for i in range(3)));high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
center=(low+high)*.5;height=high.z-low.z;assert height>0
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8
scene.world.color=(.3,.3,.3)
for name,direction,power in [('Review key',(2,-3,3),500),('Review fill',(-2,2,2),300)]:
    lamp=bpy.data.lights.new(name,'AREA');lamp.energy=power;lamp.shape='DISK';lamp.size=height*2
    obj=bpy.data.objects.new(name,lamp);scene.collection.objects.link(obj);obj.location=center+Vector(direction)*height
    obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('Review camera');obj=bpy.data.objects.new('Review camera',camera);scene.collection.objects.link(obj)
obj.location=center+Vector((2,-4,1))*height;obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
camera.type='ORTHO';camera.ortho_scale=max(height*1.25,(high.x-low.x)*1.5);scene.camera=obj
scene.render.resolution_x=480;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.render.filepath=str(folder/'oguri-review.png');bpy.ops.render.render(write_still=True)
