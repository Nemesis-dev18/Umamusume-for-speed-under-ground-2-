"""Compute an eight-byte Corolla header repair in memory; never write game data."""
import hashlib
import re
import struct
from inspect_assets import chunks, data_path, flatten, save_json
from extract_assets import payload, skip_words


def repair_preview(data):
    corrected=bytearray(data);changes=[];names=set()
    for solid in flatten(chunks(data)):
        if solid['id']!='0x80134010':continue
        leaves={n['id']:n for n in flatten(solid.get('children',[]))}
        if '0x00134011' not in leaves:continue
        header=leaves['0x00134011'];raw=payload(data,header)
        text=re.findall(rb'[!-~]{4,}',raw)
        name=max(text,key=len).decode() if text else ''
        if name not in {f'COROLLA_KIT00_BODY_{lod}' for lod in 'ABCD'}:continue
        if name in names:raise ValueError('Duplicate target solid')
        names.add(name)
        if len(raw)!=192 or '0x00134900' not in leaves:raise ValueError('Unexpected header layout')
        mesh=payload(data,leaves['0x00134900']);lead=skip_words(mesh)
        triangles=struct.unpack_from('<I',mesh,lead+36)[0]
        vertices=struct.unpack_from('<I',mesh,lead+52)[0]
        before=struct.unpack_from('<I',raw,20)[0]
        if (triangles,vertices,before)!=(16557,14512,(14512<<16)|16557):
            raise ValueError(f'{name}: no longer matches reviewed corrupt-header signature')
        offset=header['payload']+20
        old=data[offset:offset+4];new=struct.pack('<I',triangles)
        corrected[offset:offset+4]=new
        changes.append({'part':name,'offset':offset,'offset_hex':hex(offset),'length':4,
                        'old_hex':old.hex(' '),'new_hex':new.hex(' '),
                        'old_u32':before,'new_u32':triangles})
    if len(names)!=4:raise ValueError('Expected four known Corolla body LODs')
    if len(corrected)!=len(data):raise ValueError('Unexpected size change')
    changed=sum(a!=b for a,b in zip(data,corrected))
    if changed!=8:raise ValueError('Expected exactly eight changed bytes')
    chunks(corrected)
    return bytes(corrected),changes


def main():
    relative='CARS/COROLLA/GEOMETRY.BIN';data=data_path(relative).read_bytes()
    corrected,changes=repair_preview(data)
    plan={'source':relative,'source_bytes':len(data),'source_sha256':hashlib.sha256(data).hexdigest(),
          'result_bytes':len(corrected),'result_sha256':hashlib.sha256(corrected).hexdigest(),
          'changed_bytes':8,'changes':changes,'backup':relative+'.bak',
          'temporary_atomic_output':relative+'.uma-header.tmp',
          'checkpoint':'Commit the exact .bak and this plan before replacing GEOMETRY.BIN; require clean tracked state first',
          'resources_not_changed':['TEXTURES.BIN','GLOBAL','NIS','SOUND','executables','plugins'],
          'approval_required':True,'game_tested':False,
          'limits':'Repairs a demonstrably malformed header count only. Does not prove race visibility, fix non-stock kits, remove wheels, or animate the character.'}
    save_json('header-repair-plan.json',plan)
    print(f'IN-MEMORY ONLY: {len(changes)} fields, 8 changed bytes, size remains {len(data)}')
    for change in changes:print(change['part'],change['offset_hex'],change['old_hex'],'->',change['new_hex'])

if __name__=='__main__':main()
