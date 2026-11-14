"""Route the full character through the existing CARSKIN range, not the doorline overlay."""
import hashlib
import struct
from inspect_assets import chunks,flatten
from extract_assets import geometry,payload

CARSKIN=0xd6d6080a

def route_body(data,minimum,maximum):
    meshes=geometry(data,'_KIT00_BODY_');nodes={n['offset']:n for n in flatten(chunks(data))};result=bytearray(data);changes=[]
    if {m['name'] for m in meshes}!={f'COROLLA_KIT00_BODY_{x}' for x in 'ABCD'}:raise ValueError('Unexpected body set')
    for mesh in meshes:
        solid=nodes[mesh['solid_offset']];leaves={n['id']:n for n in flatten(solid['children'])}
        node=leaves['0x00134b02'];ranges=payload(data,node);lead=len(ranges)%60;shaders=payload(data,leaves['0x00134013']);count=len(ranges)//60
        target=[]
        for i in range(count):
            shader=struct.unpack_from('<I',ranges,lead+i*60+32)[0]
            if shader*8+4>len(shaders):raise ValueError('Shader index out of range')
            if struct.unpack_from('<I',shaders,shader*8)[0]==CARSKIN:target.append(i)
        if len(target)!=1:raise ValueError('Expected exactly one native CARSKIN range')
        chosen=target[0]
        if struct.unpack_from('<I',ranges,lead+chosen*60+12)[0]:raise ValueError('CARSKIN range already active')
        for i in range(count):
            values={12:struct.pack('<I',len(mesh['indices']) if i==chosen else 0),52:struct.pack('<I',0 if i<=chosen else len(mesh['indices']))}
            if i==chosen:
                for base,vector in ((0,minimum),(16,maximum)):
                    for axis,value in enumerate(vector):values[base+axis*4]=struct.pack('<f',value)
            for offset,new in values.items():
                at=node['payload']+lead+i*60+offset;old=data[at:at+4]
                if old!=new:result[at:at+4]=new;changes.append({'part':mesh['name'],'range':i,'offset':at,'before':old.hex(),'after':new.hex()})
    result=bytes(result)
    if chunks(result)!=chunks(data):raise ValueError('Unexpected container change')
    after={m['asset_hash']:m for m in geometry(result,'_KIT00_BODY_')}
    for mesh in meshes:
        new=after[mesh['asset_hash']]
        for key in ('positions','normals','uv','indices','markers','transform'):
            if mesh[key]!=new[key]:raise ValueError('Material routing changed geometry')
    return result,changes
