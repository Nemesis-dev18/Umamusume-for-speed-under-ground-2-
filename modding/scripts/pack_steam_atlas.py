"""Build per-character padded diffuse atlases for the staged native runtime meshes."""
import hashlib,json,struct
from pathlib import Path
import numpy as np
from PIL import Image
from pack_texture import pack_texture
ROOT=Path(__file__).resolve().parents[2]
SIZE=2048
GUTTER=8


def pack(folder,output=None,preserve_resolution=False):
    size=4096 if preserve_resolution else SIZE
    path=folder/'runtime/model.umab';source=path.read_bytes();data=bytearray(source);report=json.loads((folder/'runtime/model.json').read_text());g=json.loads((folder/'source.gltf').read_text())
    if hashlib.sha256(source).hexdigest()!=report['sha256']:raise ValueError('Stale motion asset')
    textures={};materials={m['name']:m for m in g['materials']}
    for group in report['groups']:
        texture=group['texture']
        if texture is None:raise ValueError('Missing diffuse material')
        if texture not in textures:
            image_path=folder/g['images'][g['textures'][texture]['source']]['uri']
            if group['material'].endswith('_face'):image_path=folder/'runtime/face-baked.png'
            image_path.resolve().relative_to(folder.resolve())
            with Image.open(image_path) as image:textures[texture]=image.convert('RGBA')
    atlas=Image.new('RGBA',(size,size));layout={};x=y=row_height=0
    for index,image in sorted(textures.items(),key=lambda item:(-max(item[1].size),-min(item[1].size),item[0])):
        cw=image.width+2*GUTTER if preserve_resolution else 1<<(image.width-1).bit_length();ch=image.height+2*GUTTER if preserve_resolution else 1<<(image.height-1).bit_length()
        if min(cw,ch)<=GUTTER*2 or max(cw,ch)>1040:raise ValueError('Unsupported diffuse texture size')
        if x+cw>size:x=0;y+=row_height;row_height=0
        if y+ch>size:raise ValueError('Atlas overflow')
        w,h=cw-2*GUTTER,ch-2*GUTTER
        if not preserve_resolution:image=image.convert('RGBa').resize((w,h),Image.Resampling.LANCZOS).convert('RGBA')
        pixels=np.array(image)
        padded=Image.fromarray(np.pad(pixels,((GUTTER,GUTTER),(GUTTER,GUTTER),(0,0)),mode='edge'));atlas.paste(padded,(x,y))
        layout[index]={'x':x+GUTTER,'y':y+GUTTER,'width':w,'height':h,'cell':[x,y,cw,ch]};x+=cw;row_height=max(row_height,ch)
    if struct.unpack_from('<I',data,4)[0]!=3:raise ValueError('Expected native UMAB v3')
    nv=struct.unpack_from('<I',data,8)[0];uv=np.ndarray((nv,2),'<f4',data,offset=68,strides=(36,4))
    for group in report['groups']:
        first=group['first_vertex'];count=group['vertex_count'];coordinates=uv[first:first+count].copy()
        if np.min(coordinates)<0 or np.max(coordinates)>1:raise ValueError('Wrapped diffuse UV needs a separate atlas cell')
        cell=layout[group['texture']];uv[first:first+count]=(coordinates*np.array([cell['width'],cell['height']])+np.array([cell['x'],cell['y']]))/size
        # Source opaque materials must not inherit an unused diffuse alpha channel.
        if materials[group['material']].get('alphaMode','OPAQUE')=='OPAQUE':
            rect=cell['cell']
            pixels=np.array(atlas);pixels[rect[1]:rect[1]+rect[3],rect[0]:rect[0]+rect[2],3]=255;atlas=Image.fromarray(pixels)
    nb=struct.unpack_from('<I',data,16)[0];ni=struct.unpack_from('<I',data,12)[0];indices=np.ndarray((ni,),'<u2',data,offset=40+nv*60+nb*16)
    for group in report['groups']:
        if group['eye_depth_off'] or group['material'].endswith('_cheek'):indices[group['first_index']:group['first_index']+group['index_count']]=0
    texture,levels,error=pack_texture(atlas);output=Path(output) if output is not None else folder/'runtime';output.resolve().relative_to(ROOT.resolve());output.mkdir(parents=True,exist_ok=True)
    atlas.save(output/'atlas.png');(output/'atlas.dds').write_bytes(texture);(output/'model-atlas.umab').write_bytes(data)
    receipt={'model_sha256':hashlib.sha256(data).hexdigest(),'source_model_sha256':report['sha256'],'atlas_sha256':hashlib.sha256(texture).hexdigest(),'size':[size,size],'source_resolution_preserved':preserve_resolution,'gutter_pixels':GUTTER,'layout':layout,'levels':levels,'opaque_rgb_rmse_0_255':error,'game_integrated':False,'neutral_iris_baked':True,'eye_depth_pass_pending':False}
    (output/'atlas.json').write_text(json.dumps(receipt,indent=2)+'\n');print(folder.name,len(texture),round(error,3),flush=True)


def main():
    for c in json.loads((ROOT/'modding/fleet-source-inventory.json').read_text())['characters']:pack(ROOT/'modding/uma-steam/fleet'/str(c['id']))

if __name__=='__main__':main()
