"""Distinguish missing iris geometry from material sampling in the review scene."""
import bpy
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];folder=ROOT/'modding/uma-steam/fleet/1032'
bpy.ops.wm.open_mainfile(filepath=str(folder/'review.blend'))
for material in bpy.data.materials:
    if material.name.endswith('_eye'):
        material.use_nodes=True;nodes=material.node_tree.nodes;nodes.clear();output=nodes.new('ShaderNodeOutputMaterial');emission=nodes.new('ShaderNodeEmission');emission.inputs['Color'].default_value=(1,0,0,1);material.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
for material in bpy.data.materials:
    if material.name.endswith('_face') and material.use_nodes:
        tree=material.node_tree;output=next(n for n in tree.nodes if n.type=='OUTPUT_MATERIAL');original=output.inputs['Surface'].links[0].from_socket
        geometry=tree.nodes.new('ShaderNodeNewGeometry');mix=tree.nodes.new('ShaderNodeMixShader');transparent=tree.nodes.new('ShaderNodeBsdfTransparent')
        tree.links.new(geometry.outputs['Backfacing'],mix.inputs[0]);tree.links.new(original,mix.inputs[1]);tree.links.new(transparent.outputs[0],mix.inputs[2]);tree.links.new(mix.outputs[0],output.inputs['Surface'])
scene=bpy.context.scene;camera=scene.camera;target=Vector((0,0,1.47));camera.location=target+Vector((0,-3,.05));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=.5
scene.cycles.samples=16;scene.render.resolution_x=600;scene.render.resolution_y=600;scene.render.filepath=str(folder/'eye-culling-diagnostic.png');bpy.ops.render.render(write_still=True)
