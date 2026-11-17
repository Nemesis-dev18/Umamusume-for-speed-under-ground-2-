"""Read local car packages and stage exact top-mip underbody-neon identities."""
import hashlib,json,struct
from pathlib import Path
from inspect_assets import ROOT,chunks,flatten,jdlz
from extract_assets import huff
from disable_car_effects import string_hash

def main():
 unique={};rows=[]
 for file in sorted((ROOT/'CARS').glob('*/TEXTURES.BIN')):
  name=file.parent.name+'_NEON';key=string_hash(name);data=file.read_bytes();found=0
  for node in flatten(chunks(data)):
   if node['id']!='0x33310003':continue
   if node['size']%24:raise ValueError('Partial descriptor')
   for at in range(node['payload'],node['end'],24):
    k,offset,size,outsize,back,_=struct.unpack_from('<6I',data,at)
    if k!=key:continue
    if offset+size>len(data):raise ValueError('Package bounds')
    blob=data[offset:offset+size];pool=jdlz(blob) if blob.startswith(b'JDLZ') else huff(blob);p=outsize-back+0x88
    if len(pool)!=outsize or p<24 or p+39>len(pool) or pool[p-24:p].split(b'\0')[0].decode()!=name:raise ValueError('Neon identity mismatch')
    width,height=struct.unpack_from('<HH',pool,p+32);fmt=pool[p+38]
    if fmt not in (0x22,0x24,0x26):raise ValueError('Unsupported native neon format')
    tag={0x22:b'DXT1',0x24:b'DXT3',0x26:b'DXT5'}[fmt];length=((width+3)//4)*((height+3)//4)*(8 if fmt==0x22 else 16)
    if not 0<length<=16384 or length>p:raise ValueError('Neon top mip bounds')
    pixels=pool[:length]
    if tag==b'DXT1' and pixels==(b'\0'*4+b'\xff'*4)*(length//8):
     found+=1;rows.append({'source':str(file.relative_to(ROOT)),'name':name,'already_transparent':True});continue
    identity=(width,height,tag,pixels);unique.setdefault(identity,len(unique));found+=1
    rows.append({'source':str(file.relative_to(ROOT)),'name':name,'descriptor_offset':at,'blob_offset':offset,'identity':unique[identity],'width':width,'height':height,'format':tag.decode(),'sha256':hashlib.sha256(pixels).hexdigest()})
  if file.parent.name not in ('DRIVER',) and not found:rows.append({'source':str(file.relative_to(ROOT)),'name':name,'absent':True})
 if not unique or len(unique)>8:raise ValueError('Neon identity budget')
 output=ROOT/'modding/staged-runtime/neon-identities.bin';output.parent.mkdir(exist_ok=True,parents=True)
 result=struct.pack('<4s2I',b'UMAE',1,len(unique))
 for (width,height,tag,pixels) in unique:result+=struct.pack('<4I',width,height,int.from_bytes(tag,'little'),len(pixels))+pixels
 output.write_bytes(result);manifest={'profiles':len(unique),'bytes':len(result),'sha256':hashlib.sha256(result).hexdigest(),'candidate':str(output.relative_to(ROOT)),'target':'modding/runtime/neon-identities.bin','textures':rows,'installed':False};(ROOT/'modding/neon-identities-plan.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'profiles':len(unique),'matched_textures':sum(not r.get('absent') for r in rows),'bytes':len(result)}))
if __name__=='__main__':main()
