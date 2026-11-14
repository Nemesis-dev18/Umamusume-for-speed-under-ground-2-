"""Disable named optional car effects by marker identity, without moving any anchors."""
import struct
from inspect_assets import chunks,flatten
from extract_assets import payload,skip_words

NAMES=('LEFT_HEADLIGHT','RIGHT_HEADLIGHT','LEFT_BRAKELIGHT','RIGHT_BRAKELIGHT','CENTRE_BRAKELIGHT','REAR_LICENSE_PLATE','LEFT_EXHAUST','RIGHT_EXHAUST')


def string_hash(name):
    value=0xffffffff
    for c in name.encode('ascii'):
        value=(value*33+c)&0xffffffff
    return value


def disable_effects(data):
    nodes=[node for node in flatten(chunks(data)) if node['id']=='0x0013401a']
    names={string_hash(name):name for name in NAMES}
    existing=set()
    for node in nodes:
        raw=payload(data,node);lead=skip_words(raw)
        if (len(raw)-lead)%80:raise ValueError('Partial marker record')
        existing.update(struct.unpack_from('<I',raw,at)[0] for at in range(lead,len(raw),80))
    if not {string_hash(name) for name in NAMES[:6]}<=existing:raise ValueError('Required known Corolla light/plate marker absent')
    replacements={old:string_hash('UMA_OFF_'+name) for old,name in names.items()}
    if set(replacements.values())&existing:raise ValueError('Disabled marker hash collision')
    result=bytearray(data);changes=[]
    for node in nodes:
        raw=payload(data,node)
        for at in range(skip_words(raw),len(raw),80):
            old=struct.unpack_from('<I',raw,at)[0]
            if old not in names:continue
            offset=node['payload']+at;new=replacements[old]
            struct.pack_into('<I',result,offset,new)
            changes.append({'name':names[old],'offset':offset,'before':data[offset:offset+4].hex(),'after':result[offset:offset+4].hex()})
    if chunks(result)!=chunks(data):raise ValueError('Container layout changed')
    return bytes(result),changes
