"""Measure a temporary lower-detail Oguri mesh; never overwrite the source scene."""
from pathlib import Path
import hashlib
import json
import math
import bpy

ROOT=Path(__file__).resolve().parents[2]
folder=ROOT/'modding/blender-review/oguri';source=folder/'oguri-source.blend';before=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
objects=[obj for obj in bpy.data.objects if obj.type=='MESH'];assert len(objects)==1
original=objects[0];copy=original.copy();copy.data=original.data.copy();bpy.context.collection.objects.link(copy)
copy.name='Oguri LOD measurement'
# Measure rest topology, without evaluating pose, outline shells or physics modifiers.
copy.modifiers.clear();copy.shape_key_clear()
modifier=copy.modifiers.new('Temporary triangle budget','DECIMATE');modifier.ratio=.4;modifier.use_collapse_triangulate=True
evaluated=copy.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
try:
    mesh.calc_loop_triangles();triangles=len(mesh.loop_triangles)
    assert 0<triangles<53024 and len(mesh.vertices)<65536 and mesh.uv_layers.active
    bone_names={b.name for obj in bpy.data.objects if obj.type=='ARMATURE' for b in obj.data.bones}
    groups={g.index:g.name for g in copy.vertex_groups};unweighted=excess=0;totals=[]
    for vertex in mesh.vertices:
        assert all(math.isfinite(x) for x in vertex.co)
        weights=[g.weight for g in vertex.groups if groups.get(g.group) in bone_names and g.weight>1e-6]
        unweighted+=not weights;excess+=len(weights)>4;totals.append(sum(weights))
    report={'source_sha256':before,'ratio':.4,'vertices':len(mesh.vertices),'triangles':triangles,'uv_layers':len(mesh.uv_layers),'materials':len(mesh.materials),'unweighted_vertices':unweighted,'vertices_over_four_weights':excess,'weight_sum_range':[min(totals),max(totals)],'scope':'Measurement only: no mesh export, rig retarget, silhouette or deformation approval'}
    (folder/'lod-measurement.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
finally:evaluated.to_mesh_clear()
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
