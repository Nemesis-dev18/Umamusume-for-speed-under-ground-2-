"""Compute accurate character submesh bounds in memory; never write game data."""
import hashlib
import math
import struct
from inspect_assets import chunks, data_path, flatten, save_json
from extract_assets import geometry,payload


def bounds_preview(data):
    meshes=geometry(data,'_KIT00_BODY_')
    targets={f'COROLLA_KIT00_BODY_{lod}'for lod in 'ABCD'}
    if {m['name'] for m in meshes}!=targets:raise ValueError('Unexpected character body set')
    nodes={n['offset']:n for n in flatten(chunks(data))}
    result=bytearray(data);changes=[]
    for mesh in meshes:
        solid=nodes[mesh['solid_offset']]
        ranges=next(n for n in flatten(solid['children']) if n['id']=='0x00134b02')
        raw=payload(data,ranges);lead=len(raw)%60
        if struct.unpack_from('<II',raw,lead+48)[1]!=0 or struct.unpack_from('<I',raw,lead+12)[0]!=len(mesh['indices']):
            raise ValueError('Expected first range to cover the entire character')
        referenced=[mesh['positions'][i] for i in set(mesh['indices'])]
        old_min=struct.unpack_from('<3f',raw,lead);old_max=struct.unpack_from('<3f',raw,lead+16)
        if all(old_min[k]<=p[k]<=old_max[k] for p in referenced for k in range(3)):
            raise ValueError('Bounds already contain the character')
        fields=[]
        for at,lower in ((0,True),(16,False)):
            for axis in range(3):
                value=(min if lower else max)(p[axis] for p in referenced)+(-0.01 if lower else 0.01)
                if not math.isfinite(value):raise ValueError('Invalid character bounds')
                offset=ranges['payload']+lead+at+axis*4
                old=data[offset:offset+4];new=struct.pack('<f',value)
                result[offset:offset+4]=new
                fields.append({'offset':offset,'offset_hex':hex(offset),'old_hex':old.hex(' '),'new_hex':new.hex(' '),'new_value':struct.unpack('<f',new)[0]})
        changes.append({'part':mesh['name'],'old_min':old_min,'old_max':old_max,'fields':fields})
    if len(result)!=len(data) or chunks(data)!=chunks(result):raise ValueError('Unexpected structural change')
    return bytes(result),changes


def main():
    relative='CARS/COROLLA/GEOMETRY.BIN';data=data_path(relative).read_bytes();result,changes=bounds_preview(data)
    count=sum(a!=b for a,b in zip(data,result))
    plan={'source':relative,'source_sha256':hashlib.sha256(data).hexdigest(),'result_sha256':hashlib.sha256(result).hexdigest(),
          'bytes_before':len(data),'bytes_after':len(result),'field_bytes':96,'changed_bytes':count,'changes':changes,
          'backup':relative+'.before-bounds.bak','temporary':relative+'.uma-bounds.tmp','approval_required':True,
          'purpose':'Repair first material range AABBs that do not contain the actual character geometry',
          'limits':'Does not prove race visibility, alter pose, animate the character, remove wheels, or change materials'}
    save_json('bounds-repair-plan.json',plan)
    print(f'IN MEMORY: 24 float fields, {count} changed bytes; size unchanged {len(data)}')
    for change in changes:print(change['part'],'old bounds',change['old_min'],change['old_max'],'field offsets',[f['offset_hex'] for f in change['fields']])

if __name__=='__main__':main()
