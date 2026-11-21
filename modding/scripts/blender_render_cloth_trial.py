"""Render native versus offline cloth trial in the same view; diagnostic only."""
import bpy,json,struct,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'modding/diagnostics/triangle-contact-prototype';OUT=ROOT/'modding/diagnostics/blender-cloth-trial'
sys.path.insert(0,str(HERE));from mesh import physical_mesh
model=(ROOT/'modding/runtime/fleet/1067/model.umab').read_bytes();nv,ni,nb=struct.unpack_from('<3I',model,8)
raw=(OUT/'run-source/run-003.umap').read_bytes();rows=[struct.unpack_from('<6f4B2f',raw,12+v*36) for v in range(nv)]
index=struct.unpack_from('<'+'H'*ni,model,40+nv*60+nb*16);faces=[index[i:i+3] for i in range(0,ni,3)]
roots,mapping,tris,edges,mass=physical_mesh(json.loads((HERE/'diamond-topology-position-skin.json').read_text()))
adj=[[] for _ in roots]
for a,b in edges:adj[a].append(b);adj[b].append(a)
seen=set();keep=set()
for v in range(len(roots)):
 if v in seen:continue
 stack=[v];seen.add(v);part=[]
 while stack:
  a=stack.pop();part.append(a)
  for b in adj[a]:
   if b not in seen:seen.add(b);stack.append(b)
 if min(mass[i] for i in part)<1:keep.update(part)
order=sorted(keep);sim_index={v:i for i,v in enumerate(order)}
trial=json.loads((OUT/'structural-only/trial-004.json').read_text());assert len(trial)==len(order)
native=[r[:3] for r in rows];modified=list(native)
for render,particle in mapping.items():
 if particle in keep:modified[render]=trial[sim_index[particle]]
bpy.ops.wm.read_factory_settings(use_empty=True)
material=bpy.data.materials.new('Native atlas');material.use_nodes=True
shader=material.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.8
texture=material.node_tree.nodes.new('ShaderNodeTexImage');texture.image=bpy.data.images.load(str(ROOT/'modding/runtime/fleet/1067/atlas.dds'))
material.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color']);material.node_tree.links.new(texture.outputs['Alpha'],shader.inputs['Alpha'])
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.device='CPU'
scene.render.resolution_x=1000;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Diagnostic world');scene.world.color=(.18,.18,.18);scene.view_settings.view_transform='Standard'
for label,positions,y in (('Native',native,-.65),('Cloth trial',modified,.65)):
 mesh=bpy.data.meshes.new(label);mesh.from_pydata(positions,[],faces);mesh.update();obj=bpy.data.objects.new('GEO-'+label,mesh);scene.collection.objects.link(obj);obj.location.y=y
 uv=mesh.uv_layers.new(name='Native UV')
 for loop in mesh.loops:
  source=struct.unpack_from('<2f',model,40+loop.vertex_index*36+28);uv.data[loop.index].uv=(source[0],1-source[1])
 for polygon in mesh.polygons:polygon.use_smooth=True
 obj.data.materials.append(material)
for name,location,power,size in [('Key',(3,-3,4),450,4),('Fill',(2,3,2),250,3)]:
 light=bpy.data.lights.new(name,'AREA');light.energy=power;light.size=size;obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);obj.location=location;obj.rotation_euler=(Vector((0,0,1))-obj.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('Comparison');obj=bpy.data.objects.new('Comparison',camera);scene.collection.objects.link(obj);obj.location=(4,-.2,1.9);obj.rotation_euler=(Vector((0,0,.9))-obj.location).to_track_quat('-Z','Y').to_euler();camera.type='ORTHO';camera.ortho_scale=2.9;scene.camera=obj
scene.render.filepath=str(OUT/'native-vs-cloth-frame004.png');bpy.ops.render.render(write_still=True)
