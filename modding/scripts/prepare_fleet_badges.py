"""Stage distinct chibi badges while retaining ordinary-car manufacturer textures."""
import hashlib,json,struct
from PIL import Image
from inspect_assets import ROOT,chunks,flatten,jdlz
from disable_car_effects import string_hash
from prepare_selection_label import dxt3
from prepare_kitasan_badge import badge,compress_jdlz
NAMES={1068:'KITASAN',1052:'URARA',1032:'TACHYON',1062:'MAMBO',1015:'OPERA',1006:'OGURI',1058:'DOTO'}


def directory(raw):
    result={}
    for tpk in flatten(chunks(raw)):
        if tpk['id']!='0xb3300000':continue
        nodes=list(flatten(tpk['children']));info=next((n for n in nodes if n['id']=='0x33310004'),None);pool=next((n for n in nodes if n['id']=='0x33320002'),None)
        if not info or not pool:continue
        for at in range(info['payload'],info['end'],124):
            key=struct.unpack_from('<I',raw,at+36)[0];offset,size=struct.unpack_from('<I',raw,at+48)[0],struct.unpack_from('<I',raw,at+56)[0];begin=pool['payload']+120+offset
            if begin+size>pool['end']:raise ValueError('Texture range outside pool')
            if key in result:raise ValueError('Ambiguous texture hash')
            result[key]=(begin,size,raw[at:at+124])
    return result


def main():
    source=(ROOT/'FRONTEND/FrontB.lzc').read_bytes();original=jdlz(source);raw=original;old=directory(original);outputs={};folder=ROOT/'modding/menu-art/badges';folder.mkdir(parents=True,exist_ok=True)
    for identifier,name in NAMES.items():
        model=ROOT/'modding/uma-steam/mini-fleet'/str(identifier);report=json.loads((model/'badge-review.json').read_text())
        if report.get('shading')!='Unlit diffuse with source alpha for UI badge':raise ValueError('Outdated mini render')
        if report['source_gltf_sha256']!=hashlib.sha256((model/'source.gltf').read_bytes()).hexdigest():raise ValueError('Stale mini render')
        with Image.open(model/'badge-review.png') as image:
            image=image.convert('RGBA');box=image.getchannel('A').getbbox()
            if box is None:raise ValueError('Empty mini render')
            image=image.crop(box);image.thumbnail((62,62),Image.Resampling.LANCZOS);canvas=Image.new('RGBA',(128,64));canvas.alpha_composite(image,((128-image.width)//2,(64-image.height)//2))
        canvas.save(folder/(str(identifier)+'.png'));pixels=dxt3(canvas);key=string_hash('CARSELECT_MANUFACTURER_'+name);outputs[key]=pixels
        if identifier==1068:
            begin,size,_=directory(raw)[key]
            if size!=len(pixels):raise ValueError('Existing Kitasan badge size changed')
            raw=raw[:begin]+pixels+raw[begin+size:]
        else:raw,added=badge(raw,pixels,name);assert added==key
    after=directory(raw)
    for key,(begin,size,header) in old.items():
        new_begin,new_size,_=after[key]
        if size!=new_size or (key not in outputs and original[begin:begin+size]!=raw[new_begin:new_begin+new_size]):raise ValueError('Unrelated frontend texture changed')
    for key,pixels in outputs.items():
        begin,size,_=after[key]
        if raw[begin:begin+size]!=pixels:raise ValueError('Badge pixel verification failed')
    encoded=compress_jdlz(raw)
    if len(encoded)>=len(raw) or jdlz(encoded)!=raw:raise ValueError('Invalid frontend compression')
    path=ROOT/'modding/staged-runtime/FrontB.fleet-badges.lzc';path.write_bytes(encoded)
    (ROOT/'modding/fleet-badge-plan.json').write_text(json.dumps({'target':'FRONTEND/FrontB.lzc','candidate':str(path.relative_to(ROOT)),'before_sha256':hashlib.sha256(source).hexdigest(),'after_sha256':hashlib.sha256(encoded).hexdigest(),'manufacturers':NAMES,'installed':False,'manufacturer_mapping_pending':True,'menu_visual_approved':False},indent=2)+'\n');print('Seven badges staged; unrelated texture pixels preserved; manufacturer mapping pending')

if __name__=='__main__':main()
