"""Inspect data-only EAGL ELF animation banks; never load/execute ELF code."""
import argparse
import hashlib
import math
import struct
from pathlib import Path
from inspect_assets import ROOT, chunks, data_path, flatten, save_json
from extract_assets import payload, skip_words


def bounded(data, offset, size):
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError(f'Animation range {offset:#x}+{size:#x} exceeds {len(data):#x}')
    return data[offset:offset + size]


def u32(data, offset):
    return struct.unpack('<I', bounded(data, offset, 4))[0]


def string(data, offset):
    if not 0 <= offset < len(data): raise ValueError('String offset out of range')
    end = data.find(b'\0', offset, min(len(data), offset + 1024))
    if end < 0: raise ValueError('Unterminated animation string')
    return data[offset:end].decode('ascii')


def inspect_data_elf(elf, file_offset):
    h = struct.unpack('<16sHHIIIIIHHHHHH', bounded(elf, 0, 52))
    if h[0][:7] != b'\x7fELF\x01\x01\x01' or h[1:3] != (1, 8):
        raise ValueError('Expected ELF32 little-endian MIPS relocatable data')
    if h[10] or h[9]: raise ValueError('Program headers excluded')
    shoff, stride, count, names_index = h[6], h[11], h[12], h[13]
    if stride != 40 or not 1 <= count <= 256 or names_index >= count:
        raise ValueError('Invalid ELF section table')
    sections = [struct.unpack('<10I', bounded(elf, shoff+i*40, 40)) for i in range(count)]
    shnames = sections[names_index]
    names = bounded(elf, shnames[4], shnames[5])
    inventory=[]
    for i, section in enumerate(sections):
        if section[2] & 4: raise ValueError('Executable section excluded')
        if section[1] != 8: bounded(elf, section[4], section[5])
        inventory.append({'index': i, 'name': string(names, section[0]), 'type': section[1],
                          'flags': section[2], 'offset_in_elf': section[4], 'bytes': section[5],
                          'absolute_offset': file_offset+section[4], 'alignment': section[8]})
    symbols=[]
    for section in sections:
        if section[1] != 2: continue
        if section[9] != 16 or section[5]%16 or section[6] >= count:
            raise ValueError('Invalid ELF symbol table')
        ns=sections[section[6]];st=bounded(elf,ns[4],ns[5])
        for at in range(section[4],section[4]+section[5],16):
            nm,value,size,info,other,index=struct.unpack('<IIIBBH',bounded(elf,at,16))
            symbols.append({'name':string(st,nm),'value':value,'size':size,'info':info,'section':index})
    return sections,symbols,inventory


def inspect_bank(elf,file_offset):
    sections,symbols,inventory=inspect_data_elf(elf,file_offset)
    count=len(sections)
    roots=[s for s in symbols if s['name']=='__AnimationBank:::bank']
    if len(roots)!=1 or not 0 < roots[0]['section'] < count:raise ValueError('AnimationBank symbol absent/ambiguous')
    root=roots[0];ds=sections[root['section']];pool=bounded(elf,ds[4],ds[5])
    relocations={}
    for section in sections:
        if section[1]!=9:continue
        if section[7]!=root['section'] or section[9]!=8 or section[5]%8:
            raise ValueError('Unsupported animation relocations')
        for at in range(section[4],section[4]+section[5],8):
            offset,info=struct.unpack('<II',bounded(elf,at,8));symbol=info>>8
            if info&255!=2 or symbol>=len(symbols) or symbols[symbol]['section']!=root['section']:
                raise ValueError('Only local R_MIPS_32 data relocations are supported')
            target=u32(pool,offset)+symbols[symbol]['value']
            bounded(pool,target,1)
            if offset in relocations:raise ValueError('Duplicate relocation')
            relocations[offset]=target
    def pointer(offset):
        if offset not in relocations:raise ValueError(f'Missing data relocation at {offset:#x}')
        return relocations[offset]
    bank=root['value'];bounded(pool,bank,28)
    header_size,channels=struct.unpack_from('<II',pool,bank)
    if header_size!=28 or not 1<=channels<=4096:raise ValueError('Unsupported bank header')
    curve_table,name_table=pointer(bank+16),pointer(bank+20)
    bounded(pool,curve_table,channels*4);bounded(pool,name_table,channels*4)
    targets=sorted(set(relocations.values())|{len(pool)})
    curves=[]
    for i in range(channels):
        desc=pointer(curve_table+i*4);name=string(pool,pointer(name_table+i*4))
        bounded(pool,desc,16)
        fmt=pointer(desc+4);encoded=pointer(desc+12)
        kind,frames=struct.unpack_from('<HH',pool,desc+8)
        following=min(t for t in targets if t>encoded)
        raw=bounded(pool,encoded,following-encoded)
        curve={'name':name,'descriptor_offset_in_pool':desc,'kind_raw':kind,'frames_raw':frames,
               'format_offset_in_pool':fmt,'format12_hex':bounded(pool,fmt,12).hex(),
               'data_offset_in_pool':encoded,'data_absolute_offset':file_offset+ds[4]+encoded,
               'encoded_region_bytes':len(raw),'encoded_sha256':hashlib.sha256(raw).hexdigest(),
               'descriptor_hex':bounded(pool,desc,16).hex(),'data_header_hex':raw[:32].hex(),
               'decoded':False}
        if len(raw)>=32:
            signature,mode,components,samples=struct.unpack_from('<4I',raw)
            if (signature,mode,components)==(0x14000000,2,4) and samples==frames:
                if len(raw)!=32+samples*16:raise ValueError('Float4 curve extent mismatch')
                values=[struct.unpack_from('<4f',raw,32+j*16) for j in range(samples)]
                if not all(math.isfinite(x) for v in values for x in v):raise ValueError('Nonfinite curve')
                lengths=[math.sqrt(sum(x*x for x in v)) for v in values]
                curve.update(decoded=True,representation='stored float4 samples',values=values,
                             norm_min=min(lengths),norm_max=max(lengths),timebase='Unverified; sample order only')
        if not curve['decoded']:curve['unresolved']='Encoded curve variant not interpreted; not exported as floats'
        curves.append(curve)
    return {'elf_file_offset':file_offset,'data_file_offset':file_offset+ds[4],
            'elf_type':'ET_REL','machine':'MIPS','contains_executable_sections':False,
            'sections':inventory,'symbols':symbols,'relocations':relocations,'bank_offset_in_pool':bank,
            'channels':curves,'bone_hierarchy':None,'skinning_binding':None}


def inspect_skeleton(elf,file_offset):
    sections,symbols,inventory=inspect_data_elf(elf,file_offset)
    roots=[s for s in symbols if s['name'].startswith('__Skeleton:::')]
    if len(roots)!=1 or not 0<roots[0]['section']<len(sections):raise ValueError('Skeleton symbol absent/ambiguous')
    root=roots[0];ds=sections[root['section']];pool=bounded(elf,ds[4],ds[5]);base=root['value']
    bounded(pool,base,16);count=u32(pool,base+8)
    if not 1<=count<=512:raise ValueError('Skeleton bone count invalid')
    bounded(pool,base+16,count*112)
    names={}
    for symbol in symbols:
        if not symbol['name'].startswith('__Bone:::'):continue
        if symbol['section']!=root['section']:raise ValueError('Bone symbol outside skeleton data')
        index=u32(pool,symbol['value'])
        if index>=count or index in names:raise ValueError('Invalid/duplicate bone index')
        names[index]=symbol['name'].removeprefix('__Bone:::')
    if len(names)!=count:raise ValueError('Missing native bone names')
    bones=[]
    for i in range(count):
        at=base+16+i*112
        scale=struct.unpack_from('<3f',pool,at);parent=struct.unpack_from('<i',pool,at+12)[0]
        rotation=struct.unpack_from('<4f',pool,at+16);translation=struct.unpack_from('<3f',pool,at+32)
        lane=u32(pool,at+44);matrix=struct.unpack_from('<16f',pool,at+48)
        if not all(math.isfinite(v) for v in (*scale,*rotation,*translation,*matrix)):
            raise ValueError('Nonfinite skeleton data')
        if not -1<=parent<count or parent==i:raise ValueError('Invalid skeleton parent')
        bones.append({'index':i,'name':names[i],'parent':parent,'scale_raw':scale,'rotation_raw4':rotation,
                      'translation_raw3':translation,'index_lane_raw':lane,'matrix_raw16':matrix,
                      'record_absolute_offset':file_offset+ds[4]+at})
    for bone in bones:
        seen=set();at=bone['index']
        while at!=-1:
            if at in seen:raise ValueError('Skeleton parent cycle')
            seen.add(at);at=bones[at]['parent']
    return {'elf_file_offset':file_offset,'data_file_offset':file_offset+ds[4],
            'contains_executable_sections':False,'sections':inventory,'skeleton':root['name'].removeprefix('__Skeleton:::'),
            'skeleton_offset_in_pool':base,'header_hash_raw':f'0x{u32(pool,base):08x}',
            'bones':bones,'interpretation':'Hierarchy validated by parent ranges/cycles and named bone indices; transform convention and skin binding unverified'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',nargs='+',default=['CARS/COROLLA/PARTS_ANIMATIONS.bin','NIS/Scene_IntroNis01_BundleB.bun'])
    p.add_argument('--output',default='animation-banks.json')
    args=p.parse_args();output=Path(args.output)
    if output.is_absolute() or '..' in output.parts:raise ValueError('Output must stay inside modding')
    reports=[]
    for relative in args.input:
        data=data_path(relative).read_bytes();banks=[]
        for node in flatten(chunks(data)):
            if node['id'] not in ('0x00e34010','0x00e34009'):continue
            raw=payload(data,node);lead=skip_words(raw)
            bank=(inspect_bank if node['id']=='0x00e34010' else inspect_skeleton)(raw[lead:],node['payload']+lead)
            bank['chunk_offset']=node['offset'];banks.append(bank)
        reports.append({'source':relative,'sha256':hashlib.sha256(data).hexdigest(),'banks':banks})
    save_json(str(output),reports)
    curves=[c for r in reports for b in r['banks'] for c in b.get('channels',[])]
    print(f'{sum(len(r["banks"]) for r in reports)} data banks; {len(curves)} channels; {sum(c["decoded"] for c in curves)} float4 curves; {sum(len(b.get('bones',[])) for r in reports for b in r['banks'])} native bones; skin binding unverified')

if __name__=='__main__':main()
