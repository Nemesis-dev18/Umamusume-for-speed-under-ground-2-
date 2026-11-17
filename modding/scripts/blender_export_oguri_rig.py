"""Export original PMX bone names from imported metadata, without editing the scene."""
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
folder=ROOT/'modding/blender-review/oguri';source=folder/'oguri-source.blend';digest=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
rigs=[obj for obj in bpy.data.objects if obj.type=='ARMATURE'];assert len(rigs)==1
rig=rigs[0];rows=[]
for bone in rig.data.bones:
    pose=rig.pose.bones[bone.name];name=pose.mmd_bone.name_j
    rows.append({'blender_name':bone.name,'pmx_name':name,'parent_blender':bone.parent.name if bone.parent else None,'head_blender':list(bone.head_local),'tail_blender':list(bone.tail_local)})
names={row['blender_name']:row for row in rows}
for row in rows:
    seen=set();parent=row['parent_blender']
    while parent is not None:
        assert parent in names and parent not in seen;seen.add(parent);parent=names[parent]['parent_blender']
    row['parent_pmx']=names[row['parent_blender']]['pmx_name'] if row['parent_blender'] else None
original=[row['pmx_name'] for row in rows if row['pmx_name']]
assert len(original)==len(set(original))
assert all(any(row['pmx_name']==name for row in rows) for name in ['左腕','右腕','左足','右足','頭'])
report={'scene_sha256':digest,'coordinate_space':'Blender armature-local coordinates; not converted to runtime axes','bones':rows,'scope':'Metadata only; generated helper bones may have empty PMX names'}
(folder/'original-rig-map.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
print('Exported',len(rows),'bones;',len(original),'original names; parent graph acyclic')
