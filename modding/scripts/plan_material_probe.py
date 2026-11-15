"""Prepare an isolated material probe in memory; never write game binaries."""
import hashlib
import re
import struct
from inspect_assets import chunks, data_path, flatten, save_json
from extract_assets import payload


def material_preview(data):
    out=bytearray(data);changes=[];targets={f'COROLLA_KIT00_BODY_{x}' for x in 'ABCD'}
    for solid in flatten(chunks(data)):
        if solid['id']!='0x80134010':continue
        leaves={n['id']:n for n in flatten(solid.get('children',[]))}
        if '0x00134011' not in leaves:continue
        header=payload(data,leaves['0x00134011']);names=re.findall(rb'[!-~]{4,}',header)
        name=max(names,key=len).decode() if names else ''
        if name not in targets:continue
        ranges=payload(data,leaves['0x00134b02']);lead=len(ranges)%60
        count=struct.unpack_from('<I',ranges,lead+12)[0]
        texture_slot=struct.unpack_from('<I',ranges,lead+28)[0]
        shader_slot=struct.unpack_from('<I',ranges,lead+32)[0]
        textures=payload(data,leaves['0x00134012']);shaders=payload(data,leaves['0x00134013'])
        if count!=49671 or texture_slot*8+4>len(textures) or shader_slot*8+4>len(shaders):raise ValueError('Unexpected character material layout')
        if struct.unpack_from('<I',textures,texture_slot*8)[0]!=0x1c9637a6:raise ValueError('Character atlas differs')
        if struct.unpack_from('<I',shaders,shader_slot*8)[0]!=0x02a05578:raise ValueError('Character material is no longer DECAL')
        offset=leaves['0x00134013']['payload']+shader_slot*8
        out[offset:offset+4]=struct.pack('<I',0x0fedee40)
        changes.append({'part':name,'offset':offset,'offset_hex':hex(offset),'length':4,
                        'old_hex':'78 55 a0 02','new_hex':'40 ee ed 0f',
                        'old_material':'DECAL','new_material':'DULLPLASTIC'})
    if {c['part'] for c in changes}!=targets or len(changes)!=4:raise ValueError('Expected four unique body targets')
    if sum(a!=b for a,b in zip(data,out))!=16 or len(data)!=len(out):raise ValueError('Expected exactly 16 changed bytes')
    if chunks(data)!=chunks(out):raise ValueError('Chunk structure changed')
    return bytes(out),changes


def main():
    relative='CARS/COROLLA/GEOMETRY.BIN';data=data_path(relative).read_bytes()
    out,changes=material_preview(data)
    plan={'source':relative,'source_sha256':hashlib.sha256(data).hexdigest(),'result_sha256':hashlib.sha256(out).hexdigest(),
          'bytes_before':len(data),'bytes_after':len(out),'changed_bytes':16,'changes':changes,
          'backup':relative+'.before-material.bak','temporary':relative+'.uma-material.tmp',
          'approval_required':True,'game_must_be_closed':True,'applied':False,
          'purpose':'Isolate whether the DECAL material causes race invisibility; DULLPLASTIC is present in GLOBALB.BUN',
          'limits':'No animation, pose, texture, wheel, bounding-box, or geometry change. Outcome requires a race test.'}
    save_json('material-probe-plan.json',plan)
    for c in changes:print(c['part'],c['offset_hex'],c['old_hex'],'->',c['new_hex'])
    print('IN MEMORY ONLY: four material references, 16 changed bytes; unchanged file size',len(data))

if __name__=='__main__':main()
