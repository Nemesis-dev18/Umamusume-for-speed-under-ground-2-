"""Encode a full DXT5 mip chain for the independent renderer, not game installation."""
import hashlib
import io
import json
import numpy as np
from PIL import Image
from extract_assets import dds_header
from inspect_assets import ROOT


def pack_texture():
    with Image.open(ROOT/'modding/character-source/atlas.png') as source:image=source.convert('RGBA')
    w,h=image.size
    if w>4096 or h>4096 or w&(w-1) or h&(h-1):raise ValueError('Expected power-of-two texture')
    data=[];levels=[];top=image.copy()
    while True:
        stream=io.BytesIO();image.save(stream,format='DDS',pixel_format='DXT5');encoded=stream.getvalue()
        length=((image.width+3)//4)*((image.height+3)//4)*16
        if encoded[:4]!=b'DDS ' or encoded[84:88]!=b'DXT5' or len(encoded)!=128+length:raise ValueError('Unexpected DXT encoder layout')
        levels.append({'width':image.width,'height':image.height,'bytes':length});data.append(encoded[128:])
        if image.size==(1,1):break
        image=image.convert('RGBa').resize((max(1,image.width//2),max(1,image.height//2)),Image.Resampling.LANCZOS).convert('RGBA')
    result=dds_header(w,h,b'DXT5',len(data[0]),len(data))+b''.join(data)
    with Image.open(io.BytesIO(result)) as decoded:
        original=np.array(top,dtype=float);actual=np.array(decoded.convert('RGBA'),dtype=float)
        opaque=original[:,:,3]>.5*255
        rgb_rmse=float(np.sqrt(np.mean((original[:,:,:3][opaque]-actual[:,:,:3][opaque])**2)))
    return result,levels,rgb_rmse


def main():
    data,levels,error=pack_texture();destination=ROOT/'modding/runtime/atlas.dds'
    destination.write_bytes(data)
    report={'format':'Standard DDS DXT5/BC3 with premultiplied-alpha filtered mip generation','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'levels':levels,'opaque_rgb_rmse_0_255':error,'game_integrated':False}
    (destination.parent/'atlas-texture.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'bytes':len(data),'levels':len(levels),'opaque_rgb_rmse_0_255':error,'game_integrated':False}))

if __name__=='__main__':main()
