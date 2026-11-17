"""Stage original-size JDLZ shadow slots to isolate compressed-stream tail reads."""
import hashlib
import json
import struct
from pathlib import Path
from inspect_assets import ROOT,chunks,flatten,jdlz
from extract_assets import payload
from disable_car_effects import string_hash
from verify_foot_shadow import verify


def descriptors(data):
    entries={}
    for node in flatten(chunks(data)):
        if node['id']!='0x33310003':continue
        raw=payload(data,node)
        if len(raw)%24:raise ValueError('Partial descriptor')
        for at in range(0,len(raw),24):
            entry=struct.unpack_from('<6I',raw,at)
            if entry[0] in entries:raise ValueError('Duplicate texture hash')
            entries[entry[0]]=(node['payload']+at,entry)
    return entries


def prepare(original,compact,slot):
    before,after=descriptors(original),descriptors(compact)
    targets={string_hash(slot+'_SHADOWFE'),string_hash(slot+'_SHADOWIG')}
    if not targets.issubset(before) or before.keys()!=after.keys():raise ValueError('Shadow directory mismatch')
    out=bytearray(original);ranges=[]
    for key in targets:
        at,a=before[key];_,b=after[key]
        if a[1]!=b[1] or a[3:]!=b[3:]:raise ValueError('Relocated shadow unsupported')
        stream=bytearray(compact[b[1]:b[1]+b[2]])
        if stream[:4]!=b'JDLZ' or len(stream)+16>a[2]:raise ValueError('Insufficient original slot for tail guard')
        decoded=jdlz(stream)
        stream.extend(bytes(a[2]-len(stream)))
        struct.pack_into('<I',stream,12,len(stream))
        if jdlz(stream)!=decoded:raise ValueError('Guard changed decompressed bytes')
        out[a[1]:a[1]+a[2]]=stream;ranges.append((a[1],a[2]))
    if descriptors(out)!=before:raise ValueError('Descriptor changed')
    allowed=bytearray(len(original))
    for at,size in ranges:allowed[at:at+size]=b'\1'*size
    if any(x!=y and not allowed[i] for i,(x,y) in enumerate(zip(original,out))):raise ValueError('Unrelated bytes changed')
    verify(original,bytes(out),slot)
    return bytes(out),ranges


def main():
    rows=[]
    for row in json.loads((ROOT/'modding/fleet-shadow-plan.json').read_text())['files']:
        original=(ROOT/row['target']).read_bytes();compact=(ROOT/row['candidate']).read_bytes()
        candidate,ranges=prepare(original,compact,row['slot'])
        target=ROOT/'modding/staged-runtime/fleet-shadows-guard'/row['slot']/'TEXTURES.BIN'
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(candidate)
        rows.append({'slot':row['slot'],'target':row['target'],'candidate':str(target.relative_to(ROOT)),'before_sha256':hashlib.sha256(original).hexdigest(),'after_sha256':hashlib.sha256(candidate).hexdigest(),'changed_slots':ranges})
    (ROOT/'modding/fleet-shadow-guard-plan.json').write_text(json.dumps({'files':rows,'installed':False,'game_verified':False,'hypothesis':'Original compressed slot sizes and zero tail guard; does not establish crash cause'},indent=2)+'\n')
    print('Seven guarded candidates staged; original descriptors and unrelated bytes unchanged; NOT game verified')

if __name__=='__main__':main()
