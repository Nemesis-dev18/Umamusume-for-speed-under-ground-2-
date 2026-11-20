"""Stage a Gentildonna label and source-model portrait without replacing Nissan's other badges."""
import hashlib,json,struct,subprocess
import numpy as np
from PIL import Image
from inspect_assets import ROOT,jdlz,cartypes
from prepare_fleet_badges import directory
from prepare_selection_label import dxt3
from prepare_kitasan_badge import badge,compress_jdlz
from prepare_tiremask import rewrite_jdlz
from jdlz_native import finish_native,validate_native
from disable_car_effects import string_hash


def main():
 out=ROOT/'modding/staged-runtime/gentildonna-menu';out.mkdir(exist_ok=True)
 svg='<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="256"><g font-family="DejaVu Sans" font-weight="bold" font-style="oblique" font-size="108" stroke="#251c2a" stroke-width="12" paint-order="stroke fill"><text x="230" y="112" fill="#ffded0">GENTIL</text><text x="200" y="225" fill="#e8bd62">DONNA</text></g></svg>'
 (out/'label.svg').write_text(svg);subprocess.run(['magick','-background','none',str(out/'label.svg'),'-resize','256x64!',str(out/'label.png')],check=True)
 front=ROOT/'FRONTEND/FrontB.lzc';before=front.read_bytes();original=jdlz(before);raw=bytearray(original);textures=directory(raw)
 start,size,header=textures[string_hash('SECONDARY_LOGO_350Z')];assert size==16384
 with Image.open(out/'label.png') as im:label=dxt3(im.convert('RGBA'))
 assert len(label)==size;raw[start:start+size]=label
 # Portrait pixels come from the permitted model's independent neutral render.
 with Image.open(ROOT/'modding/runtime/gentildonna-gpu/9001-0.ppm') as im:
  im=im.convert('RGBA');pixels=np.array(im);pixels[:,:,3]=np.where(np.all(pixels[:,:,:3]==[37,42,50],axis=2),0,255);im=Image.fromarray(pixels).crop((245,0,395,180));im.thumbnail((62,62),Image.Resampling.LANCZOS);canvas=Image.new('RGBA',(128,64));canvas.alpha_composite(im,((128-im.width)//2,(64-im.height)//2));canvas.save(out/'portrait.png')
 portrait=dxt3(canvas);key=string_hash('CARSELECT_MANUFACTURER_GENTILDONNA')
 if key in textures:
  begin,count,_=directory(raw)[key];assert count==len(portrait);raw[begin:begin+count]=portrait
 else:raw,added=badge(bytes(raw),portrait,'GENTILDONNA');assert added==key
 after=directory(raw)
 for identity,(begin,count,_) in textures.items():
  if identity in (string_hash('SECONDARY_LOGO_350Z'),key):continue
  now,length,_=after[identity];assert count==length and original[begin:begin+count]==raw[now:now+length]
 encoded=finish_native(compress_jdlz(bytes(raw)));validate_native(encoded);assert jdlz(encoded)==raw
 (out/'FrontB.lzc').write_bytes(encoded)
 files=[{'target':'FRONTEND/FrontB.lzc','candidate':str((out/'FrontB.lzc').relative_to(ROOT)),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(encoded).hexdigest()}]
 for target in ('GLOBAL/GLOBALB.BUN','GLOBAL/GlobalB.lzc'):
  before=(ROOT/target).read_bytes();decoded=jdlz(before) if before.startswith(b'JDLZ') else before;result=bytearray(decoded);car=next(c for c in cartypes(decoded) if c['name']=='350Z');at=car['offset']+0xc0;result[at:at+16]=b'GENTILDONNA'.ljust(16,b'\0');encoded=rewrite_jdlz(before,bytes(result)) if before.startswith(b'JDLZ') else bytes(result)
  assert decoded[:at]==result[:at] and decoded[at+16:]==result[at+16:]
  dest=out/target.split('/')[-1];dest.write_bytes(encoded);files.append({'target':target,'candidate':str(dest.relative_to(ROOT)),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(encoded).hexdigest()})
 (out/'plan.json').write_text(json.dumps({'files':files,'installed':False,'visual_review_pending':True},indent=2)+'\n');print('Staged Gentildonna label and portrait; other menu textures preserved')

if __name__=='__main__':main()
