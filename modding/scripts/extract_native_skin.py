"""Extract the observed 60-byte NIS skin layout; preserve local bone palettes."""
import argparse
import hashlib
import math
import re
import struct
from pathlib import Path
from inspect_assets import ROOT, chunks, data_path, flatten, save_json
from extract_assets import payload, skip_words, write_obj
from extract_animation_banks import bounded


def read_skin(data):
    meshes=[]
    for solid in flatten(chunks(data)):
        if solid['id']!='0x80134010':continue
        leaves={n['id']:n for n in flatten(solid.get('children',[]))}
        required=('0x00134011','0x00134900','0x00134b01','0x00134b02','0x00134b03')
        if not all(k in leaves for k in required):continue
        header,mh,vb,ranges,ib=[payload(data,leaves[k]) for k in required]
        mh=mh[skip_words(mh):]
        if len(mh)<56:raise ValueError('Short native mesh header')
        triangles=struct.unpack_from('<I',mh,36)[0];vertices=struct.unpack_from('<I',mh,52)[0]
        if not vertices or not triangles:continue
        begin=len(vb)-vertices*60
        if begin<0 or vb[:begin]!=b'\x11'*begin:
            continue
        names=re.findall(rb'[!-~]{5,}',header)
        name=max(names,key=len).decode() if names else f"solid_{solid['offset']:x}"
        header_start=skip_words(header)
        bone_count=bounded(header,header_start+24,1)[0]
        if not 1<=bone_count<=128:raise ValueError('Invalid native bone-count byte')
        points=[];normals=[];uv=[];weights=[];local_indices=[]
        for i in range(vertices):
            at=begin+i*60
            position=struct.unpack_from('<3f',vb,at);normal=struct.unpack_from('<3f',vb,at+12)
            tex=struct.unpack_from('<2f',vb,at+28)
            weight=struct.unpack_from('<3f',vb,at+36);indices=struct.unpack_from('<3f',vb,at+48)
            if not all(math.isfinite(v) for v in (*position,*normal,*tex,*weight,*indices)):
                raise ValueError('Nonfinite skin vertex')
            if any(not 0<=w<=1 for w in weight) or abs(sum(weight)-1)>1e-5:
                raise ValueError('Invalid skin weights')
            if any(v!=int(v) or not 0<=v<16 for v in indices):
                raise ValueError('Invalid local bone palette index')
            points.append(position);normals.append(normal);uv.append(tex)
            weights.append(weight);local_indices.append([int(v) for v in indices])
        first=skip_words(ib)
        index_data=bounded(ib,first,triangles*6)
        indices=list(struct.unpack(f'<{triangles*3}H',index_data))
        if max(indices)>=vertices:raise ValueError('Native triangle index out of bounds')
        lead=len(ranges)%60
        if ranges[:lead]!=b'\x11'*lead:raise ValueError('Unexpected material padding')
        runs=[];expected=0
        for at in range(lead,len(ranges),60):
            count=struct.unpack_from('<I',ranges,at+12)[0]
            start=struct.unpack_from('<I',ranges,at+52)[0]
            if not count:continue
            if start!=expected or count%3 or start+count>len(indices):raise ValueError('Native material ranges do not tile triangles')
            palette=list(ranges[at+33:at+49])
            used=sorted(set(palette[local_indices[v][j]] for v in indices[start:start+count] for j in range(3) if weights[v][j]>0))
            if any(index>=bone_count for index in used):raise ValueError('Palette maps outside declared bone count')
            runs.append({'offset':start,'count':count,'slot_byte_raw':ranges[at+32],
                         'palette16_raw':palette,'candidate_global_bone_indices_used':used,
                         'interpretation':'Palette association inferred from byte table/local indices; skeleton identity not resolved'})
            expected+=count
        if expected!=len(indices):raise ValueError('Incomplete native material ranges')
        meshes.append({'name':name,'solid_offset':solid['offset'],'vertex_stride':60,'bone_count_byte':bone_count,
                       'vertex_data_absolute_offset':leaves['0x00134b01']['payload']+begin,
                       'positions':points,'normals':normals,'uv':uv,'indices':indices,
                       'weights':weights,'local_bone_indices':local_indices,'skin_runs':runs,
                       'skeleton_binding':None,'material_runs':[]})
    return meshes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',default='NIS/Scene_IntroNis01_BundleB.bun')
    parser.add_argument('--output',default='extracted/native-skin')
    args=parser.parse_args();relative=Path(args.output)
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('Output outside modding')
    destination=ROOT/'modding'/relative
    for parent in (destination,*destination.parents):
        if parent==ROOT:break
        if parent.is_symlink():raise ValueError('Output symlink excluded')
    if destination.exists():raise ValueError('Output already exists')
    source=data_path(args.input);data=source.read_bytes();before=hashlib.sha256(data).hexdigest()
    meshes=read_skin(data)
    if not meshes:raise ValueError('No validated 60-byte native skin meshes')
    destination.mkdir(parents=True)
    for mesh in meshes:
        safe=re.sub('[^A-Za-z0-9_-]','_',mesh['name'])
        write_obj(mesh,destination/f'{safe}.obj')
    save_json(str(relative/'skin.json'),{'source':args.input,'sha256':before,'meshes':meshes,
             'limits':'Original skin data extracted; no runtime animation, no automatic skeleton binding'})
    if hashlib.sha256(source.read_bytes()).hexdigest()!=before:raise ValueError('Source changed during extraction')
    print(f'Extracted {len(meshes)} native meshes, {sum(len(m["weights"]) for m in meshes)} weighted vertices; source unchanged')

if __name__=='__main__':main()
