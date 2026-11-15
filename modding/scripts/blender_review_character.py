"""Build an independent Blender review scene from the verified runtime rest mesh."""
from pathlib import Path
import hashlib
import json
import math
import struct
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'modding/runtime/kitasan.umab';data=source.read_bytes()
magic,version,vertices,indices,bones,idle,run,reserved=struct.unpack_from('<4s7I',data)
assert magic==b'UMAB' and version==2 and vertices==14512 and indices%3==0 and bones==282 and not reserved
rows=[struct.unpack_from('<6f4B2f',data,32+i*36) for i in range(vertices)]
assert all(math.isfinite(value) for row in rows for value in row)
start=32+vertices*60+bones*16;faces=struct.unpack_from(f'<{indices}H',data,start)
assert max(faces)<vertices
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mesh=bpy.data.meshes.new('Runtime rest mesh');mesh.from_pydata([r[:3] for r in rows],[],[faces[i:i+3] for i in range(0,indices,3)]);mesh.update()
assert not mesh.validate() and len(mesh.vertices)==vertices and len(mesh.polygons)==indices//3
obj=bpy.data.objects.new('Kitasan — runtime source review',mesh);bpy.context.collection.objects.link(obj)
uv=mesh.uv_layers.new(name='Runtime UV')
for loop in mesh.loops:uv.data[loop.index].uv=(rows[loop.vertex_index][-2],1-rows[loop.vertex_index][-1])
for polygon in mesh.polygons:polygon.use_smooth=True
mesh.normals_split_custom_set_from_vertices([r[3:6] for r in rows])
material=bpy.data.materials.new('Original atlas review');material.use_nodes=True
shader=material.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.8
texture=material.node_tree.nodes.new('ShaderNodeTexImage');texture.image=bpy.data.images.load(str(ROOT/'modding/character-source/atlas.png'));texture.image.pack()
material.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color']);material.node_tree.links.new(texture.outputs['Alpha'],shader.inputs['Alpha']);obj.data.materials.append(material)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8
scene.world.color=(.3,.3,.3)
for name,location,power,size in [('Key',(3,-4,5),500,4),('Fill',(-2,3,3),300,3)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
    actor=bpy.data.objects.new(name,light);scene.collection.objects.link(actor);actor.location=location;actor.rotation_euler=(Vector((0,0,1))-actor.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('Review camera');actor=bpy.data.objects.new('Review camera',camera);scene.collection.objects.link(actor);actor.location=(4,-6,2.7);actor.rotation_euler=(Vector((0,0,1))-actor.location).to_track_quat('-Z','Y').to_euler();camera.type='ORTHO';camera.ortho_scale=2.5;scene.camera=actor
scene.render.resolution_x=480;scene.render.resolution_y=640;scene.render.resolution_percentage=100
out=ROOT/'modding/blender-review';out.mkdir(exist_ok=True)
scene.render.filepath=str(out/'kitasan-rest.png');bpy.ops.wm.save_as_mainfile(filepath=str(out/'kitasan-rest.blend'));bpy.ops.render.render(write_still=True)
(out/'manifest.json').write_text(json.dumps({'runtime_sha256':hashlib.sha256(data).hexdigest(),'vertices':vertices,'triangles':indices//3,'scope':'Rest-mesh review only; no animation, rig or game installation changed','blender_version':bpy.app.version_string},indent=2)+'\n')
