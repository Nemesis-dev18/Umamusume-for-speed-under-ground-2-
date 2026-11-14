"""Extract NFSU2 Corolla data without changing any game resource."""
import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path
from inspect_assets import ROOT, chunks, data_path, flatten, jdlz, huff, save_json


def payload(data, node):
    return data[node['payload']:node['end']]


def skip_words(data):
    at = 0
    while data[at:at+4] == b'\x11'*4:
        at += 4
    return at


def geometry(data, selected):
    result = []
    for solid in flatten(chunks(data)):
        if solid['id'] != '0x80134010':
            continue
        leaves = {n['id']: n for n in flatten(solid.get('children', []))}
        required = ('0x00134011', '0x00134900', '0x00134b01', '0x00134b03')
        if not all(k in leaves for k in required):
            continue
        header = payload(data, leaves[required[0]])
        names = re.findall(rb'[!-~]{4,}', header)
        name = max(names, key=len).decode('ascii') if names else f"solid_{solid['offset']:x}"
        if selected not in name:
            continue
        mh = payload(data, leaves[required[1]])
        mh = mh[skip_words(mh):]
        if len(mh) < 56:
            raise ValueError('Short mesh header')
        triangles, vertices = struct.unpack_from('<I', mh, 36)[0], struct.unpack_from('<I', mh, 52)[0]
        vb, ib = (payload(data, leaves[k]) for k in required[2:])
        if not vertices or not triangles:
            continue
        stride = next((s for s in (36,24) if len(vb) >= vertices*s and
                       all(b == 0x11 for b in vb[:len(vb)-vertices*s])), None)
        if stride is None:
            raise ValueError(f'{name}: unsupported vertex layout')
        lead = len(vb)-vertices*stride
        positions, normals, uv = [], [], []
        for at in range(lead, len(vb), stride):
            p = struct.unpack_from('<3f', vb, at)
            n = struct.unpack_from('<3f', vb, at+12) if stride == 36 else None
            t = struct.unpack_from('<2f', vb, at+stride-8)
            if not all(math.isfinite(v) for v in (*p, *(n or ()), *t)):
                raise ValueError(f'{name}: nonfinite vertex')
            positions.append(p); normals.append(n); uv.append(t)
        # Locate filler by words; do not consume a genuine u16 index whose low byte is 0x11.
        first = skip_words(ib)
        if first+triangles*6 > len(ib):
            raise ValueError(f'{name}: truncated indices')
        indices = struct.unpack_from(f'<{triangles*3}H', ib, first)
        if max(indices) >= vertices:
            raise ValueError(f'{name}: index out of bounds')
        markers = []
        if '0x0013401a' in leaves:
            raw = payload(data, leaves['0x0013401a']); begin = skip_words(raw)
            if (len(raw)-begin)%80:
                raise ValueError('Partial marker record')
            for at in range(begin,len(raw),80):
                matrix = struct.unpack_from('<16f',raw,at+16)
                if not all(math.isfinite(v) for v in matrix): raise ValueError('Nonfinite marker')
                markers.append({'hash':f'0x{struct.unpack_from("<I",raw,at)[0]:08x}','matrix':matrix})
        runs=[]
        if '0x00134012' in leaves and '0x00134b02' in leaves:
            materials=payload(data,leaves['0x00134012'])
            ranges=payload(data,leaves['0x00134b02'])
            lead=len(ranges)%60
            for at in range(lead,len(ranges),60):
                count=struct.unpack_from('<I',ranges,at+12)[0]
                material=struct.unpack_from('<I',ranges,at+28)[0]
                start=struct.unpack_from('<I',ranges,at+52)[0]
                if count:
                    if start+count>len(indices) or count%3 or start%3 or material*8+4>len(materials):
                        raise ValueError('Invalid material index range')
                    runs.append({'offset':start,'count':count,'texture_hash':f'{struct.unpack_from("<I",materials,material*8)[0]:08x}'})
            if sorted((r['offset'],r['count']) for r in runs)!=[(0,len(indices))]:
                raise ValueError('Selected prototype requires one covering material run')
        result.append({'name':name,'solid_offset':solid['offset'],'stride':stride,
                       'vertex_data_offset':leaves[required[2]]['payload']+lead,
                       'index_data_offset':leaves[required[3]]['payload']+first,
                       'positions':positions,'normals':normals,'uv':uv,'indices':indices,
                       'markers':markers,'material_runs':runs,'transform':struct.unpack_from('<16f',header,64) if len(header)>=128 else None,
                       'native_bones':None,'native_animation_curves':None})
    return result


def write_obj(mesh, path):
    with path.open('x') as out:
        out.write('# Local coordinates; transform and hashed markers are in manifest.json\n')
        if mesh['material_runs']:
            out.write(f'mtllib {path.stem}.mtl\n')
            out.write(f"usemtl texture_{mesh['material_runs'][0]['texture_hash']}\n")
        for p in mesh['positions']: out.write('v '+' '.join(map(str,p))+'\n')
        for t in mesh['uv']: out.write('vt '+' '.join(map(str,t))+'\n')
        normals = all(n is not None for n in mesh['normals'])
        if normals:
            for n in mesh['normals']: out.write('vn '+' '.join(map(str,n))+'\n')
        ids=mesh['indices']
        for i in range(0,len(ids),3):
            out.write('f '+' '.join(f'{v+1}/{v+1}/{v+1}' if normals else f'{v+1}/{v+1}' for v in ids[i:i+3])+'\n')


def mip_layout(w,h,fmt,total):
    levels=[];offset=0
    while True:
        size=(((w+3)//4)*((h+3)//4)*(8 if fmt==0x22 else 16) if fmt in (0x22,0x24,0x26)
              else w*h*(4 if fmt==0x20 else 1))
        if offset+size>total:raise ValueError('Partial mip chain')
        levels.append({'width':w,'height':h,'offset':offset,'bytes':size});offset+=size
        if offset==total:return levels
        if w==h==1:raise ValueError('ImageSize exceeds full mip chain')
        w=max(1,w//2);h=max(1,h//2)


def dds_header(w,h,tag,size,mips=1):
    fields = [124,0x81007 | (0x20000 if mips>1 else 0),h,w,size,0,mips]+[0]*11
    fields += [32,4,int.from_bytes(tag,'little'),0,0,0,0,0]
    fields += [0x1000 | (0x400008 if mips>1 else 0),0,0,0,0]
    return b'DDS '+struct.pack('<31I',*fields)


def textures(data, destination):
    from PIL import Image
    records=[]
    for node in flatten(chunks(data)):
        if node['id'] != '0x33310003': continue
        desc=payload(data,node)
        if len(desc)%24: raise ValueError('Partial TPK descriptor')
        for i in range(0,len(desc),24):
            key,offset,size,outsize,back,unknown=struct.unpack_from('<6I',desc,i)
            record={'hash':f'0x{key:08x}','descriptor_offset':node['payload']+i,'blob_offset':offset,
                    'blob_size':size,'blob_mod128':offset%128,'decompressed_size':outsize}
            if offset+size>len(data): raise ValueError('Texture blob out of bounds')
            blob=data[offset:offset+size];record['codec']=blob[:4].decode('ascii',errors='replace')
            if not blob.startswith((b'JDLZ',b'HUFF')):
                record['unresolved']='Codec not yet implemented; no fabricated output';records.append(record);continue
            pool=jdlz(blob) if blob.startswith(b'JDLZ') else huff(blob)
            p=outsize-back+0x88
            if len(pool)!=outsize or p<24 or p+39>len(pool): raise ValueError('Embedded texture header out of range')
            if struct.unpack_from('<I',pool,p)[0]!=key: raise ValueError('Texture hash mismatch')
            w,h=struct.unpack_from('<HH',pool,p+32);fmt=pool[p+38]
            if not 1<=w<=4096 or not 1<=h<=4096: raise ValueError('Texture dimensions invalid')
            record.update(name=pool[p-24:p].split(b'\0')[0].decode('ascii',errors='replace'),width=w,height=h,format=hex(fmt),header_in_pool=p)
            target=destination/f'{key:08x}'
            image_size=struct.unpack_from('<I',pool,p+20)[0]
            levels=mip_layout(w,h,fmt,image_size) if fmt in (0x22,0x24,0x26,0x20,0x08,0x80,0x81) else []
            if image_size>p:raise ValueError('Mip data overlaps texture header')
            record['mips']=levels
            if fmt in (0x22,0x24,0x26):
                tag={0x22:b'DXT1',0x24:b'DXT3',0x26:b'DXT5'}[fmt]
                length=((w+3)//4)*((h+3)//4)*(8 if fmt==0x22 else 16)
                if length>p: raise ValueError('Texture pixels overlap header')
                dds=dds_header(w,h,tag,length,len(levels))+pool[:image_size]
                target.with_suffix('.dds').write_bytes(dds)
                with Image.open(target.with_suffix('.dds')) as image: image.save(target.with_suffix('.png'))
                record['exported_mips']=len(levels)
            elif fmt==0x20:
                if w*h*4>p: raise ValueError('BGRA pixels overlap header')
                Image.frombytes('RGBA',(w,h),pool[:w*h*4],'raw','BGRA').save(target.with_suffix('.png'))
                record['exported_mips']=len(levels)
            elif fmt in (0x08,0x80,0x81):
                imageoff,paletteoff,imagesize,palettesize=struct.unpack_from('<4I',pool,p+12)
                pal=paletteoff-imageoff
                if palettesize!=1024 or pal<w*h or pal+1024>len(pool): raise ValueError('Palette out of bounds')
                colors=pool[pal:pal+1024];rgba=bytearray()
                for index in pool[:w*h]:
                    b,g,r,a=colors[index*4:index*4+4];rgba.extend((r,g,b,a))
                Image.frombytes('RGBA',(w,h),bytes(rgba)).save(target.with_suffix('.png'))
                record.update(exported_mips=len(levels),palette_offset=pal,image_size=imagesize)
            else: record['unresolved']='Unsupported pixel format'
            if levels and 'unresolved' not in record:
                mipdir=destination/f'{key:08x}_mips';mipdir.mkdir()
                for level,mip in enumerate(levels):
                    mw,mh,begin,length=(mip[k] for k in ('width','height','offset','bytes'))
                    pixels=pool[begin:begin+length]
                    if fmt in (0x22,0x24,0x26):
                        import io
                        with Image.open(io.BytesIO(dds_header(mw,mh,tag,length)+pixels)) as image:
                            image.save(mipdir/f'{level:02d}.png')
                    elif fmt==0x20:Image.frombytes('RGBA',(mw,mh),pixels,'raw','BGRA').save(mipdir/f'{level:02d}.png')
                    else:
                        rgba=bytearray()
                        for index in pixels:
                            b,g,r,a=colors[index*4:index*4+4];rgba.extend((r,g,b,a))
                        Image.frombytes('RGBA',(mw,mh),bytes(rgba)).save(mipdir/f'{level:02d}.png')
            records.append(record)
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--car',default='COROLLA',choices=['COROLLA'])
    parser.add_argument('--part',default='KIT00_BODY_')
    parser.add_argument('--output',default='extracted/COROLLA',help='New directory relative to modding/')
    args=parser.parse_args()
    relative=Path(args.output)
    if relative.is_absolute() or '..' in relative.parts: raise ValueError('Output must stay inside modding/')
    destination=ROOT/'modding'/relative
    for parent in (destination,*destination.parents):
        if parent==ROOT: break
        if parent.is_symlink(): raise ValueError('Output symlink excluded')
    if destination.exists(): raise ValueError('Destination exists; refusing overwrite')
    sources={name:data_path(f'CARS/{args.car}/{name}') for name in ('GEOMETRY.BIN','TEXTURES.BIN')}
    before={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in sources.items()}
    meshes=geometry(sources['GEOMETRY.BIN'].read_bytes(),args.part)
    if not meshes: raise ValueError('No matching geometry')
    destination.mkdir(parents=True)
    summary=[]
    for mesh in meshes:
        safe=re.sub('[^A-Za-z0-9_-]','_',mesh['name'])
        write_obj(mesh,destination/f'{safe}.obj')
        if mesh['material_runs']:
            key=mesh['material_runs'][0]['texture_hash']
            with (destination/f'{safe}.mtl').open('x') as material:
                material.write(f'newmtl texture_{key}\nKd 1 1 1\nmap_Kd textures/{key}.png\n')
        info={k:v for k,v in mesh.items() if k not in ('positions','normals','uv','indices')}
        info.update(vertices=len(mesh['positions']),triangles=len(mesh['indices'])//3)
        summary.append(info)
    texture_dir=destination/'textures';texture_dir.mkdir()
    tex=textures(sources['TEXTURES.BIN'].read_bytes(),texture_dir)
    after={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in sources.items()}
    if before!=after: raise ValueError('Source changed during extraction')
    manifest={'source_sha256':before,'source_unchanged':True,'meshes':summary,'textures':tex,
              'limitations':['Original mip chain extracted; no re-encoding or repacking','Native rig/curves not identified; markers are not bones']}
    save_json(str(relative/'manifest.json'),manifest)
    print(f'Extracted {len(meshes)} meshes; {len(tex)} texture records; {sum("unresolved" not in t for t in tex)} textures decoded; sources unchanged')

if __name__=='__main__': main()
