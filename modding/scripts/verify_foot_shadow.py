"""Check staged shadow pixels independently of the package writer."""
import hashlib
import io
import struct
from PIL import Image
from inspect_assets import chunks,flatten,huff,jdlz
from extract_assets import payload,dds_header,mip_layout

TARGETS={0xb7f6575b,0xb7f657c0}


def pools(data):
    result={}
    for node in flatten(chunks(data)):
        if node['id']!='0x33310003':continue
        raw=payload(data,node)
        if len(raw)%24:raise ValueError('Partial descriptor')
        for at in range(0,len(raw),24):
            key,offset,size,outsize,back,_=struct.unpack_from('<6I',raw,at)
            blob=data[offset:offset+size]
            pool=jdlz(blob) if blob.startswith(b'JDLZ') else huff(blob)
            if len(pool)!=outsize:raise ValueError('Pool size mismatch')
            result[key]=(pool,outsize-back+0x88)
    return result


def verify(original,candidate):
    a,b=pools(original),pools(candidate)
    if a.keys()!=b.keys() or len(original)!=len(candidate):raise ValueError('Texture directory/size changed')
    for key,(old,header) in a.items():
        new,new_header=b[key]
        if key not in TARGETS:
            if old!=new or header!=new_header:raise ValueError('Unrelated texture changed')
            continue
        size=struct.unpack_from('<I',old,header+20)[0]
        if header!=new_header or old[size:]!=new[size:]:raise ValueError('Shadow metadata changed')
        w,h=struct.unpack_from('<HH',new,header+32)
        if (w,h,new[header+38],size)!=(128,64,0x24,10880):raise ValueError('Shadow format mismatch')
        levels=mip_layout(w,h,0x24,size)
        if len(levels)!=4:raise ValueError('Shadow mip count mismatch')
        image=Image.open(io.BytesIO(dds_header(w,h,b'DXT3',8192,len(levels))+new[:size])).convert('RGBA')
        if image.getpixel((0,0))[3] or image.getpixel((127,63))[3]:raise ValueError('Opaque shadow corners')
        if image.getextrema()[:3]!=((0,0),)*3 or not 0<image.getextrema()[3][1]<200:raise ValueError('Unexpected shadow pixels')
    return {'textures':len(a),'only_two_shadows_changed':True,'format':'DXT3 128x64, four mips','metadata_unchanged':True,'sha256':hashlib.sha256(candidate).hexdigest()}
