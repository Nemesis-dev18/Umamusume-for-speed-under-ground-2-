"""Inspect imported native clips and verify visible deformation before game packaging."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];folder=ROOT/'modding/uma-steam/fleet/1052'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(folder/'source.gltf'))
for obj in bpy.context.scene.objects:
    if obj.type=='ARMATURE':
        print('NATIVE_ARMATURE',obj.name,len(obj.data.bones),flush=True)
        if obj.animation_data:
            print('ACTION',obj.animation_data.action.name if obj.animation_data.action else None,'TRACKS',[(t.name,[(s.name,s.action.name) for s in t.strips]) for t in obj.animation_data.nla_tracks],flush=True)
print('ACTIONS',[(a.name,list(a.frame_range)) for a in bpy.data.actions],flush=True)
