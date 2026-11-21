"""Stage Diamond's local source icon, title and names alongside regional title fixes."""
import hashlib,json,subprocess
from PIL import Image
from inspect_assets import ROOT,jdlz,cartypes
from prepare_regional_character_titles import build
from prepare_fleet_badges import directory
from prepare_kitasan_badge import badge,compress_jdlz
from prepare_selection_label import dxt3
from prepare_character_name import prepare_names,entries
from prepare_tiremask import rewrite_jdlz
from jdlz_native import finish_native,validate_native
from disable_car_effects import string_hash

def main():
 folder=ROOT/'modding/staged-runtime/diamond-menu';folder.mkdir(exist_ok=True)
 source=(ROOT/'FRONTEND/FrontB.lzc').read_bytes();regional,aliases,_,_=build(source);raw=jdlz(regional);old=directory(raw)
 svg='<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="256"><g font-family="DejaVu Sans" font-weight="bold" font-style="oblique" font-size="108" stroke="#163a31" stroke-width="12" paint-order="stroke fill"><text x="260" y="112" fill="#d9ffe8">SATONO</text><text x="185" y="225" fill="#ddcf83">DIAMOND</text></g></svg>'
 (folder/'title.svg').write_text(svg);subprocess.run(['magick','-background','none',str(folder/'title.svg'),'-resize','256x64!',str(folder/'title.png')],check=True)
 key=string_hash('SECONDARY_LOGO_CELICA');at,size,_=old[key];assert size==16384
 with Image.open(folder/'title.png') as im:pixels=dxt3(im.convert('RGBA'))
 assert len(pixels)==size;edited=bytearray(raw);edited[at:at+size]=pixels
 icon,=list((ROOT/'modding/uma-steam/fleet/1067/textures').glob('chr_icon_1067_*.png'))
 with Image.open(icon) as im:
  im=im.convert('RGBA');box=im.getchannel('A').getbbox();assert box;im=im.crop(box);im.thumbnail((62,62),Image.Resampling.LANCZOS);canvas=Image.new('RGBA',(128,64));canvas.alpha_composite(im,((128-im.width)//2,(64-im.height)//2));canvas.save(folder/'portrait.png')
 data,added=badge(bytes(edited),dxt3(canvas),'DIAMOND');assert added==string_hash('CARSELECT_MANUFACTURER_DIAMOND');new=directory(data)
 for identity,(pos,length,_) in old.items():
  now,count,_=new[identity];assert count==length
  if identity!=key:assert raw[pos:pos+length]==data[now:now+count]
 packed=finish_native(compress_jdlz(data));assert validate_native(packed)==data
 outputs={'FRONTEND/FrontB.lzc':packed};fields=[]
 for target in ('LANGUAGES/English.bin','LANGUAGES/Spanish.bin'):
  original=(ROOT/target).read_bytes();candidate=prepare_names(original,{'CELICA':'Satono Diamond','MIATA':'Agnes Tachyon','MX5':'Agnes Tachyon'} if string_hash('CAR_NAME_MX5') in {k for k,_,_ in entries(original)[2]} else {'CELICA':'Satono Diamond','MIATA':'Agnes Tachyon'})
  outputs[target]=candidate
 for target in ('GLOBAL/GLOBALB.BUN','GLOBAL/GlobalB.lzc'):
  original=(ROOT/target).read_bytes();decoded=jdlz(original) if original.startswith(b'JDLZ') else original;candidate=bytearray(decoded);car=next(c for c in cartypes(decoded) if c['name']=='CELICA');at=car['offset']+0xc0;candidate[at:at+16]=b'DIAMOND'.ljust(16,b'\0');assert decoded[:at]==candidate[:at] and decoded[at+16:]==candidate[at+16:];outputs[target]=rewrite_jdlz(original,bytes(candidate)) if original.startswith(b'JDLZ') else bytes(candidate);fields.append({'target':target,'decoded_offset':at,'bytes':16,'value':'DIAMOND'})
 assert jdlz(outputs['GLOBAL/GlobalB.lzc'])==outputs['GLOBAL/GLOBALB.BUN']
 rows=[]
 for target,value in outputs.items():
  dest=folder/target;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(value);rows.append({'target':target,'candidate':str(dest.relative_to(ROOT)),'before_sha256':hashlib.sha256((ROOT/target).read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(value).hexdigest(),'bytes':len(value)})
 (folder/'plan.json').write_text(json.dumps({'files':rows,'fields':fields,'regional_aliases':aliases,'installed':False,'gameplay_verified':False},indent=2)+'\n');print('PASS Diamond title/icon, localized names and manufacturer mapping; five regional aliases retained; staged only')
if __name__=='__main__':main()
