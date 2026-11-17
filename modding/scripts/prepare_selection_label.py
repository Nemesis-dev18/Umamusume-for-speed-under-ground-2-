"""Create an original text-only selection label and preserve the source TPK layout."""
import hashlib
import io
import json
from pathlib import Path
import struct
from PIL import Image,ImageDraw,ImageFont
from inspect_assets import ROOT,jdlz,chunks
from extract_assets import dds_header
from prepare_tiremask import rewrite_jdlz


def dxt3(image):
    stream=io.BytesIO();image.save(stream,format='DDS',pixel_format='DXT5');data=stream.getvalue()
    width,height=image.size;assert data[84:88]==b'DXT5' and width%4==height%4==0
    output=bytearray();alpha=image.getchannel('A')
    for y in range(0,height,4):
        for x in range(0,width,4):
            packed=sum(((alpha.getpixel((x+i%4,y+i//4))+8)//17)<<(i*4) for i in range(16))
            at=128+((y//4)*(width//4)+x//4)*16
            output.extend(packed.to_bytes(8,'little'));output.extend(data[at+8:at+16])
    assert len(output)==width*height
    return bytes(output)


def main():
    source=ROOT/'FRONTEND/FrontB.lzc';original=source.read_bytes();raw=jdlz(original)
    record=json.loads((ROOT/'modding/selection-label-source.json').read_text());start=record['pixel_offset'];size=record['bytes'];header=record['decoded_header']
    if raw[header+12:header+36].split(b'\0')[0]!=b'SECONDARY_LOGO_COROLLA' or (record['width'],record['height'],record['mips'],size)!=(256,64,1,16384):raise ValueError('Unexpected selection label')
    image=Image.new('RGBA',(1024,256),(255,255,255,0));draw=ImageDraw.Draw(image)
    font=Path('/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf')
    for text,y in [('KITASAN',4),('BLACK',126)]:
        face=ImageFont.truetype(str(font),112);box=draw.textbbox((0,0),text,font=face);width=box[2]-box[0]
        draw.text(((1024-width)/2-box[0],y-box[1]),text,font=face,fill=(255,255,255,255))
    image=image.resize((256,64),Image.Resampling.LANCZOS);pixels=dxt3(image)
    decoded=Image.open(io.BytesIO(dds_header(256,64,b'DXT3',size)+pixels)).convert('RGBA')
    assert decoded.getextrema()[3][0]==0 and decoded.getextrema()[3][1]==255
    modified=raw[:start]+pixels+raw[start+size:];assert len(modified)==len(raw) and chunks(modified)==chunks(raw)
    candidate=rewrite_jdlz(original,modified);assert jdlz(candidate)==modified
    out=ROOT/'modding/staged-runtime/FrontB.kitasan-label.lzc';out.write_bytes(candidate)
    image.save(ROOT/'modding/diagnostics/kitasan-selection-label.png')
    preview=Image.new('RGBA',image.size,(40,40,40,255));preview.alpha_composite(decoded);preview.save(ROOT/'modding/diagnostics/kitasan-selection-label-preview.png')
    plan={'target':str(source.relative_to(ROOT)),'candidate':str(out.relative_to(ROOT)),'backup':'FRONTEND/FrontB.lzc.before-kitasan-label.bak','before_sha256':hashlib.sha256(original).hexdigest(),'after_sha256':hashlib.sha256(candidate).hexdigest(),'decoded_changed_range':[start,start+size],'decoded_bytes':len(raw),'bytes':len(candidate),'installed':False,'gameplay_verified':False}
    (ROOT/'modding/selection-label-plan.json').write_text(json.dumps(plan,indent=2)+'\n');print('Original Kitasan text label staged; one DXT3 level, decoded layout preserved')


if __name__=='__main__':main()
