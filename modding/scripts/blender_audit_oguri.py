"""Read the source review scene and report export constraints without changing it."""
from pathlib import Path
import json
import math
import bpy

ROOT=Path(__file__).resolve().parents[2]
folder=ROOT/'modding/blender-review/oguri'
bpy.ops.wm.open_mainfile(filepath=str(folder/'oguri-source.blend'))
meshes=[o for o in bpy.data.objects if o.type=='MESH'];rigs=[o for o in bpy.data.objects if o.type=='ARMATURE'];assert len(rigs)==1 and meshes
bone_names={b.name for b in rigs[0].data.bones};rows=[]
for obj in meshes:
    missing=too_many=0;minimum=math.inf;maximum=0;uv_outside=0
    groups={g.index:g.name for g in obj.vertex_groups}
    for vertex in obj.data.vertices:
        weights=[g.weight for g in vertex.groups if groups.get(g.group) in bone_names and g.weight>1e-6]
        if not weights:missing+=1
        if len(weights)>4:too_many+=1
        total=sum(weights);minimum=min(minimum,total);maximum=max(maximum,total)
    uv=obj.data.uv_layers.active
    if uv:
        for loop in uv.data:
            assert all(math.isfinite(x) for x in loop.uv)
            if any(x<0 or x>1 for x in loop.uv):uv_outside+=1
    materials=[]
    for index,slot in enumerate(obj.material_slots):
        polygons=[p for p in obj.data.polygons if p.material_index==index]
        materials.append({'name':slot.name,'triangles':sum(len(p.vertices)-2 for p in polygons)})
    rows.append({'object':obj.name,'vertices':len(obj.data.vertices),'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),'unweighted_vertices':missing,'more_than_four_influences':too_many,'weight_sum_range':[minimum,maximum],'uv_present':uv is not None,'uv_loops_outside_unit':uv_outside,'materials':materials})
assert sum(r['vertices'] for r in rows)==34537
report={'scope':'Read-only Blender source audit; no optimization or export applied','bones':len(bone_names),'meshes':rows,'images':[{'name':i.name,'size':list(i.size)} for i in bpy.data.images]}
(folder/'export-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps([{k:v for k,v in r.items() if k!='materials'} for r in rows]))
