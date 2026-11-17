"""Stage a string-table pointer change to Kitasan Black without rewriting other strings."""
import hashlib
import json
import struct
from inspect_assets import ROOT,chunks
from disable_car_effects import string_hash


def entries(data):
    nodes=[n for n in chunks(data) if n['id']=='0x00039000']
    if len(nodes)!=1:raise ValueError('Expected one language block')
    node=nodes[0];base=node['payload']
    if node['size']<16:raise ValueError('Truncated language header')
    unknown,count,keys,text=struct.unpack_from('<4I',data,base)
    if not 16<=unknown<=keys<=text<=node['size'] or count>100000 or keys+count*8>text:raise ValueError('Invalid language table bounds')
    records=[]
    for i in range(count):
        at=base+keys+i*8;key,offset=struct.unpack_from('<2I',data,at);start=base+text+offset
        if not base+text<=start<node['end']:raise ValueError('String offset outside block')
        end=data.find(b'\0',start,node['end'])
        if end<0:raise ValueError('Unterminated language string')
        records.append((key,data[start:end],at))
    if len({r[0] for r in records})!=count:raise ValueError('Duplicate string keys')
    return node,text,records


def prepare(data):
    node,text,records=entries(data);key=string_hash('CAR_NAME_COROLLA');target=[r for r in records if r[0]==key]
    if len(target)!=1 or target[0][1]!=b'Corolla':raise ValueError('Unexpected Corolla label')
    added=b'Kitasan Black\0';payload_size=node['size']+len(added);padding=(-payload_size)%16
    output=bytearray(data[:node['end']]+added+bytes(padding)+data[node['end']:])
    struct.pack_into('<I',output,node['offset']+4,payload_size+padding)
    struct.pack_into('<I',output,target[0][2]+4,node['size']-text)
    _,_,after=entries(output)
    if {k:v for k,v,_ in after}!={k:(b'Kitasan Black' if k==key else v) for k,v,_ in records}:raise ValueError('Unrelated string changed')
    return bytes(output)


def prepare_names(data,names):
    node,text,records=entries(data);mapping={string_hash('CAR_NAME_'+slot):name.encode('utf-8') for slot,name in names.items()}
    if not mapping or len(mapping)!=len(names) or not mapping.keys()<={k for k,_,_ in records}:raise ValueError('Missing or duplicate vehicle name key')
    if any(not name or b'\0' in name or len(name)>96 for name in mapping.values()):raise ValueError('Invalid vehicle label')
    added=bytearray();offsets={}
    for key,name in mapping.items():offsets[key]=node['size']-text+len(added);added.extend(name+b'\0')
    size=node['size']+len(added);padding=(-size)%16;output=bytearray(data[:node['end']]+added+bytes(padding)+data[node['end']:]);struct.pack_into('<I',output,node['offset']+4,size+padding)
    for key,old,at in records:
        if key in offsets:struct.pack_into('<I',output,at+4,offsets[key])
    _,_,after=entries(output)
    if {k:v for k,v,_ in after}!={k:mapping.get(k,v) for k,v,_ in records}:raise ValueError('Unrelated language entry changed')
    return bytes(output)


def main():
    rows=[]
    for language in ['English','Spanish']:
        target=ROOT/'LANGUAGES'/(language+'.bin');source=target.read_bytes();out=prepare(source)
        candidate=ROOT/'modding/staged-runtime'/(language+'.kitasan.bin');candidate.write_bytes(out)
        rows.append({'target':str(target.relative_to(ROOT)),'candidate':str(candidate.relative_to(ROOT)),'backup':str(target.relative_to(ROOT))+'.before-kitasan-name.bak','before_sha256':hashlib.sha256(source).hexdigest(),'after_sha256':hashlib.sha256(out).hexdigest(),'before_bytes':len(source),'bytes':len(out)})
    (ROOT/'modding/character-name-plan.json').write_text(json.dumps({'files':rows,'installed':False,'gameplay_verified':False},indent=2)+'\n');print('Staged English/Spanish Kitasan Black label; other strings preserved')


if __name__=='__main__':main()
