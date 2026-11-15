"""Prepare compact native geometry with sampled motion bounds; do not install it."""
import hashlib
import json
import struct
import subprocess
import numpy as np
from inspect_assets import ROOT,chunks,flatten,data_path
from extract_assets import geometry,payload
from plan_hidden_compaction import SOURCE_HASH,verify_compaction,reviewed_source
from animate_kitasan import Rig


def motion_bounds():
    rig=Rig();minimum=rig.records[:,:3].min(0).astype(float);maximum=rig.records[:,:3].max(0).astype(float)
    for name in ('idle','run'):
        with np.load(ROOT/f'modding/animation-offline-v2/{name}.npz',allow_pickle=False) as clip:
            for rotation,offset in zip(clip['rotations'],clip['offsets']):
                positions,_=rig.skin(rotation,offset);minimum=np.minimum(minimum,positions.min(0));maximum=np.maximum(maximum,positions.max(0))
    return minimum-.15,maximum+.15


def with_motion_bounds(data,minimum,maximum):
    result=bytearray(data);nodes={n['offset']:n for n in flatten(chunks(data))};fields=[]
    meshes=geometry(data,'_KIT00_BODY_')
    if {m['name'] for m in meshes}!={f'COROLLA_KIT00_BODY_{x}' for x in 'ABCD'}:raise ValueError('Unexpected bodies')
    for mesh in meshes:
        solid=nodes[mesh['solid_offset']];leaves={n['id']:n for n in flatten(solid['children'])}
        header=leaves['0x00134011'];ranges=leaves['0x00134b02'];lead=len(payload(data,ranges))%60
        for node,begin in ((header,32),(ranges,lead)):
            for delta,values in ((0,minimum),(16,maximum)):
                for axis,value in enumerate(values):
                    at=node['payload']+begin+delta+axis*4;new=struct.pack('<f',value)
                    fields.append({'part':mesh['name'],'chunk':node['id'],'offset':at,'before':data[at:at+4].hex(),'after':new.hex()});result[at:at+4]=new
    if chunks(result)!=chunks(data):raise ValueError('Bounds changed container layout')
    return bytes(result),fields


def main():
    source_path=reviewed_source();source=source_path.read_bytes()
    if hashlib.sha256(source).hexdigest()!=SOURCE_HASH:raise ValueError('Source differs from reviewed prototype')
    completed=subprocess.run([str(ROOT/'modding/runtime/compact-hidden-dry-run'),str(source_path.relative_to(ROOT))],cwd=ROOT,stdout=subprocess.PIPE,check=True,timeout=120)
    compact=completed.stdout;verify_compaction(source,compact)
    minimum,maximum=motion_bounds();candidate,fields=with_motion_bounds(compact,minimum,maximum);verified=verify_compaction(source,candidate)
    destination=ROOT/'modding/staged-runtime';destination.mkdir(exist_ok=True)
    output=destination/'GEOMETRY.BIN'
    with output.open('xb') as stream:stream.write(candidate)
    report={'source_sha256':SOURCE_HASH,'candidate_sha256':hashlib.sha256(candidate).hexdigest(),'bytes':len(candidate),'minimum':minimum.tolist(),'maximum':maximum.tolist(),'bounds_basis':'80 authored idle/run keyframes plus rest and 0.15m margin; not exhaustive runtime interpolation proof','fields':fields,'compaction':verified,'installed':False,'authorization':'User explicitly authorized all repairs after pipeline capture; executables/network remain excluded'}
    (destination/'geometry-plan.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('fields','compaction')}))

if __name__=='__main__':main()
