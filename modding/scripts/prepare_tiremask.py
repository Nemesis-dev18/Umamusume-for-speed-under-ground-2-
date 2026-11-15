"""Make the independent front-end tire mask transparent; preserve decoded chunk layout."""
import hashlib
import json
import struct
from inspect_assets import ROOT,chunks,flatten,jdlz


def rewrite_jdlz(source,data):
    original=jdlz(source)
    if not data or len(data)!=len(original):raise ValueError('JDLZ decoded size changed')
    stream=bytearray();bit1=bit2=8;flag1=flag2=0
    def emit(literal,a,b=0,near=0):
        nonlocal bit1,bit2,flag1,flag2
        if bit1==8:flag1=len(stream);stream.append(0);bit1=0
        if bit2==8:flag2=len(stream);stream.append(0);bit2=0
        if literal:stream.append(a)
        else:
            stream[flag1]|=1<<bit1;stream[flag2]|=near<<bit2;bit2+=1;stream.extend((a,b))
        bit1+=1
    at=16;position=0;flags1=flags2=1
    while position<len(data):
        if flags1==1:flags1=source[at]|256;at+=1
        if flags2==1:flags2=source[at]|256;at+=1
        if flags1&1:
            a,b=source[at:at+2];at+=2;near=flags2&1
            length,distance=(((a&240)<<4|b)+3,(a&15)+1) if near else ((a&31)+3,(b|((a&224)<<3))+17)
            # A changed source pixel must never leak through a back-reference into another texture.
            if all(data[position+k]==data[position+k-distance] for k in range(length)):emit(False,a,b,near)
            else:
                for value in data[position:position+length]:emit(True,value)
            position+=length;flags2>>=1
        else:emit(True,data[position]);position+=1;at+=1
        flags1>>=1
    encoded=b'JDLZ\x02\x10\0\0'+struct.pack('<2I',len(data),len(stream)+16)+stream
    if jdlz(encoded)!=data:raise ValueError('JDLZ rewrite failed')
    return encoded


def prepare(source):
    original=jdlz(source);result=bytearray(original);matches=[]
    for tpk in flatten(chunks(original)):
        if tpk['id']!='0xb3300000':continue
        nodes=list(flatten(tpk['children']))
        infos=[n for n in nodes if n['id']=='0x33310004']
        pixels=[n for n in nodes if n['id']=='0x33320002']
        if len(infos)!=1 or len(pixels)!=1:continue
        info,data=infos[0],pixels[0]
        if info['size']%124:raise ValueError('Partial raw TextureInfo')
        for at in range(info['payload'],info['end'],124):
            if original[at+12:at+36].split(b'\0')[0]!=b'TIREMASK':continue
            key=struct.unpack_from('<I',original,at+36)[0]
            placement,size=struct.unpack_from('<I',original,at+48)[0],struct.unpack_from('<I',original,at+56)[0]
            width,height=struct.unpack_from('<HH',original,at+68)
            fmt,mips=original[at+74],original[at+78]
            if (key,width,height,fmt,mips,size)!=(0xc8cbb2df,128,128,0x22,5,10912):raise ValueError('Unexpected tire-mask format')
            begin=data['payload']+120+placement;end=begin+size
            if begin%128 or begin<data['payload']+120 or end>data['end']:raise ValueError('Mask pixels outside aligned TPK data')
            result[begin:end]=(b'\0\0\0\0\xff\xff\xff\xff')*(size//8)
            matches.append({'texture':'TIREMASK','texture_info_offset':at,'pixel_offset':begin,'pixel_bytes':size,'format':'DXT1','width':width,'height':height,'mips':mips})
    if len(matches)!=1:raise ValueError('Tire mask absent or ambiguous')
    if chunks(result)!=chunks(original):raise ValueError('Decoded chunk layout changed')
    encoded=rewrite_jdlz(source,result)
    if jdlz(encoded)!=result:raise ValueError('JDLZ round trip failed')
    return encoded,matches


def main():
    target=ROOT/'FRONTEND/FrontB.lzc';backup=target.with_name(target.name+'.before-uma-tiremask.bak')
    source=(backup if backup.exists() else target).read_bytes();candidate,ranges=prepare(source)
    out=ROOT/'modding/staged-runtime/FrontB.no-tiremask.lzc';out.write_bytes(candidate)
    plan={'target':str(target.relative_to(ROOT)),'backup':str(backup.relative_to(ROOT)),'candidate':str(out.relative_to(ROOT)),'before_bytes':len(source),'bytes':len(candidate),'before_sha256':hashlib.sha256(source).hexdigest(),'after_sha256':hashlib.sha256(candidate).hexdigest(),'decoded_pixel_ranges':ranges,'installed':False,'gameplay_verified':False}
    (ROOT/'modding/tiremask-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    print('Staged transparent front-end tire mask:',len(source),'->',len(candidate),'bytes; decoded offsets unchanged')


if __name__=='__main__':main()
