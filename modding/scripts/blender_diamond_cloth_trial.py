"""Offline Blender cloth experiment; writes only diagnostic snapshots/reports."""
import bpy
import json
import sys
import struct
import math
import time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'modding/diagnostics/triangle-contact-prototype'
sys.path.insert(0,str(HERE));sys.path.insert(0,str(Path(__file__).resolve().parent))
from mesh import physical_mesh
import blender_diamond_intersections as source
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def main():
    base=ROOT/'modding/diagnostics/blender-cloth-trial';no_self='--no-self' in sys.argv;no_body='--no-body' in sys.argv;out=base/('structural-only' if no_body else 'deduplicated-without-self' if no_self else 'deduplicated-full-contact');out.mkdir(parents=True,exist_ok=True)
    topo=json.loads((HERE/'diamond-topology-position-skin.json').read_text())
    roots,mapping,tris,edges,mass=physical_mesh(topo)
    adjacent=[[] for _ in roots]
    for a,b in edges:adjacent[a].append(b);adjacent[b].append(a)
    seen=set();keep=set();excluded=[]
    for v in range(len(roots)):
        if v in seen:continue
        stack=[v];seen.add(v);part=[]
        while stack:
            a=stack.pop();part.append(a)
            for b in adjacent[a]:
                if b not in seen:seen.add(b);stack.append(b)
        if min(mass[i] for i in part)<1:keep.update(part)
        else:excluded.extend(part)
    order=sorted(keep);remap={v:i for i,v in enumerate(order)}
    sim_tris=[tuple(remap[v] for v in tri) for tri in tris if tri[0] in keep]
    duplicate_faces=len(sim_tris)-len({tuple(sorted(tri)) for tri in sim_tris})
    sim_tris=list({tuple(sorted(tri)):tri for tri in sim_tris}.values())
    sim_roots=[roots[v] for v in order]
    assert len(sim_roots)>2000 and all(all(v in keep for v in tri) for tri in tris if tri[0] in keep)
    body=[]
    for group in source.meta['groups']:
        if not group['material'].startswith('mtl_bdy'):continue
        for t in range(group['first_index']//3,(group['first_index']+group['index_count'])//3):
            ids=source.triangles[t]
            if len(set(ids))==3 and max(source.weights[v] for v in ids)<=.05:body.append(ids)
    body_ids=sorted({v for tri in body for v in tri});body_map={v:i for i,v in enumerate(body_ids)}
    body_tris=[tuple(body_map[v] for v in tri) for tri in body]
    poses=[]
    for path in sorted((base/'run-source').glob('*.umap')):
        raw=path.read_bytes();assert struct.unpack_from('<4s2I',raw)==(b'UMAP',1,source.nv)
        poses.append(np.ndarray((source.nv,3),dtype='<f4',buffer=raw,offset=12,strides=(36,4)).copy())
    assert len(poses)==48
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    def object_mesh(name,vertices,faces):
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
        obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);return obj
    cloth=object_mesh('GEO-Diamond-cloth-trial',poses[0][sim_roots].tolist(),sim_tris)
    collider=object_mesh('GEO-Diamond-body-collision',poses[0][body_ids].tolist(),body_tris)
    for obj,ids in ((cloth,sim_roots),(collider,body_ids)):
        obj.shape_key_add(name='Basis')
        for i,pose in enumerate(poses):
            key=obj.shape_key_add(name=f'Run-{i:03d}');key.data.foreach_set('co',pose[ids].ravel())
    pins=cloth.vertex_groups.new(name='Native-attachments')
    for i,original in enumerate(order):
        weight=1-mass[original]
        if weight>0:pins.add([i],min(1,weight),'REPLACE')
    collider.modifiers.new('Native-body-surface','COLLISION')
    collider.collision.thickness_outer=.002;collider.collision.thickness_inner=.001
    modifier=cloth.modifiers.new('Garment-physics-trial','CLOTH')
    settings=modifier.settings;settings.quality=8;settings.mass=.15
    settings.tension_stiffness=15;settings.compression_stiffness=15;settings.shear_stiffness=5;settings.bending_stiffness=.2
    settings.air_damping=2;settings.vertex_group_mass=pins.name;settings.pin_stiffness=1
    contacts=modifier.collision_settings;contacts.use_collision=not no_body;contacts.distance_min=.002
    contacts.collision_quality=4;contacts.use_self_collision=not no_self;contacts.self_distance_min=.002
    scene=bpy.context.scene;scene.render.fps=80;scene.frame_start=1;scene.frame_end=96
    modifier.point_cache.frame_start=1;modifier.point_cache.frame_end=96
    def animate(scene):
        current=(scene.frame_current-1)%48
        for obj in (cloth,collider):
            for i,key in enumerate(obj.data.shape_keys.key_blocks[1:]):key.value=float(i==current)
    bpy.app.handlers.frame_change_pre.append(animate)
    rows=[];begin=time.monotonic();rejected=None
    for frame in range(1,97):
        scene.frame_set(frame);graph=bpy.context.evaluated_depsgraph_get();evaluated=cloth.evaluated_get(graph);mesh=evaluated.to_mesh()
        positions=np.empty((len(sim_roots),3),dtype=np.float32);mesh.vertices.foreach_get('co',positions.ravel());evaluated.to_mesh_clear()
        native=poses[(frame-1)%48][sim_roots]
        displacement=float(np.linalg.norm(positions-native,axis=1).max())
        assert np.isfinite(positions).all()
        if frame%8==0 or frame==1 or displacement>.3:
            worst=int(np.linalg.norm(positions-native,axis=1).argmax());row={'frame':frame,'maximum_displacement_m':displacement,'minimum_z':float(positions[:,2].min()),'worst_render_vertex':sim_roots[worst],'worst_pin_weight':1-mass[order[worst]],'worst_native_motion_from_initial_m':float(np.linalg.norm(native[worst]-poses[0][sim_roots[worst]])),'worst_simulated_motion_from_initial_m':float(np.linalg.norm(positions[worst]-poses[0][sim_roots[worst]]))};rows.append(row);print(json.dumps(row),flush=True)
            (out/f'trial-{frame:03d}.json').write_text(json.dumps(positions.tolist(),separators=(',',':'))+'\n')
        if displacement>.3:
            rejected='Offset from native reference exceeds 30cm; attachment/visual review required, not proof of solver divergence';break
    bpy.app.handlers.frame_change_pre.remove(animate)
    report={'scope':'Offline Blender cloth trial, not runtime implementation. Body selection includes rigid costume surfaces. Does not prove collision-free or visually accepted output.','simulation_particles':len(sim_roots),'duplicate_physical_faces_removed':duplicate_faces,'unattached_particles_retained_on_native_animation':len(excluded),'body_triangles':len(body),'elapsed_seconds':time.monotonic()-begin,'frames':rows,'rejected':rejected,'accepted_for_game':False}
    (out/'simulation-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
