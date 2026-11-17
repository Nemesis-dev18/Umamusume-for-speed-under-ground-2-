"""Distinguish missing iris geometry from material sampling in the review scene."""
import bpy
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];folder=ROOT/'modding/uma-steam/fleet/1032'
bpy.ops.wm.open_mainfile(filepath=str(folder/'review.blend'))
for material in bpy.data.materials:
    if material.name.endswith('_eye'):
        material.use_nodes=True;nodes=material.node_tree.nodes;nodes.clear();output=nodes.new('ShaderNodeOutputMaterial');emission=nodes.new('ShaderNodeEmission');emission.inputs['Color'].default_value=(1,0,0,1);material.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
scene=bpy.context.scene;camera=scene.camera;target=Vector((0,0,1.47));camera.location=target+Vector((0,-3,.05));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=.5
scene.cycles.samples=16;scene.render.resolution_x=600;scene.render.resolution_y=600;scene.render.filepath=str(folder/'eye-geometry-diagnostic.png');bpy.ops.render.render(write_still=True)
