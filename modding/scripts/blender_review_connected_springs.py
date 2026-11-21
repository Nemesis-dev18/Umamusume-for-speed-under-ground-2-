"""Compare actual runtime cape snapshots in a labelled contact sheet; not game rendering."""
import bpy,json,struct,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
assert '--' in sys.argv;ident=int(sys.argv[sys.argv.index('--')+1]);assert ident in (1062,1067)
folder=ROOT/f'modding/diagnostics/native-connected-springs/{ident}';model=(ROOT/f'modding/runtime/fleet/{ident}/model.umab').read_bytes();nv,ni,nb=struct.unpack_from('<3I',model,8)
indices=struct.unpack_from('<'+'H'*ni,model,40+nv*60+nb*16);triangles=[indices[i:i+3] for i in range(0,ni,3) if len(set(indices[i:i+3]))==3]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16
scene.render.resolution_x=1200;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.view_settings.view_transform='Standard'
scene.world=bpy.data.worlds.new('Review world');scene.world.color=(.2,.2,.2)
material=bpy.data.materials.new('Active native atlas');material.use_nodes=True;shader=material.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.8
texture=material.node_tree.nodes.new('ShaderNodeTexImage');texture.image=bpy.data.images.load(str(ROOT/f'modding/runtime/fleet/{ident}/atlas.dds'));material.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color']);material.node_tree.links.new(texture.outputs['Alpha'],shader.inputs['Alpha'])
for row,variant in enumerate(('baseline','linked')):
 for column,tag in enumerate(('frame-030','frame-090','frame-150')):
  data=(folder/variant/(tag+'.umap')).read_bytes();assert struct.unpack_from('<4s2I',data)==(b'UMAP',1,nv) and len(data)==12+nv*36
  values=[struct.unpack_from('<6f',data,12+36*v) for v in range(nv)]
  mesh=bpy.data.meshes.new(f'{variant}-{tag}');mesh.from_pydata([v[:3] for v in values],[],triangles);mesh.update();assert not mesh.validate()
  obj=bpy.data.objects.new('GEO-'+variant+'-'+tag,mesh);scene.collection.objects.link(obj);obj.location=(0,(column-1)*1.2,(1-row)*1.9)
  uv=mesh.uv_layers.new(name='Native UV')
  for loop in mesh.loops:
   u,v=struct.unpack_from('<2f',model,40+36*loop.vertex_index+28);uv.data[loop.index].uv=(u,1-v)
  for polygon in mesh.polygons:polygon.use_smooth=True
  mesh.normals_split_custom_set_from_vertices([v[3:6] for v in values]);mesh.materials.append(material)
  text=bpy.data.curves.new('Caption','FONT');text.body=f'{variant} {tag[6:]}';text.size=.105;text.align_x='CENTER'
  label=bpy.data.objects.new('Caption',text);scene.collection.objects.link(label);label.location=(-.55,obj.location.y,obj.location.z-.14);label.rotation_euler=Vector((-1,0,0)).to_track_quat('Z','Y').to_euler()
for name,location,power,size in [('Key',(-4,-3,6),650,5),('Fill',(-3,4,3),400,4)]:
 light=bpy.data.lights.new(name,'AREA');light.energy=power;light.size=size;obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);obj.location=location;obj.rotation_euler=(Vector((0,0,1.8))-obj.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('Rear comparison');obj=bpy.data.objects.new('Rear comparison',camera);scene.collection.objects.link(obj);obj.location=(-7,0,1.8);obj.rotation_euler=(Vector((0,0,1.75))-obj.location).to_track_quat('-Z','Y').to_euler();camera.type='ORTHO';camera.ortho_scale=4.9;scene.camera=obj
scene.render.filepath=str(folder/'rear-contact-sheet.png');bpy.ops.render.render(write_still=True)
(folder/'render-review.json').write_text(json.dumps({'scope':'Local Cycles contact sheet of actual C runtime pose samples; not in-game lighting, continuous animation, clipping or FPS acceptance.','character_id':ident,'frames':[30,90,150],'rows':['baseline','linked'],'visual_approved':False,'gameplay_verified':False},indent=2)+'\n')
