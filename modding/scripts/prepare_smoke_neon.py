"""Stage transparent smoke and underbody glow; leave decoded metadata unchanged."""
import hashlib
import io
import json
import struct
from PIL import Image
from inspect_assets import ROOT,chunks,flatten,jdlz
from extract_assets import dds_header,mip_layout
from prepare_tiremask import rewrite_jdlz


def prepare(source,names):
    output=bytearray(source);ranges=[]
    for root in flatten(chunks(source)):
        if root['id']!='0xb3300000':continue
        nodes=list(flatten(root['children']))
        infos=[n for n in nodes if n['id']=='0x33310004'];data=[n for n in nodes if n['id']=='0x33320002']
        if len(infos)!=1 or len(data)!=1:continue
        info,pixels=infos[0],data[0]
        if info['size']%124:raise ValueError('Partial TextureInfo')
        for at in range(info['payload'],info['end'],124):
            name=source[at+12:at+36].split(b'\0')[0].decode('ascii',errors='replace')
            if name not in names:continue
            placement=struct.unpack_from('<I',source,at+48)[0];size=struct.unpack_from('<I',source,at+56)[0]
            width,height=struct.unpack_from('<HH',source,at+68);fmt=source[at+74];mips=source[at+78]
            if fmt!=0x24 or not 1<=width<=1024 or not 1<=height<=1024:raise ValueError('Unexpected effect texture format')
            levels=mip_layout(width,height,fmt,size)
            if len(levels)!=mips:raise ValueError('Mip count mismatch')
            begin=pixels['payload']+120+placement;end=begin+size
            if begin%128 or begin<pixels['payload']+120 or end>pixels['end']:raise ValueError('Texture outside aligned pixel block')
            output[begin:end]=bytes(size)
            for level in levels:
                offset=begin+level['offset'];length=level['bytes']
                image=Image.open(io.BytesIO(dds_header(level['width'],level['height'],b'DXT3',length)+output[offset:offset+length])).convert('RGBA')
                if image.getextrema()!=((0,0),)*4:raise ValueError('Effect mip not transparent black')
            ranges.append({'name':name,'offset':begin,'bytes':size,'width':width,'height':height,'mips':mips})
    if sorted(r['name'] for r in ranges)!=sorted(names):raise ValueError('Effect absent or ambiguous')
    cursor=0
    for row in sorted(ranges,key=lambda r:r['offset']):
        begin=row['offset'];end=begin+row['bytes']
        if begin<cursor or source[cursor:begin]!=output[cursor:begin]:raise ValueError('Unrelated bytes changed or ranges overlap')
        cursor=end
    if source[cursor:]!=output[cursor:] or chunks(source)!=chunks(output):raise ValueError('Unrelated data or layout changed')
    return bytes(output),ranges


def main():
    files=[];sha=lambda data:hashlib.sha256(data).hexdigest()
    for stem,names in [('InGameCommon',{'SFX_SMOKE_A_CS','SFX_SMOKE_B_CS'}),('GLOBALB',{'NEONBLUR'})]:
        raw=ROOT/'GLOBAL'/f'{stem}.bun';raw=raw if raw.exists() else ROOT/'GLOBAL'/f'{stem}.BUN'
        packed=ROOT/'GLOBAL'/('GlobalB.lzc' if stem=='GLOBALB' else stem+'.lzc')
        source=raw.read_bytes();encoded=packed.read_bytes()
        if jdlz(encoded)!=source:raise ValueError('Raw/compressed baseline mismatch')
        candidate,ranges=prepare(source,names);compressed=rewrite_jdlz(encoded,candidate)
        for target,before,after in [(raw,source,candidate),(packed,encoded,compressed)]:
            relative=target.relative_to(ROOT);out=ROOT/'modding/staged-runtime/smoke-neon'/relative;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(after)
            files.append({'target':str(relative),'candidate':str(out.relative_to(ROOT)),'backup':str(relative)+'.before-smoke-neon.bak','before_sha256':sha(before),'after_sha256':sha(after),'before_bytes':len(before),'bytes':len(after),'decoded_pixel_ranges':ranges})
    (ROOT/'modding/smoke-neon-plan.json').write_text(json.dumps({'files':files,'installed':False,'gameplay_verified':False},indent=2)+'\n')
    print('Staged four files; every mip decoded transparent, unrelated bytes and chunk layout exact; game files untouched')


if __name__=='__main__':main()
