"""Stage a dedicated manufacturer badge; retain every existing Toyota texture."""
import hashlib,io,json,struct
from PIL import Image
from inspect_assets import ROOT,chunks,flatten,jdlz,cartypes
from disable_car_effects import string_hash
from prepare_selection_label import dxt3
from prepare_tiremask import rewrite_jdlz


def literal_jdlz(raw):
    if not raw:raise ValueError('Empty JDLZ')
    stream=bytearray()
    for at in range(0,len(raw),8):
        stream.append(0)
        if at==0:stream.append(0)
        stream.extend(raw[at:at+8])
    out=b'JDLZ\x02\x10\0\0'+struct.pack('<II',len(raw),16+len(stream))+stream
    if jdlz(out)!=raw:raise ValueError('JDLZ roundtrip')
    return out


def badge(raw,pixels):
    tree=chunks(raw);tpk=next(n for n in tree if n['offset']==204288)
    nodes={n['id']:n for n in flatten(tpk['children']) if n['id']!='0x00000000'}
    info,keys,formats,pool=[nodes[k] for k in ['0x33310004','0x33310002','0x33310005','0x33320002']]
    count=info['size']//124
    if (info['size']%124,keys['size'],formats['size'])!=(0,count*8,count*32):raise ValueError('Texture tables mismatch')
    rows=[]
    for i in range(count):
        a=raw[info['payload']+124*i:info['payload']+124*(i+1)]
        k=raw[keys['payload']+8*i:keys['payload']+8*(i+1)]
        f=raw[formats['payload']+32*i:formats['payload']+32*(i+1)]
        if a[36:40]!=k[:4]:raise ValueError('Table order mismatch')
        rows.append((struct.unpack('<I',k[:4])[0],a,k,f))
    original=next(r for r in rows if r[0]==0x3ad994a0)
    key=string_hash('CARSELECT_MANUFACTURER_KITASAN')
    if key in {r[0] for r in rows}:raise ValueError('Badge already present')
    a=bytearray(original[1]);struct.pack_into('<I',a,36,key)
    placement=pool['size']-120
    if placement%128 or len(pixels)!=8192:raise ValueError('Unaligned texture')
    struct.pack_into('<I',a,48,placement)
    rows.append((key,bytes(a),struct.pack('<II',key,0),original[3]));rows.sort(key=lambda r:r[0])
    replacements={info['offset']:b''.join(r[1] for r in rows),keys['offset']:b''.join(r[2] for r in rows),formats['offset']:b''.join(r[3] for r in rows),pool['offset']:raw[pool['payload']:pool['end']]+pixels}
    # Grow the existing metadata padding so subsequent pixel addresses shift by 256.
    pad=next((n for n in tpk['children'] if n['id']=='0x00000000' and n['offset']==nodes['0xb3310000']['end']),None)
    if pad is None:raise ValueError('Missing metadata padding')
    replacements[pad['offset']]=bytes(pad['size']+92)
    def rebuild(n):
        content=replacements.get(n['offset'])
        if content is None:content=b''.join(rebuild(c) for c in n['children']) if 'children' in n else raw[n['payload']:n['end']]
        return struct.pack('<II',int(n['id'],16),len(content))+content
    out=b''.join(rebuild(n) for n in tree);chunks(out)
    if len(out)!=len(raw)+256+8192:raise ValueError('Unexpected layout growth')
    return out,key


def main():
    source=ROOT/'FRONTEND/FrontB.lzc';before=source.read_bytes();raw=jdlz(before)
    image=Image.open(ROOT/'modding/character-source/official/kitasan-portrait.png').convert('RGBA')
    image.thumbnail((64,64),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(128,64));canvas.alpha_composite(image,((128-image.width)//2,0))
    canvas.save(ROOT/'modding/diagnostics/kitasan-badge-preview.png')
    out,key=badge(raw,dxt3(canvas));encoded=literal_jdlz(out)
    staged=ROOT/'modding/staged-runtime/FrontB.kitasan-badge.lzc';staged.write_bytes(encoded)
    rows=[dict(target=str(source.relative_to(ROOT)),candidate=str(staged.relative_to(ROOT)),before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(encoded).hexdigest(),bytes=len(encoded))]
    for name in ['GLOBAL/GLOBALB.BUN','GLOBAL/GlobalB.lzc']:
        path=ROOT/name;before=path.read_bytes();data=jdlz(before) if before[:4]==b'JDLZ' else before
        records=[r for r in cartypes(data) if r['name']=='COROLLA']
        if len(records)!=1:raise ValueError('Ambiguous Corolla')
        at=records[0]['offset']+0xc0
        if data[at:at+16]!=b'TOYOTA'+bytes(10):raise ValueError('Unexpected manufacturer')
        changed=data[:at]+b'KITASAN'+bytes(9)+data[at+16:]
        result=rewrite_jdlz(before,changed) if before[:4]==b'JDLZ' else changed
        dest=ROOT/'modding/staged-runtime'/('badge-'+path.name);dest.write_bytes(result)
        rows.append(dict(target=name,candidate=str(dest.relative_to(ROOT)),before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(result).hexdigest(),bytes=len(result),decoded_changed_range=[at,at+16]))
    (ROOT/'modding/kitasan-badge-plan.json').write_text(json.dumps(dict(files=rows,texture_hash=hex(key),installed=False,gameplay_verified=False),indent=2)+'\n')
    print('Staged dedicated Kitasan badge; original Toyota records preserved')

if __name__=='__main__':main()
